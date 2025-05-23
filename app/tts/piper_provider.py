import os
import logging
import uuid
import re
import glob
import subprocess
import json
from typing import Optional, List, Dict, Any, AsyncGenerator
from pathlib import Path

from app.tts.base import TTSProvider
from app.config import AUDIO_DIR, NETWORK_SHARE_PATH, NETWORK_SHARE_URL

logger = logging.getLogger(__name__)

class PiperProvider(TTSProvider):
    """
    TTS provider implementation using Piper (local neural TTS).
    
    Piper is a fast, local neural text-to-speech system that sounds great and is optimized for the Raspberry Pi 4.
    More information: https://github.com/rhasspy/piper
    """
    
    def __init__(self, voice_id: Optional[str] = None):
        """
        Initialize the Piper provider
        
        Args:
            voice_id: Optional voice ID to use (defaults to "en_GB-northern_english_male-medium")
        """
        # Set default voice ID if not provided
        self.voice_id = voice_id or "en_GB-northern_english_male-medium"
        
        # Determine Piper base directory (contains models, libs, etc.)
        # Priority: PIPER_DIR env var, otherwise default to ~/piper
        piper_base_dir_default = os.path.expanduser("~/piper")
        # Store as instance variable
        self.piper_base_dir = os.path.expanduser(os.environ.get("PIPER_DIR", piper_base_dir_default))
        logger.info(f"Using Piper base directory: {self.piper_base_dir}")

        # Determine Piper executable path
        # Priority: PIPER_PATH env var, otherwise default to <piper_base_dir>/piper
        piper_exe_path_default = os.path.join(self.piper_base_dir, "piper") # Use self.piper_base_dir
        self.piper_path = os.path.expanduser(os.environ.get("PIPER_PATH", piper_exe_path_default))
        logger.info(f"Using Piper executable path: {self.piper_path}")
        
        # Check if the determined piper executable exists and is a file
        if not os.path.isfile(self.piper_path):
            logger.warning(
                f"Piper executable not found or is not a file at '{self.piper_path}'. "
                f"Ensure it's installed correctly or set PIPER_PATH env var. "
                f"Will attempt to run '{os.path.basename(self.piper_path)}' assuming it's in system PATH."
            )
            # Fallback to just the name, hoping it's in PATH
            self.piper_path = os.path.basename(self.piper_path) 
        else:
             logger.info(f"Confirmed Piper executable exists at: {self.piper_path}")
        
        # Allow specifying an exact path to the voice model file (overrides model search)
        self.voice_model_path = os.environ.get("PIPER_VOICE_MODEL_PATH")
        if self.voice_model_path:
            logger.info(f"Using specific voice model path from environment: {self.voice_model_path}")
        
        # Determine models directory path
        # Priority: PIPER_MODELS_DIR env var, otherwise default to piper_base_dir
        self.models_dir = os.environ.get("PIPER_MODELS_DIR", self.piper_base_dir) # Use self.piper_base_dir
        
        # Log the models directory path
        logger.info(f"Piper models directory set to: {self.models_dir}")
        
        # Use the absolute path from config
        self.output_dir = AUDIO_DIR
        self.network_share_path = NETWORK_SHARE_PATH
        
        # Create directories if they don't exist
        os.makedirs(self.output_dir, exist_ok=True)
        try:
            os.makedirs(self.network_share_path, exist_ok=True)
            self.network_share_available = True
            logger.info(f"Network share path is available at {self.network_share_path}")
        except Exception as e:
            self.network_share_available = False
            logger.warning(f"Network share path is not available: {e}")
        
        logger.info(f"Initialized Piper Provider with default voice {self.voice_id}")

        # Log final calculated paths after __init__
        logger.info(f"PiperProvider initialized with:")
        logger.info(f"  Base Dir: {self.piper_base_dir}")
        logger.info(f"  Executable Path: {self.piper_path}")
        logger.info(f"  Models Dir: {self.models_dir}")
        logger.info(f"  Voice Model Path Env: {self.voice_model_path}")
        logger.info(f" LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH')}")

    def _create_friendly_filename(self, universe: str, title: str) -> str:
        """Create a friendly filename from universe and title"""
        # Remove special characters and spaces
        clean_universe = re.sub(r'[^\w\s-]', '', universe.lower())
        clean_title = re.sub(r'[^\w\s-]', '', title.lower())
        
        # Replace spaces with underscores
        filename = f"piper_{clean_universe}_{clean_title}_{uuid.uuid4()}.wav"
        return filename

    def generate_audio(self, text: str, voice_id: Optional[str] = None, story_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate audio from text using Piper
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use (overrides default)
            story_info: Optional dictionary containing universe and title for the filename
            
        Returns:
            Path to the generated audio file or None if generation failed
        """
        try:
            # Use provided voice ID or default
            selected_voice_id = voice_id or self.voice_id
            
            # Create a user-friendly filename if story_info is provided
            if story_info and story_info.get('universe') and story_info.get('title'):
                filename = self._create_friendly_filename(
                    story_info.get('universe', 'unknown'), 
                    story_info.get('title', 'story')
                )
            else:
                # Fallback to UUID if story_info is not provided
                filename = f"piper_{uuid.uuid4()}.wav"
            
            # Local file path
            local_file_path = os.path.join(self.output_dir, filename)
            # Network file path
            network_file_path = os.path.join(self.network_share_path, filename)
            # Local URL path (for web app)
            local_url_path = f"/static/audio/{filename}"
            
            # Get full voice ID if it's just the basic name
            if not selected_voice_id.endswith('.onnx'):
                selected_voice_id = f"{selected_voice_id}.onnx"
            
            # Debug info
            logger.info(f"Looking for voice model: {selected_voice_id}")
            logger.info(f"Models directory: {self.models_dir}")
            logger.info(f"Current working directory: {os.getcwd()}")
            
            # Expand home directory to full path for logging
            home_dir = os.path.expanduser("~")
            logger.info(f"Home directory: {home_dir}")
            
            # List files in models directory to debug
            if os.path.exists(self.models_dir):
                logger.info(f"Files in {self.models_dir}: {os.listdir(self.models_dir)}")
            else:
                logger.warning(f"Models directory does not exist: {self.models_dir}")
            
            # Look for the model file with extensive checks
            model_path = None
            search_paths = []
            possible_locations = []
            
            # Use the specific model path from environment if available
            if self.voice_model_path and os.path.exists(self.voice_model_path):
                logger.info(f"Using model from PIPER_VOICE_MODEL_PATH: {self.voice_model_path}")
                model_path = self.voice_model_path
            else:
                # Try multiple possible locations
                possible_locations = [
                    # Direct path
                    selected_voice_id,
                    # In models directory
                    os.path.join(self.models_dir, selected_voice_id),
                    # Try with absolute home path
                    os.path.join(home_dir, "piper", selected_voice_id),
                    # Try with direct home/piper path
                    f"~/piper/{selected_voice_id}",
                    # Try without .onnx extension if already added
                    os.path.join(self.models_dir, selected_voice_id.replace('.onnx', '')) + '.onnx',
                ]
            
            for location in possible_locations:
                # Expand ~ if present
                if location.startswith("~"):
                    location = os.path.expanduser(location)
                
                search_paths.append(location)
                logger.info(f"Checking for model at: {location}")
                
                if os.path.exists(location):
                    logger.info(f"✓ Found model at: {location}")
                    model_path = location
                    break
                else:
                    logger.info(f"✗ Not found at: {location}")
            
            if not model_path:
                logger.error(f"Voice model not found in any of these locations: {search_paths}")
                # Only check for file existence directly for troubleshooting
                direct_path = os.path.join(home_dir, "piper", selected_voice_id)
                if os.path.isfile(direct_path):
                    logger.error(f"File actually exists at {direct_path} but wasn't detected by os.path.exists()")
                raise FileNotFoundError(f"Voice model not found: {selected_voice_id}")
            
            # Extract the speaker ID from story_info if provided
            speaker_id = None
            if story_info and 'speaker_id' in story_info:
                speaker_id = story_info.get('speaker_id')
            
            logger.info(f"Using Piper voice: {selected_voice_id}")
            
            try:
                # Create a JSON input line for Piper
                json_data = {"text": text, "output_file": local_file_path}
                if speaker_id is not None:
                    json_data["speaker_id"] = speaker_id
                
                json_line = json.dumps(json_data) + "\n"
                print(f"json_line: {json_line}")
                
                # Run Piper command with JSON input
                # Ensure piper_path is absolute
                absolute_piper_path = os.path.abspath(self.piper_path)
                absolute_model_path = os.path.abspath(model_path)
                cmd = [
                    absolute_piper_path, # Use absolute path
                    "--model", absolute_model_path, # Use absolute path
                    "--json-input"
                ]
                
                # Log the command being executed
                logger.info(f"Executing piper command: {' '.join(cmd)}")
                
                                # Log the LD_LIBRARY_PATH from the environment that will be inherited
                piper_lib_dir = os.path.dirname(os.path.abspath(self.piper_path))
                if os.path.isdir(self.piper_base_dir) and self.piper_base_dir != piper_lib_dir:
                    piper_lib_dir = self.piper_base_dir

                current_env = os.environ.copy()
                # This line modifies LD_LIBRARY_PATH based on the calculation above
                current_env['LD_LIBRARY_PATH'] = f"{piper_lib_dir}:{current_env.get('LD_LIBRARY_PATH', '')}".strip(':')

                result = subprocess.run(
                    cmd,
                    input=json_line,
                    capture_output=True,
                    text=True,
                    check=True,
                    env=current_env # Passes the modified environment
                )
                logger.info(f"Generated audio file at {local_file_path}")
                
                # Save to network share if available
                if self.network_share_available and os.path.exists(local_file_path):
                    try:
                        import shutil
                        shutil.copy2(local_file_path, network_file_path)
                        logger.info(f"Copied audio file to network share at {network_file_path}")
                    except Exception as e:
                        logger.error(f"Failed to save to network share: {e}")
                
                # Return the proper path that works with the audio endpoint
                # Instead of "audio/filename.wav", return just the filename
                # that will be used with the /api/audio/file/{filename} endpoint
                return filename
                
            except Exception as e:
                logger.error(f"Error in Piper audio generation: {e}", exc_info=True)
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Piper command failed: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Error generating audio with Piper: {e}", exc_info=True)
            return None

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices from the models directory
        
        Returns:
            List of voice dictionaries with voice_id and name
        """
        try:
            voices = []
            # Look for .onnx files in the models directory
            for model_file in glob.glob(os.path.join(self.models_dir, "*.onnx")):
                voice_id = Path(model_file).stem  # Remove .onnx extension
                config_file = model_file + ".json"
                
                # Default values
                name = voice_id.replace('_', ' ').title()
                language = None
                gender = None
                
                # Try to read config file for more information
                if os.path.exists(config_file):
                    try:
                        with open(config_file, 'r', encoding='utf-8') as f:
                            config = json.load(f)
                            # Try to extract language and speaker info
                            if "language" in config:
                                language = config["language"]
                            
                            # See if it's a multi-speaker model
                            if "speaker_id_map" in config:
                                # For multi-speaker models, create an entry for each speaker
                                for speaker_name, speaker_id in config["speaker_id_map"].items():
                                    speaker_voice_id = f"{voice_id}@{speaker_name}"
                                    voices.append({
                                        'voice_id': speaker_voice_id,
                                        'name': f"{name} - {speaker_name}",
                                        'language': language,
                                        'speaker_id': speaker_id
                                    })
                                # Skip adding the base model since we added each speaker
                                continue
                    except Exception as e:
                        logger.warning(f"Failed to read config file {config_file}: {e}")
                
                # Add the voice (either single speaker or if config couldn't be read)
                voices.append({
                    'voice_id': voice_id,
                    'name': name,
                    'language': language,
                    'gender': gender
                })
            
            # If no voices found, add some default voices
            if not voices:
                voices = [
                    {
                        "voice_id": "en_GB-northern_english_male-medium",
                        "name": "Northern English Male (Medium)",
                        "language": "en_GB"
                    }
                ]
            
            return voices
        except Exception as e:
            logger.error(f"Error getting available Piper voices: {e}", exc_info=True)
            return []

    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Piper service
        
        Returns:
            Dictionary with service information
        """
        voices = self.get_available_voices()
        return {
            'service': 'Piper',
            'description': 'Piper is a fast, local neural text-to-speech engine optimized for the Raspberry Pi 4',
            'voices_available': len(voices),
            'default_voice': self.voice_id,
            'models_directory': self.models_dir,
            'piper_executable': self.piper_path,
            'repository': 'https://github.com/rhasspy/piper'
        }

    async def generate_audio_streaming(self, text: str,  # type: ignore
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Generate raw audio data from text in a streaming fashion.
        Outputs raw PCM audio suitable for piping to a player like aplay.

        Args:
            text: The text to convert to speech.
            voice_id: Optional voice ID to use.
            story_info: Optional dictionary containing universe and title (used for speaker_id).

        Returns:
            Async generator yielding chunks of raw PCM audio data.
        """
        import asyncio
        
        process = None # Define process here to ensure it's accessible in finally
        try:
            # Use provided voice ID or default
            selected_voice_id = voice_id or self.voice_id
            
            # Handle potential multi-speaker format like "en_US-lessac-medium@2"
            speaker_id = None
            if '@' in selected_voice_id:
                selected_voice_id, speaker_id_str = selected_voice_id.split('@', 1)
                try:
                    speaker_id = int(speaker_id_str)
                    logger.info(f"Using multi-speaker voice: {selected_voice_id} with speaker ID: {speaker_id}")
                except ValueError:
                    logger.warning(f"Invalid speaker ID format in voice_id: {voice_id}. Ignoring speaker ID.")
                    speaker_id = None # Reset if format is wrong
            # Extract the speaker ID from story_info if provided (fallback)
            elif story_info and 'speaker_id' in story_info:
                speaker_id = story_info.get('speaker_id')
            
            # Append .onnx if needed (after splitting speaker ID)
            if not selected_voice_id.endswith('.onnx'):
                selected_voice_id = f"{selected_voice_id}.onnx"

            # Determine model path
            model_path = None
            
            # Use the specific model path from environment if available
            if self.voice_model_path and os.path.exists(self.voice_model_path):
                model_path = self.voice_model_path
            else:
                # Try multiple possible locations
                home_dir = os.path.expanduser("~")
                possible_locations = [
                    selected_voice_id,
                    os.path.join(self.models_dir, selected_voice_id),
                    os.path.join(home_dir, "piper", selected_voice_id),
                    f"~/piper/{selected_voice_id}",
                    os.path.join(self.models_dir, selected_voice_id.replace('.onnx', '')) + '.onnx',
                ]
                
                for location in possible_locations:
                    # Expand ~ if present
                    if location.startswith("~"):
                        location = os.path.expanduser(location)
                    
                    if os.path.exists(location):
                        model_path = location
                        break
                        
            if not model_path:
                logger.error(f"Voice model not found for streaming: {selected_voice_id}")
                # Yield nothing if model not found to avoid breaking consumer entirely
                return
                # raise FileNotFoundError(f"Voice model not found: {selected_voice_id}") # Alternative: raise error

            # Prepare Piper command for raw streaming output
            cmd = [
                self.piper_path,
                "--model", model_path,
                "--output-raw" # Output raw audio to stdout
            ]
            
            # Add speaker ID if applicable
            if speaker_id is not None:
                cmd.extend(["--speaker", str(speaker_id)])

            # Set up environment variables (similar to generate_audio)
            piper_lib_dir = os.path.dirname(os.path.abspath(self.piper_path))
            if os.path.isdir(self.piper_base_dir) and self.piper_base_dir != piper_lib_dir:
                piper_lib_dir = self.piper_base_dir
                
            current_env = os.environ.copy()
            current_env['LD_LIBRARY_PATH'] = f"{piper_lib_dir}:{current_env.get('LD_LIBRARY_PATH', '')}".strip(':')

            logger.info(f"Executing piper streaming command: {' '.join(cmd)}")

            # Execute Piper, reading text from stdin and writing raw audio to stdout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=current_env # Pass the environment variables
            )

            # Write text to Piper's stdin and close it
            if process.stdin:
                # Piper expects specific encoding, often UTF-8
                process.stdin.write(text.encode('utf-8'))
                await process.stdin.drain()
                process.stdin.close()

            # Read raw audio chunks from Piper's stdout
            chunk_size = 4096 # Adjust chunk size as needed
            while process.stdout and not process.stdout.at_eof():
                chunk = await process.stdout.read(chunk_size)
                if not chunk:
                    break # End of stream
                yield chunk
                # No artificial sleep needed here

            # Wait for the process to finish and check for errors
            await process.wait()

            if process.returncode != 0:
                stderr_output = await process.stderr.read() if process.stderr else b''
                logger.error(f"Piper command failed with exit code {process.returncode}: {stderr_output.decode(errors='ignore')}")
                # Option 1: Just log the error but don't break the stream
                # Option 2: Raise - commented out for now
                # raise RuntimeError(f"Piper failed: {stderr_output.decode(errors='ignore')}")

        except asyncio.CancelledError:
            logger.info("Piper streaming task cancelled.")
            # Ensure process is terminated if cancelled mid-stream
            if process and process.returncode is None:
                try:
                    process.terminate()
                    await process.wait()
                    logger.info("Terminated Piper process due to cancellation.")
                except ProcessLookupError:
                    pass # Process already finished
                except Exception as term_err:
                    logger.warning(f"Error terminating Piper process on cancellation: {term_err}")
            raise # Re-raise CancelledError
            
        except FileNotFoundError as e:
            logger.error(f"Piper executable or model not found: {e}")
            # Yield nothing or raise specific error
            return
            
        except Exception as e:
            logger.error(f"Error in streaming audio generation with Piper: {str(e)}", exc_info=True)
            # Yield an empty chunk or raise to signal error to the consumer
            yield b""
            
        finally:
            # Ensure process is cleaned up if it was started and hasn't finished
            if process and process.returncode is None:
                try:
                    logger.warning("Piper process still running in finally block, terminating.")
                    process.terminate()
                    await process.wait()
                except ProcessLookupError:
                    pass # Process already finished
                except Exception as term_err:
                    logger.warning(f"Error terminating Piper process in finally block: {term_err}") 