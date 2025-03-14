from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Any, Optional
import logging
from pydantic import BaseModel

from app.db.database import get_db
from app.db import crud
from app.integrations.home_assistant import HomeAssistantIntegration
from app.config import HOME_ASSISTANT_URL, NETWORK_SHARE_PATH, NETWORK_SHARE_URL

# Set up logger
logger = logging.getLogger(__name__)

# Define request models
class PlayRequest(BaseModel):
    story_id: int
    entity_id: str

class PauseRequest(BaseModel):
    entity_id: str

router = APIRouter()

@router.post("/home-assistant/play", response_model=Dict[str, bool])
async def play_story(play_request: PlayRequest, db: Session = Depends(get_db)):
    """Play a story on a Home Assistant media player"""
    try:
        # Get story from the database
        story = crud.get_story_by_id(db, play_request.story_id)
        if not story:
            logger.error(f"Story with ID {play_request.story_id} not found")
            raise HTTPException(status_code=404, detail="Story not found")
        
        if story.audio_path is None:
            logger.error(f"Story with ID {play_request.story_id} has no audio")
            raise HTTPException(status_code=400, detail="Story has no audio")
        
        # Get just the filename from the audio path
        filename = story.audio_path.split('/')[-1]
        logger.info(f"Original audio path: {story.audio_path}")
        logger.info(f"Extracted filename: {filename}")
        
        # Try different path formats that Home Assistant might be able to access
        # Option 1: Local file path (if Home Assistant has the file locally)
        media_path = f"media-source://media_source/share/story/storyteller/{filename}"
        logger.info(f"Trying local path: {media_path}")
        
        # # # Option 2: Media folder path (if configured in Home Assistant)
        # media_path = f"http://192.168.2.14/music/storyteller/{filename}"
        # # logger.info(f"Trying media source path: {media_path}")
        
        # # Option 3: Network share with SMB protocol
        #smb_path = f"file://192.168.2.14/music/storyteller/{filename}"
        # logger.info(f"Trying SMB path: {smb_path}")
        
        # Let's try the media source path first
        ha_path = media_path
        
        # Log entity ID
        logger.info(f"Target media player entity ID: {play_request.entity_id}")
        
        # Send to Home Assistant
        logger.info("Initializing Home Assistant integration")
        ha = HomeAssistantIntegration()
        
        logger.info("Calling play_story method")
        success = ha.play_story(ha_path, play_request.entity_id)
        
        # # If that didn't work, try the SMB path
        # if not success:
        #     logger.info(f"Media source path failed, trying SMB path")
        #     success = ha.play_story(smb_path, play_request.entity_id)/
        
        # # If that didn't work either, try the local path
        # if not success:
        #     logger.info(f"SMB path failed, trying local path")
        #     success = ha.play_story(local_path, play_request.entity_id)
        
        logger.info(f"Final play story result: {success}")
        
        if not success:
            logger.error("Failed to play story on Home Assistant after trying multiple paths")
            raise HTTPException(status_code=500, detail="Failed to play story on Home Assistant")
        
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error playing story on Home Assistant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/home-assistant/pause", response_model=Dict[str, bool])
async def pause_media(pause_request: PauseRequest):
    """Pause media playback on a Home Assistant media player"""
    try:
        # Log entity ID
        logger.info(f"Pausing media on entity ID: {pause_request.entity_id}")
        
        # Send to Home Assistant
        logger.info("Initializing Home Assistant integration")
        ha = HomeAssistantIntegration()
        
        logger.info("Calling pause_media method")
        success = ha.pause_media(pause_request.entity_id)
        
        logger.info(f"Pause media result: {success}")
        
        if not success:
            logger.error("Failed to pause media on Home Assistant")
            raise HTTPException(status_code=500, detail="Failed to pause media on Home Assistant")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error pausing media on Home Assistant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/home-assistant/play_pause", response_model=Dict[str, bool])
async def play_pause_media(pause_request: PauseRequest):
    """Toggle play/pause state on a Home Assistant media player"""
    try:
        # Log entity ID
        logger.info(f"Toggling play/pause on entity ID: {pause_request.entity_id}")
        
        # Send to Home Assistant
        logger.info("Initializing Home Assistant integration")
        ha = HomeAssistantIntegration()
        
        logger.info("Calling play_pause method")
        success = ha.play_pause(pause_request.entity_id)
        
        logger.info(f"Play/pause media result: {success}")
        
        if not success:
            logger.error("Failed to toggle play/pause on Home Assistant")
            raise HTTPException(status_code=500, detail="Failed to toggle play/pause on Home Assistant")
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error toggling play/pause on Home Assistant: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/home-assistant/status", response_model=Dict[str, bool])
async def get_ha_status():
    """Check if Home Assistant is configured and available"""
    has_config = bool(HOME_ASSISTANT_URL)
    is_available = False
    
    if has_config:
        try:
            ha = HomeAssistantIntegration()
            players = ha.get_media_players()
            is_available = players is not None
        except Exception as e:
            logger.error(f"Error connecting to Home Assistant: {e}")
    
    return {
        "has_config": has_config,
        "is_available": is_available
    }

@router.get("/home-assistant/media-players", response_model=List[Dict[str, Any]])
async def get_media_players():
    """Get available media players from Home Assistant"""
    try:
        ha = HomeAssistantIntegration()
        players = ha.get_media_players()
        
        if not players:
            return []
            
        return players
    except Exception as e:
        logger.error(f"Error fetching media players: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
