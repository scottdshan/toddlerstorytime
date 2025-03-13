import os
import logging
import uuid
from typing import Optional, List, Dict, Any
from pathlib import Path

from app.tts.base import TTSProvider
from app.config import AUDIO_DIR

logger = logging.getLogger(__name__)

class NoneProvider(TTSProvider):
    """
    A 'None' TTS provider that doesn't actually generate audio.
    Useful for testing without incurring costs from real TTS services.
    """
    
    def __init__(self, voice_id: Optional[str] = None):
        """
        Initialize the None provider
        
        Args:
            voice_id: Optional voice ID (not used but kept for API compatibility)
        """
        self.voice_id = voice_id or "dummy_voice"
        
        # Use the absolute path from config
        self.output_dir = AUDIO_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("Initialized None TTS Provider")
    
    def generate_audio(self, text: str, voice_id: Optional[str] = None) -> Optional[str]:
        """
        Create a dummy audio path without actually generating audio
        
        Args:
            text: The text that would be converted to speech
            voice_id: Optional voice ID (not used)
            
        Returns:
            Path to a non-existent audio file
        """
        # Create a unique filename
        filename = f"dummy_audio_{uuid.uuid4()}.mp3"
        
        # Create the full path for the file system
        file_path = os.path.join(self.output_dir, filename)
        # Use forward slashes for the URL path - standardize to always start with /static/
        relative_path = f"/static/audio/{filename}"
        
        # Log the dummy generation
        text_excerpt = text[:50] + "..." if len(text) > 50 else text
        logger.info(f"DUMMY TTS: Would generate audio for: '{text_excerpt}'")
        logger.info(f"DUMMY TTS: Dummy file path would be: {file_path}")
        logger.info(f"DUMMY TTS: Audio URL path: {relative_path}")
        
        # Create an empty file as a placeholder
        Path(file_path).touch()
        
        return relative_path
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Return a list of dummy voices
        
        Returns:
            List with a single dummy voice
        """
        return [
            {
                "voice_id": "dummy_voice_1",
                "name": "Dummy Voice 1",
                "description": "This is a dummy voice for testing",
                "gender": "neutral"
            },
            {
                "voice_id": "dummy_voice_2",
                "name": "Dummy Voice 2",
                "description": "Another dummy voice for testing",
                "gender": "neutral"
            }
        ]
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Return dummy service information
        
        Returns:
            Dictionary with dummy service information
        """
        return {
            "service": "None TTS Provider",
            "description": "Dummy provider that doesn't actually generate audio",
            "remaining_characters": "Unlimited",
            "is_free": True,
            "status": "active"
        } 