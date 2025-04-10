import os
import uuid
import logging
import re
import glob
from typing import Optional, List, Dict, Any, cast, Iterator, AsyncGenerator, Union
import asyncio
from collections import deque

from elevenlabs import generate, save, set_api_key, voices
from elevenlabs.api import User

from app.config import ELEVENLABS_API_KEY, DEFAULT_VOICE_ID, AUDIO_DIR, NETWORK_SHARE_PATH
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
        
        # For streaming, keep a buffer of text chunks to process
        self.text_buffer = deque()
        # Minimum number of characters before we process a chunk
        self.min_chunk_size = 50  
    
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
            from elevenlabs.api import User
            user_data = User.from_api()
            
            subscription = user_data.subscription
            if subscription:
                character_limit = subscription.character_limit
                character_count = subscription.character_count
                
                # Calculate remaining characters
                remaining = max(0, character_limit - character_count) if character_limit else "Unlimited"
                
                return {
                    "service": "ElevenLabs",
                    "subscription_tier": subscription.tier,
                    "character_limit": character_limit or "Unlimited",
                    "character_count": character_count,
                    "characters_remaining": remaining,
                    "voice_count": len(self.get_available_voices()),
                    "default_voice": self.voice_id
                }
            
            return {
                "service": "ElevenLabs",
                "error": "Could not retrieve subscription information"
            }
            
        except Exception as e:
            logger.error(f"Error getting ElevenLabs service info: {e}")
            return {
                "service": "ElevenLabs",
                "error": str(e)
            }
    
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
        Generate audio from text using the ElevenLabs API
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use
            story_info: Optional dictionary containing universe and title for the filename
            
        Returns:
            Path to the generated audio file
        """
        try:
            voice = voice_id or self.voice_id
            audio_data = generate(text=text, voice=str(voice), model="eleven_multilingual_v2")
            audio_bytes = b''.join(audio_data) if isinstance(audio_data, Iterator) else audio_data

            # Create a user-friendly filename if story_info is provided
            if story_info and story_info.get('universe') and story_info.get('title'):
                filename = self._create_friendly_filename(
                    story_info.get('universe', 'unknown'), 
                    story_info.get('title', 'story')
                )
            else:
                # Fallback to UUID if story_info is not provided
                filename = f"story_{uuid.uuid4()}.mp3"
                
            local_file_path = os.path.join(self.output_dir, filename)
            network_file_path = os.path.join(self.network_share_path, filename)
            local_url_path = f"/static/audio/{filename}"

            save(audio_bytes, local_file_path)
            logger.info(f"Generated ElevenLabs audio file at {local_file_path}")

            if self.network_share_available:
                try:
                    with open(network_file_path, 'wb') as dest_file:
                        dest_file.write(audio_bytes)
                    logger.info(f"Copied audio file to network share at {network_file_path}")
                except Exception as e:
                    logger.error(f"Failed to save to network share: {e}")

            return local_url_path.replace('/static/', '')

        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {e}")
            return None
    
    async def generate_audio_streaming(self, text: str, 
                                      voice_id: Optional[str] = None, 
                                      story_info: Optional[Dict[str, Any]] = None) -> AsyncGenerator[bytes, None]: # type: ignore
        """
        Generate audio from text in a streaming fashion
        
        Args:
            text: The text to convert to speech
            voice_id: Optional voice ID to use
            story_info: Optional dictionary containing universe and title
            
        Returns:
            Async generator yielding chunks of audio data as they're generated
        """
        voice = voice_id or self.voice_id
        
        try:
            # Generate audio for the text
            logger.info(f"Generating streaming audio for text: {text[:50]}...")
            audio_stream = generate(
                text=text,
                voice=str(voice),
                model="eleven_multilingual_v2",
                stream=True
            )
            
            # Yield audio data chunks
            for audio_chunk in audio_stream:
                # Wait a short time to simulate real-time processing
                # await asyncio.sleep(0.01) # Removed this small delay
                # Ensure the audio_chunk is bytes
                if isinstance(audio_chunk, bytes):
                    yield audio_chunk
                else:
                    # Convert to bytes if it's not already
                    yield bytes(str(audio_chunk), 'utf-8')
                    
        except Exception as e:
            logger.error(f"Error in streaming audio generation: {str(e)}")
            # Signal error in the stream
