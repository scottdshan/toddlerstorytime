from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import os
from pathlib import Path

from app.db.database import get_db
from app.tts.factory import TTSFactory
from app.core.story_generator import StoryGenerator
from app.config import STORY_SETTINGS, AUDIO_DIR

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Create a singleton instance of StoryGenerator (reuse if already created in stories.py)
story_generator = StoryGenerator()

@router.get("/voices")
async def get_available_voices(provider: str = "elevenlabs"):
    """Get available voices for the specified TTS provider"""
    try:
        # Get the TTS provider
        tts = TTSFactory.get_provider(provider)
        
        # Get available voices
        voices = tts.get_available_voices()
        
        return voices
    except Exception as e:
        logger.error(f"Error getting voices: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get voices: {str(e)}"
        )

@router.get("/account-info")
async def get_account_info(provider: Optional[str] = None):
    """
    Get account information for the specified TTS provider
    """
    try:
        # Use the specified provider or default to elevenlabs
        provider_name = provider or "elevenlabs"
        
        # Create a provider instance
        tts_provider = TTSFactory.get_provider(provider_name)
        
        # Get service info
        service_info = tts_provider.get_service_info()
        
        return service_info
    except Exception as e:
        logger.error(f"Error getting account info: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get account info: {str(e)}")

@router.get("/debug/files")
async def list_audio_files():
    """List all audio files in the audio directory for debugging purposes"""
    try:
        # Use AUDIO_DIR from config
        audio_files = []
        
        # Ensure the directory exists
        if not os.path.exists(AUDIO_DIR):
            return {"files": [], "error": f"Audio directory not found: {AUDIO_DIR}"}
        
        # List all files with audio extensions
        for file in os.listdir(AUDIO_DIR):
            if file.endswith((".mp3", ".wav", ".ogg")):
                file_path = os.path.join(AUDIO_DIR, file)
                file_size = os.path.getsize(file_path)
                # Ensure consistent path format with /static/ prefix
                audio_files.append({
                    "name": file,
                    "path": f"/static/audio/{file}",
                    "size": file_size,
                    "size_formatted": f"{file_size / 1024:.2f} KB"
                })
        
        return {
            "files": audio_files, 
            "audio_dir": str(AUDIO_DIR),
            "static_dir": str(AUDIO_DIR.parent),
            "base_dir": str(AUDIO_DIR.parent.parent)
        }
    except Exception as e:
        logger.error(f"Error listing audio files: {str(e)}")
        return {"files": [], "error": str(e)}

@router.post("/generate")
async def generate_audio(request: Dict[str, Any]):
    """
    Generate audio from text or for a specific story
    """
    try:
        # Case 1: Generate audio for a story ID
        if "story_id" in request:
            story_id = request.get("story_id")
            if not story_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Valid story_id is required"
                )
            
            audio_path = story_generator.generate_audio(story_id)
            return {"audio_path": audio_path}
        
        # Case 2: Generate audio for raw text
        elif "text" in request:
            text = request.get("text")
            if not text:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Text is required"
                )
            
            # Use environment variable if provider not specified
            provider = request.get("provider")
            if not provider:
                provider = os.environ.get("TTS_PROVIDER", "elevenlabs")
            
            voice_id = request.get("voice_id")
            
            # Initialize a provider instance
            tts_provider = TTSFactory.get_provider(provider)
            audio_path = tts_provider.generate_audio(text)
            
            return {"audio_path": audio_path}
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either story_id or text must be provided"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate audio: {str(e)}"
        )
