from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import logging
import os

from app.db.database import get_db
from app.schemas.story import (
    StoryGenRequest, 
    StoryResponse, 
    StoryHistoryResponse,
    StoryPreferencesCreate,
    StoryPreferences
)
from app.core.story_generator import StoryGenerator
from app.db import crud

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Create a singleton instance of StoryGenerator
story_generator = StoryGenerator()

@router.post("/generate", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def generate_story(story_request: StoryGenRequest, db: Session = Depends(get_db)):
    """
    Generate a new story based on the provided parameters
    """
    try:
        logger.info(f"Story generation request received: {story_request.dict()}")
        
        # Set environment variables if needed for provider selection
        if story_request.llm_provider:
            os.environ["LLM_PROVIDER"] = story_request.llm_provider
            
        if story_request.tts_provider:
            os.environ["TTS_PROVIDER"] = story_request.tts_provider
            
        # Set voice ID if provided
        if story_request.voice_id:
            os.environ["TTS_VOICE_ID"] = story_request.voice_id
            
        # If using Azure OpenAI, check if we need to set deployment name
        if story_request.llm_provider and story_request.llm_provider.lower() in ["azure", "azure_openai"] and story_request.deployment_name:
            os.environ["AZURE_OPENAI_DEPLOYMENT"] = story_request.deployment_name
        
        # Get user preferences
        preferences = crud.get_preferences(db)
        pref_dict = None
        if preferences:
            pref_dict = {
                "child_name": preferences.child_name,
                "favorite_universe": preferences.favorite_universe,
                "favorite_character": preferences.favorite_character,
                "favorite_setting": preferences.favorite_setting,
                "favorite_theme": preferences.favorite_theme,
                "preferred_story_length": preferences.preferred_story_length
            }
        
        # Extract characters from the request and convert to the format expected by StoryGenerator
        characters = []
        if story_request.characters:
            # Convert StoryCharacterInput objects to simple character names
            characters = [char.character_name for char in story_request.characters]
        
        # Try to generate story with preferred provider, with fallback to OpenAI if needed
        try:
            logger.info(f"Generating story with {os.environ.get('LLM_PROVIDER', 'default provider')}")
            
            # Call the generator with extracted parameters
            story = story_generator.generate_story(
                universe=story_request.universe,
                setting=story_request.setting,
                theme=story_request.theme,
                characters=characters,
                story_length=story_request.story_length,
                child_name=story_request.child_name,
                preferences=pref_dict
            )
            
            # Generate audio if story created successfully
            if story and story.get("id"):
                try:
                    audio_path = story_generator.generate_audio(story["id"])
                    story["audio_path"] = audio_path
                except Exception as audio_err:
                    logger.error(f"Audio generation error: {str(audio_err)}")
                    # Continue without audio
            
            return story
            
        except Exception as provider_err:
            # Log error and attempt fallback to OpenAI if not already using it
            logger.warning(f"Provider error: {str(provider_err)}. Attempting fallback to OpenAI.")
            
            if os.environ.get("LLM_PROVIDER", "").lower() != "openai":
                os.environ["LLM_PROVIDER"] = "openai"
                
                # Try again with OpenAI
                story = story_generator.generate_story(
                    universe=story_request.universe,
                    setting=story_request.setting,
                    theme=story_request.theme,
                    characters=characters,
                    story_length=story_request.story_length,
                    child_name=story_request.child_name,
                    preferences=pref_dict
                )
                
                # Generate audio if requested
                if story and story.get("id"):
                    try:
                        audio_path = story_generator.generate_audio(story["id"])
                        story["audio_path"] = audio_path
                    except Exception as audio_err:
                        logger.error(f"Audio generation error: {str(audio_err)}")
                        # Continue without audio
                
                return story
            else:
                # If already using OpenAI, re-raise the exception
                raise
            
    except Exception as e:
        error_msg = f"Failed to generate story: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg
        )

@router.get("/history", response_model=List[StoryHistoryResponse])
async def get_story_history(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get the history of generated stories
    """
    try:
        # Use the CRUD function instead of story_generator.get_recent_stories
        stories = crud.get_recent_stories(db, limit)
        
        # Format the response to match the expected schema
        formatted_stories = []
        for story in stories:
            formatted_story = {
                "id": story.id,
                "universe": story.universe,
                "setting": story.setting,
                "theme": story.theme,
                "story_length": story.story_length,
                "characters": [
                    {"character_name": char.character_name, "id": char.id, "story_id": char.story_id}
                    for char in story.characters
                ],
                "prompt": story.prompt,
                "story_text": story.story_text,
                "audio_path": story.audio_path,
                "created_at": story.created_at
            }
            formatted_stories.append(formatted_story)
            
        return formatted_stories
    except Exception as e:
        logger.error(f"Error retrieving story history: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve story history: {str(e)}"
        )

@router.get("/recent", response_model=List[StoryHistoryResponse])
async def get_recent_stories(limit: int = 10, db: Session = Depends(get_db)):
    """
    Get recent stories (alias for history endpoint)
    """
    return await get_story_history(limit, db)

@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str):
    """
    Get a specific story by ID
    """
    try:
        # Convert string ID to integer
        try:
            numeric_id = int(story_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid story ID format: {story_id}. Must be an integer."
            )
            
        # We now use the DB session inside the StoryGenerator
        story = crud.get_story_by_id(story_generator.db, numeric_id)
        
        if not story:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with ID {story_id} not found"
            )
        
        # Format the response to match the expected schema
        formatted_story = {
            "id": story.id,
            "universe": story.universe,
            "setting": story.setting,
            "theme": story.theme,
            "story_length": story.story_length,
            "characters": [
                {"character_name": char.character_name, "id": char.id, "story_id": char.story_id}
                for char in story.characters
            ],
            "prompt": story.prompt,
            "story_text": story.story_text,
            "audio_path": story.audio_path,
            "created_at": story.created_at
        }
        
        return formatted_story
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving story: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve story: {str(e)}"
        )

@router.post("/preferences", response_model=StoryPreferences)
async def save_preferences(preferences: StoryPreferencesCreate, db: Session = Depends(get_db)):
    """
    Save user preferences for story generation
    """
    try:
        db_preferences = crud.save_preferences(db, preferences.dict())
        return db_preferences
    except Exception as e:
        logger.error(f"Error saving preferences: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save preferences: {str(e)}"
        )

@router.get("/preferences", response_model=StoryPreferences)
async def get_preferences(db: Session = Depends(get_db)):
    """
    Get user preferences for story generation
    """
    try:
        preferences = crud.get_preferences(db)
        
        if not preferences:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preferences found"
            )
        
        return preferences
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving preferences: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve preferences: {str(e)}"
        )
