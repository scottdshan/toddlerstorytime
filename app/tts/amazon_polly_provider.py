import os
import logging
import uuid
import re
import glob
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Dict, Any

from app.tts.base import TTSProvider
from app.config import AUDIO_DIR, NETWORK_SHARE_PATH, NETWORK_SHARE_URL

logger = logging.getLogger(__name__)

class AmazonPollyProvider(TTSProvider):
    """
    TTS provider implementation using Amazon Polly.
    """
    
    def __init__(self, voice_id: Optional[str] = None):
        """
        Initialize the Amazon Polly provider
        
        Args:
            voice_id: Optional voice ID to use (defaults to "Joanna")
        """
        # Use environment variables for AWS credentials if not using instance profile
        self.aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.environ.get("AWS_REGION", "us-east-1")
        
        # Initialize Polly client
        self.polly = self._create_polly_client()
        
        # Set default voice ID
        self.voice_id = voice_id or "Joanna"
        
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
        
        logger.info(f"Initialized Amazon Polly Provider with default voice {self.voice_id}")

    def _create_polly_client(self):
        """
        Create and return the Polly client
        
        Returns:
            Boto3 Polly client
        """
        try:
            # Verify AWS credentials are available
            if not self.aws_access_key or not self.aws_secret_key:
                logger.warning("AWS credentials not found. Make sure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY are set in your environment.")
            
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region
            )
            return session.client('polly')
        except Exception as e:
            logger.error(f"Failed to create Polly client: {e}")
            # Return a minimal client that will fail gracefully when used
            return boto3.Session().client('polly')
    
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
        Generate audio from text using Amazon Polly
        
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
            
            # Check if the voice_id looks like an ElevenLabs ID (not a valid Polly voice)
            # ElevenLabs IDs are typically longer random strings
            if selected_voice_id and len(selected_voice_id) > 10 and not selected_voice_id.isalpha():
                logger.warning(f"Received what appears to be a non-Polly voice ID: {selected_voice_id}. Using default Polly voice instead.")
                selected_voice_id = "Joanna"  # Fall back to default Polly voice
            
            # Create a user-friendly filename if story_info is provided
            if story_info and story_info.get('universe') and story_info.get('title'):
                filename = self._create_friendly_filename(
                    story_info.get('universe', 'unknown'), 
                    story_info.get('title', 'story')
                )
            else:
                # Fallback to UUID if story_info is not provided
                filename = f"polly_{uuid.uuid4()}.mp3"
                
            # Local file path
            local_file_path = os.path.join(self.output_dir, filename)
            # Network file path
            network_file_path = os.path.join(self.network_share_path, filename)
            # Local URL path (for web app)
            local_url_path = f"/static/audio/{filename}"
            # Network URL (for Home Assistant)
            network_url_path = f"{NETWORK_SHARE_URL}/{filename}"
            
            logger.info(f"Using Amazon Polly voice: {selected_voice_id}")
            
            # Generate speech
            response = self.polly.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId=selected_voice_id,
                Engine='neural'  # Use neural engine for better quality
            )
            
            # Save the audio file to both locations
            if "AudioStream" in response:
                audio_data = response['AudioStream'].read()
                
                # Save to local path
                with open(local_file_path, 'wb') as file:
                    file.write(audio_data)
                logger.info(f"Generated audio file at {local_file_path}")
                
                # Save to network share if available
                if self.network_share_available:
                    try:
                        with open(network_file_path, 'wb') as file:
                            file.write(audio_data)
                        logger.info(f"Copied audio file to network share at {network_file_path}")
                        
                        # Return network URL for Home Assistant
                        # The format in the database will be audio/filename.mp3, keep consistent
                        return local_url_path.replace('/static/', '')
                    except Exception as e:
                        logger.error(f"Failed to save to network share: {e}")
                        # Continue with local path
                
                logger.info(f"Audio URL path: {local_url_path}")
                return local_url_path.replace('/static/', '')
            else:
                logger.error("No AudioStream found in response")
                return None
                
        except ClientError as e:
            logger.error(f"Error generating audio with Amazon Polly: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Unexpected error generating audio: {e}", exc_info=True)
            return None
    
    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get a list of available voices from Amazon Polly
        
        Returns:
            List of voice dictionaries with voice_id and name
        """
        try:
            # Get the list of voices that support neural engine
            response = self.polly.describe_voices(
                Engine='neural',
                LanguageCode='en-US'  # Filter for English voices, can be parameterized later
            )
            
            voices = []
            if 'Voices' in response:
                for voice in response['Voices']:
                    voices.append({
                        'voice_id': voice['Id'],
                        'name': voice['Name'],
                        'gender': voice['Gender'],
                        'language': voice['LanguageCode'],
                        'engine': 'neural'
                    })
            
            return voices
            
        except ClientError as e:
            logger.error(f"Error getting available voices from Amazon Polly: {e}", exc_info=True)
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting voices: {e}", exc_info=True)
            return []
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get information about the Amazon Polly service
        
        Returns:
            Dictionary with service information
        """
        return {
            'service': 'Amazon Polly',
            'description': 'Amazon Polly is a cloud service that converts text into lifelike speech.',
            'voices_available': len(self.get_available_voices()),
            'default_voice': self.voice_id,
            'aws_region': self.aws_region
        } 