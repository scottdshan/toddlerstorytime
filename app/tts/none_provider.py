import os
import logging
import uuid
import re
import glob
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
    
    def _create_friendly_filename(self, universe: str, title: str) -> str:
        """
        Create a user-friendly filename based on universe and title
        
        Args:
            universe: The story universe
            title: The story title
            
        Returns:
            A user-friendly filename
        """
        # Sanitize the universe and title
        universe = re.sub(r'[^\w\s-]', '', universe).strip().lower()
        title = re.sub(r'[^\w\s-]', '', title).strip().lower()
        
        # Replace spaces with hyphens
        universe = re.sub(r'\s+', '-', universe)
        title = re.sub(r'\s+', '-', title)
        
        # Create the base filename
        base_filename = f"{universe}-{title}"
        
        # Check if files with this base name already exist
        existing_files = glob.glob(os.path.join(self.output_dir, f"{base_filename}*.mp3"))
        
        # If no files exist, return the base filename
        if not existing_files:
            return f"{base_filename}.mp3"
        
        # If files exist, find the highest number and increment
        highest_num = 0
        for file in existing_files:
            # Extract the number if it exists
            match = re.search(rf"{re.escape(base_filename)}-(\d+)\.mp3$", file)
            if match:
                num = int(match.group(1))
                highest_num = max(highest_num, num)
        
        # Return the filename with the incremented number
        return f"{base_filename}-{highest_num + 1}.mp3"
    
    def generate_audio(self, text: str, voice_id: Optional[str] = None, story_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a dummy audio path without actually generating audio
        
        Args:
            text: The text that would be converted to speech
            voice_id: Optional voice ID (not used)
            story_info: Optional dictionary containing universe and title for the filename
            
        Returns:
            Path to a non-existent audio file
        """
        # Create a user-friendly filename if story_info is provided
        if story_info and story_info.get('universe') and story_info.get('title'):
            filename = self._create_friendly_filename(
                story_info.get('universe', 'unknown'), 
                story_info.get('title', 'story')
            )
        else:
            # Fallback to UUID if story_info is not provided
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
        Get information about the service
        
        Returns:
            Dictionary with service information
        """
        return {
            "service": "None Provider",
            "description": "A dummy provider that doesn't actually generate audio.",
            "note": "This provider is for testing only and does not incur costs."
        } 