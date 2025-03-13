import os
import uuid
import logging
from typing import Optional, List, Dict, Any, cast, Iterator

from elevenlabs import generate, save, set_api_key, voices
from elevenlabs.api import User

from app.config import ELEVENLABS_API_KEY, DEFAULT_VOICE_ID, AUDIO_DIR, NETWORK_SHARE_PATH, NETWORK_SHARE_URL
from app.tts.base import TTSProvider

# Set up logging
logger = logging.getLogger(__name__)

# Set ElevenLabs API key
if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY is not set")
set_api_key(ELEVENLABS_API_KEY)

class ElevenLabsProvider(TTSProvider):
    """
    TTS provider implementation for ElevenLabs
    """
    
    def __init__(self, voice_id=None):
        self.voice_id = voice_id or DEFAULT_VOICE_ID
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
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from ElevenLabs"""
        try:
            voice_list = voices()
            return [{"voice_id": voice.voice_id, "name": voice.name} for voice in voice_list]
        except Exception as e:
            logger.error(f"Error fetching ElevenLabs voices: {e}")
            return []
    
    def get_service_info(self) -> Dict[str, Any]:
        """Get user subscription info"""
        try:
            user = User.from_api()
            return {
                "provider": "elevenlabs",
                "subscription": user.subscription.tier,
                "character_limit": user.subscription.character_limit,
                "character_count": user.subscription.character_count,
                "reset_date": user.subscription.next_character_count_reset_unix
            }
        except Exception as e:
            logger.error(f"Error fetching ElevenLabs user info: {e}")
            return {
                "provider": "elevenlabs",
                "error": str(e)
            }
    
    def generate_audio(self, text: str, voice_id: Optional[str] = None) -> Optional[str]:
        """
        Generate audio from text using ElevenLabs API
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use (defaults to instance voice_id)
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Use provided voice_id or default to instance voice_id
            voice = voice_id or self.voice_id
            
            # Generate audio
            audio_data = generate(
                text=text,
                voice=str(voice),
                model="eleven_multilingual_v2"
            )
            
            # Convert to bytes if it's an iterator
            if isinstance(audio_data, Iterator):
                audio_bytes = b''.join(audio_data)
            else:
                audio_bytes = audio_data
            
            # Create a unique filename
            filename = f"story_{uuid.uuid4()}.mp3"
            # Local file path
            local_file_path = os.path.join(self.output_dir, filename)
            # Network file path
            network_file_path = os.path.join(self.network_share_path, filename)
            # Local URL path (for web app)
            local_url_path = f"/static/audio/{filename}"
            
            # Save audio to local file
            save(audio_bytes, local_file_path)
            logger.info(f"Generated ElevenLabs audio file at {local_file_path}")
            
            # Save to network share if available
            if self.network_share_available:
                try:
                    with open(local_file_path, 'rb') as src_file:
                        audio_data = src_file.read()
                        
                    with open(network_file_path, 'wb') as dest_file:
                        dest_file.write(audio_data)
                    logger.info(f"Copied audio file to network share at {network_file_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to save to network share: {e}")
            
            logger.info(f"ElevenLabs audio URL path: {local_url_path}")
            # Return audio path (remove /static/ for consistency with database)
            return local_url_path.replace('/static/', '')
        
        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {e}")
            return None
