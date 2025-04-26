import os
import logging
import asyncio
import subprocess
import uuid
from typing import Optional, List, Dict, Any, AsyncGenerator

from app.tts.base import TTSProvider
from app.config import AUDIO_DIR # Assuming AUDIO_DIR is where temporary files might go if needed

logger = logging.getLogger(__name__)

# Default path, assumes 'koko' is in the system PATH
DEFAULT_KOKO_PATH = "koko" 

class KokorosProvider(TTSProvider):
    """
    TTS provider implementation using Kokoros (local TTS via command line).
    Uses the 'koko stream' command for streaming audio synthesis.
    Kokoros project: https://github.com/lucasjinreal/Kokoros
    """

    def __init__(self, voice_id: Optional[str] = None, koko_path: Optional[str] = None):
        """
        Initialize the Kokoros provider.

        Args:
            voice_id: Default voice ID to use (e.g., "af_sky"). Defaults to "af_sky".
            koko_path: Path to the 'koko' executable. Defaults to 'koko' (assumes in PATH).
        """
        # Default to a known good voice if none provided
        self.voice_id = voice_id or os.environ.get("KOKOROS_DEFAULT_VOICE_ID", "af_sky") 
        
        # Determine koko executable path
        # Priority: KOKO_PATH env var, then argument, then default
        self.koko_path = (
            os.environ.get("KOKO_PATH") or 
            koko_path or 
            DEFAULT_KOKO_PATH
        )
        
        # Basic check if the executable seems plausible
        # A more robust check might involve running 'koko -h'
        # if not os.path.exists(self.koko_path) and not shutil.which(self.koko_path):
        #     logger.warning(f"Kokoros executable not found at specified path: {self.koko_path}. Synthesis might fail.")
            
        # Output directory (might not be strictly needed for pure streaming)
        self.output_dir = AUDIO_DIR
        os.makedirs(self.output_dir, exist_ok=True)

        logger.info(f"Initialized Kokoros TTS Provider with executable path: {self.koko_path} and default voice: {self.voice_id}")

    def _get_kokoros_voices(self) -> List[Dict[str, Any]]:
        """
        Placeholder for fetching available Kokoros voices.
        Currently returns a default set as Kokoros CLI doesn't have a standard way to list voices easily.
        The voices.json file could potentially be parsed if its location is known.
        """
        # TODO: Implement dynamic voice fetching if possible, e.g., parsing voices.json
        # This might require knowing the Kokoros installation directory.
        logger.warning("Kokoros voice listing is currently static. Add logic to parse voices.json if needed.")
        return [
            {"voice_id": "af_sky", "name": "Sky (Female, Standard)"},
            {"voice_id": "af_libritts", "name": "LibriTTS (Female)"},
            {"voice_id": "en_US-amy-low", "name": "Amy (Female, US English - Low Quality)"},
            # Add other known voices if desired
        ]

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices (currently static).
        """
        return self._get_kokoros_voices()

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Kokoros service.
        """
        voices = self.get_available_voices()
        return {
            'service': 'Kokoros (Local)',
            'description': 'Kokoros is a fast, local TTS engine run via command line.',
            'voices_available': len(voices),
            'default_voice': self.voice_id,
            'koko_executable': self.koko_path,
            'repository': 'https://github.com/lucasjinreal/Kokoros'
        }

    async def generate_audio_streaming(self, text: str, 
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Generate WAV audio data from text in a streaming fashion using 'koko stream'.

        Args:
            text: The text to convert to speech.
            voice_id: Optional voice ID to use (e.g., "af_sky").
            story_info: Optional dictionary (not currently used by Kokoros).

        Returns:
            Async generator yielding chunks of WAV audio data.
        """
        process = None # Define process here to ensure it's accessible in finally
        try:
            selected_voice_id = voice_id or self.voice_id
            
            cmd = [
                self.koko_path,
                "stream",
                "--voice", selected_voice_id
                # Add any other necessary flags for koko stream if needed
            ]

            logger.info(f"Executing Kokoros streaming command: {' '.join(cmd)}")

            # Execute koko stream, piping text to stdin and reading WAV audio from stdout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE # Capture stderr for logging errors
            )

            # Write text to Kokoros stdin and close it
            if process.stdin:
                try:
                    # Kokoros likely expects UTF-8
                    process.stdin.write(text.encode('utf-8'))
                    await process.stdin.drain()
                    process.stdin.close()
                except (BrokenPipeError, ConnectionResetError) as e:
                    logger.warning(f"Kokoros stdin pipe closed unexpectedly: {e}")
                    # Attempt to read stderr for more info
                    stderr_output = await self._read_stderr(process)
                    logger.error(f"Kokoros stderr (on stdin close error): {stderr_output}")
                    # Don't yield anything if we can't send input
                    return 
            else:
                logger.error("Failed to get stdin pipe for Kokoros process.")
                stderr_output = await self._read_stderr(process) # Try reading stderr
                logger.error(f"Kokoros stderr (on stdin fail): {stderr_output}")
                return # Don't proceed without stdin

            # Read WAV audio chunks from Kokoros stdout
            chunk_size = 4096 # Adjust chunk size as needed
            while process.stdout and not process.stdout.at_eof():
                chunk = await process.stdout.read(chunk_size)
                if not chunk:
                    break # End of stream
                yield chunk
                # No artificial sleep needed, yield as data arrives

            # Wait for the process to finish and check for errors
            return_code = await process.wait()
            
            if return_code != 0:
                logger.error(f"Kokoros process exited with non-zero code: {return_code}")
                stderr_output = await self._read_stderr(process)
                logger.error(f"Kokoros stderr: {stderr_output}")
                # Optionally yield an empty chunk or raise an exception if needed
                # yield b"" # To prevent breaking consumer if it expects something
            else:
                 logger.info(f"Kokoros streaming completed successfully for text: {text[:50]}...")

        except FileNotFoundError:
            logger.error(f"Kokoros executable not found at '{self.koko_path}'. Please ensure it's installed and the path is correct (or set KOKO_PATH environment variable).")
            yield b"" # Yield empty chunk on critical error
        except Exception as e:
            logger.error(f"Error during Kokoros streaming audio generation: {e}", exc_info=True)
            # Attempt to read stderr if process exists
            if process:
                stderr_output = await self._read_stderr(process)
                logger.error(f"Kokoros stderr (on exception): {stderr_output}")
            yield b"" # Yield empty chunk on error to avoid breaking consumer
        finally:
            # Ensure the process is terminated if it's still running
            if process and process.returncode is None:
                try:
                    process.terminate()
                    await process.wait() # Wait for termination
                    logger.warning("Kokoros process terminated during cleanup.")
                except ProcessLookupError:
                    logger.debug("Kokoros process already finished.") # Process might have finished between check and terminate
                except Exception as term_err:
                    logger.error(f"Error terminating Kokoros process: {term_err}")

    async def _read_stderr(self, process: asyncio.subprocess.Process) -> str:
        """Helper function to read stderr."""
        if process.stderr:
            try:
                stderr_bytes = await process.stderr.read()
                return stderr_bytes.decode('utf-8', errors='ignore').strip()
            except Exception as e:
                logger.error(f"Error reading Kokoros stderr: {e}")
                return "[Error reading stderr]"
        return "[stderr not available]"

    def generate_audio(self, text: str, voice_id: Optional[str] = None, story_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate audio to a file (non-streaming). 
        This uses the 'koko text' command.
        
        Note: Streaming is generally preferred for real-time applications.
        
        Args:
            text: The text to convert to speech.
            voice_id: Optional voice ID.
            story_info: Optional dictionary for filename generation.

        Returns:
            Path (URL) to the generated audio file or None if generation failed.
        """
        try:
            selected_voice_id = voice_id or self.voice_id
            
            # Create a unique filename
            # Using a UUID for simplicity, but could use story_info like other providers
            filename_base = f"kokoros_audio_{uuid.uuid4()}"
            output_filename = f"{filename_base}.wav" # Kokoros default output seems to be wav
            output_filepath = os.path.join(self.output_dir, output_filename)
            
            cmd = [
                self.koko_path,
                "text",
                text, # Pass text directly as argument
                "--voice", selected_voice_id,
                "--output", output_filepath 
            ]

            logger.info(f"Executing Kokoros file generation command: {' '.join(cmd)}")

            # Run the command synchronously for file generation
            result = subprocess.run(cmd, capture_output=True, text=True, check=False, encoding='utf-8')

            if result.returncode != 0:
                logger.error(f"Kokoros command failed with code {result.returncode}")
                logger.error(f"Stderr: {result.stderr}")
                logger.error(f"Stdout: {result.stdout}")
                return None
            
            if not os.path.exists(output_filepath):
                 logger.error(f"Kokoros command succeeded but output file not found: {output_filepath}")
                 logger.error(f"Stderr: {result.stderr}")
                 logger.error(f"Stdout: {result.stdout}")
                 return None

            logger.info(f"Kokoros generated audio file: {output_filepath}")
            
            # Return the web-accessible path (assuming /static/audio maps to AUDIO_DIR)
            relative_path = f"/static/audio/{output_filename}"
            return relative_path

        except FileNotFoundError:
            logger.error(f"Kokoros executable not found at '{self.koko_path}'. Cannot generate audio file.")
            return None
        except Exception as e:
            logger.error(f"Error generating audio file with Kokoros: {e}", exc_info=True)
            return None 