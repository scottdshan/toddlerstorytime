import os
import uuid
from typing import Optional, List, Dict, Any, cast, Iterator

from elevenlabs import generate, save, set_api_key, voices
from elevenlabs.api import User

from app.config import ELEVENLABS_API_KEY, DEFAULT_VOICE_ID, AUDIO_DIR
from app.tts.base import TTSProvider

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
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """Get available voices from ElevenLabs"""
        try:
            voice_list = voices()
            return [{"voice_id": voice.voice_id, "name": voice.name} for voice in voice_list]
        except Exception as e:
            print(f"Error fetching ElevenLabs voices: {e}")
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
            print(f"Error fetching ElevenLabs user info: {e}")
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
            filepath = os.path.join(AUDIO_DIR, filename)
            
            # Save audio to file
            save(audio_bytes, filepath)
            
            # Return the relative path for serving - use forward slashes for URL path - standardize to always start with /static/
            relative_path = f"/static/audio/{filename}"
            logger.info(f"Generated ElevenLabs audio file at {filepath}")
            logger.info(f"ElevenLabs audio URL path: {relative_path}")
            
            return relative_path
        
        except Exception as e:
            print(f"Error generating audio with ElevenLabs: {e}")
            return None
