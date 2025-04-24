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
            voice_id: Optional voice ID to use (defaults to "en_US-lessac-medium")
        """
        # Set default voice ID if not provided
        self.voice_id = voice_id or "en_US-lessac-medium"
        
        # Get Piper executable path from environment or use default
        self.piper_path = os.environ.get("PIPER_PATH", os.path.expanduser("~/piper/piper"))
        logger.info(f"Using Piper executable at: {self.piper_path}")
        
        # Check if the piper executable exists
        if not os.path.exists(self.piper_path):
            logger.warning(f"Piper executable not found at {self.piper_path}. Make sure it's installed properly.")
            
            # Try fallback to home dir
            piper_in_home = os.path.expanduser("~/piper/piper")
            if os.path.exists(piper_in_home):
                logger.info(f"Found Piper executable in home directory: {piper_in_home}")
                self.piper_path = piper_in_home
        
        # Allow specifying an exact path to the voice model file
        self.voice_model_path = os.environ.get("PIPER_VOICE_MODEL_PATH")
        if self.voice_model_path:
            logger.info(f"Using specific voice model path from environment: {self.voice_model_path}")
        
        # Get models directory from environment or use default
        self.models_dir = os.environ.get("PIPER_MODELS_DIR", os.path.expanduser("~/piper"))
        
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
                
                # Run Piper command with JSON input
                cmd = [
                    self.piper_path,
                    "--model", model_path,
                    "--json-input"
                ]
                
                # Log the command being executed
                logger.info(f"Executing piper command: {' '.join(cmd)}")
                
                # Log environment variables
                logger.info(f"LD_LIBRARY_PATH: {os.environ.get('LD_LIBRARY_PATH', 'not set')}")
                
                # Execute Piper with JSON input directly to stdin
                result = subprocess.run(
                    cmd,
                    input=json_line,
                    capture_output=True,
                    text=True,
                    check=True
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
                        "voice_id": "en_US-lessac-medium",
                        "name": "English US (Lessac, Medium)",
                        "language": "en_US"
                    },
                    {
                        "voice_id": "en_GB-alba-medium",
                        "name": "English GB (Alba, Medium)",
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

    async def generate_audio_streaming(self, text: str, 
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Generate audio from text in a streaming fashion
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use
            story_info: Optional dictionary containing universe and title
            
        Returns:
            Async generator yielding chunks of audio data as they're generated
        """
        import asyncio
        import io
        import wave
        
        try:
            # Use provided voice ID or default
            selected_voice_id = voice_id or self.voice_id
            
            # Get full voice ID if it's just the basic name
            if not selected_voice_id.endswith('.onnx'):
                selected_voice_id = f"{selected_voice_id}.onnx"
            
            # Determine model path using same logic as in generate_audio
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
                raise FileNotFoundError(f"Voice model not found: {selected_voice_id}")
            
            # Extract the speaker ID from story_info if provided
            speaker_id = None
            if story_info and 'speaker_id' in story_info:
                speaker_id = story_info.get('speaker_id')
            
            # Use a temporary file for output
            temp_output_file = os.path.join(self.output_dir, f"temp_stream_{uuid.uuid4()}.wav")
            
            # Create a JSON input line for Piper
            json_data = {"text": text, "output_file": temp_output_file}
            if speaker_id is not None:
                json_data["speaker_id"] = speaker_id
            
            json_line = json.dumps(json_data) + "\n"
            
            # Run Piper command with JSON input
            cmd = [
                self.piper_path,
                "--model", model_path,
                "--json-input"
            ]
            
            # Log the command
            logger.info(f"Executing piper streaming command: {' '.join(cmd)}")
            
            # Execute Piper to generate the audio file
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Send the JSON data to the process
            stdout, stderr = await process.communicate(json_line.encode())
            
            if process.returncode != 0:
                logger.error(f"Piper command failed: {stderr.decode()}")
                return
            
            # Read the audio file and yield chunks
            if os.path.exists(temp_output_file):
                try:
                    with open(temp_output_file, 'rb') as f:
                        # Yield file contents in chunks for streaming
                        chunk_size = 4096  # 4KB chunks
                        while chunk := f.read(chunk_size):
                            yield chunk
                            # Small delay to simulate streaming
                            await asyncio.sleep(0.01)
                finally:
                    # Clean up the temporary file
                    try:
                        os.remove(temp_output_file)
                    except Exception as e:
                        logger.warning(f"Failed to remove temporary file: {e}")
            else:
                logger.error(f"Temporary audio file not created: {temp_output_file}")
                
        except Exception as e:
            logger.error(f"Error in streaming audio generation with Piper: {str(e)}")
            # Yield an empty chunk to prevent breaking the stream
            yield b"" 