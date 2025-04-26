from typing import Optional
from app.tts.base import TTSProvider
from app.tts.elevenlabs_provider import ElevenLabsProvider
from app.tts.none_provider import NoneProvider
from app.tts.amazon_polly_provider import AmazonPollyProvider
from app.tts.piper_provider import PiperProvider
from app.tts.kokoros_provider import KokorosProvider
import os

class TTSFactory:
    """
    Factory class for creating TTS provider instances.
    Makes it easy to switch between different TTS providers.
    """
    
    @staticmethod
    def get_provider(provider_name: str, voice_id: Optional[str] = None) -> TTSProvider:
        """
        Get a TTS provider instance by name
        
        Args:
            provider_name: Name of the TTS provider ("elevenlabs", "none", "amazon", "piper", etc.)
            voice_id: Optional voice ID to use
            
        Returns:
            TTSProvider instance
            
        Raises:
            ValueError: If the provider is not supported
        """
        provider_name = provider_name.lower()
        
        # Get voice ID from environment if not explicitly provided
        if voice_id is None:
            voice_id = os.environ.get("TTS_VOICE_ID")
        
        if provider_name == "elevenlabs":
            print(f"Using ElevenLabs provider with voice ID: {voice_id}")
            return ElevenLabsProvider(voice_id=voice_id)
        elif provider_name == "none":
            return NoneProvider(voice_id=voice_id)
        elif provider_name in ["amazon", "amazon_polly", "amazon-polly", "polly"]:
            return AmazonPollyProvider(voice_id=voice_id)
        elif provider_name == "piper":
            return PiperProvider(voice_id=voice_id)
        elif provider_name == "kokoros":
            print(f"Using Kokoros provider with voice ID: {voice_id}")
            return KokorosProvider(voice_id=voice_id)
        else:
            raise ValueError(f"Unsupported TTS provider: {provider_name}")
