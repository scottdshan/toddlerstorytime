from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import crud
from app.schemas.story import StoryPreferencesCreate, StoryPreferencesResponse
import logging
import os

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/", response_model=StoryPreferencesResponse)
async def get_preferences(db: Session = Depends(get_db)):
    """
    Get the current user preferences
    """
    preferences = crud.get_preferences(db)
    if not preferences:
        # Create default preferences if none exist
        default_preferences = {
            "child_name": "Wesley",
            "favorite_universe": "Fantasy",
            "favorite_character": "Dragon",
            "favorite_setting": "Castle",
            "favorite_theme": "Adventure",
            "preferred_story_length": "medium",
            "llm_provider": "openai",
            "voice_id": None
        }
        
        preferences = crud.save_preferences(db, default_preferences)
        
    return preferences

@router.post("/", response_model=StoryPreferencesResponse, status_code=status.HTTP_201_CREATED)
async def save_preferences(preferences: StoryPreferencesCreate, db: Session = Depends(get_db)):
    """
    Save user preferences
    """
    try:
        prefs_dict = preferences.dict()
        
        # Log if local_api_url is being saved
        if preferences.llm_provider == "local" and preferences.local_api_url:
            logger.info(f"Saving Local OpenAI API URL: {preferences.local_api_url}")
            os.environ["LOCAL_OPENAI_API_URL"] = preferences.local_api_url
        
        result = crud.save_preferences(db, prefs_dict)
        return result
    except Exception as e:
        logger.error(f"Error saving preferences: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error saving preferences: {str(e)}") 