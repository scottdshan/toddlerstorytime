from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, AsyncGenerator, BinaryIO

class TTSProvider(ABC):
    """
    Abstract base class for text-to-speech providers.
    All TTS implementations should inherit from this class.
    """
    
    @abstractmethod
    def generate_audio(self, text: str, voice_id: Optional[str] = None, story_info: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Generate audio from text
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use
            story_info: Optional dictionary containing universe and title for the filename
            
        Returns:
            Path to the generated audio file or None if generation failed
        """
        pass
    
    @abstractmethod
    async def generate_audio_streaming(self, text: str, 
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]:
        """
        Generate audio from text in a streaming fashion
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use
            story_info: Optional dictionary containing universe and title for the filename
            
        Returns:
            Async generator yielding chunks of audio data as they're generated
        """
        pass
    
    @abstractmethod
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices from the provider
        
        Returns:
            List of voice dictionaries with at least 'voice_id' and 'name' keys
        """
        pass
    
    @abstractmethod
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the TTS service (e.g., usage limits, account status)
        
        Returns:
            Dictionary with service information
        """
        pass
