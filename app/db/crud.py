from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.db import models

def create_story(db: Session, story_data: Dict[str, Any]) -> models.StoryHistory:
    """
    Create a new story entry in the database
    """
    # Create the story with title field 
    db_story = models.StoryHistory(
        title=story_data.get("title", "Bedtime Story"),
        universe=story_data.get("universe"),
        setting=story_data.get("setting"),
        theme=story_data.get("theme"),
        story_length=story_data.get("story_length"),
        prompt=story_data.get("prompt"),
        story_text=story_data.get("story_text"),
        audio_path=story_data.get("audio_path"),
        llm_duration=story_data.get("llm_duration"),
    )
    db.add(db_story)
    db.commit()
    db.refresh(db_story)
    
    # Add characters to the story
    if "characters" in story_data and story_data["characters"]:
        for character in story_data["characters"]:
            if isinstance(character, dict) and "character_name" in character:
                # Extract the character name from the dict
                character_name = character["character_name"]
            else:
                # Use the character as is if it's a string
                character_name = character
                
            db_character = models.StoryCharacter(
                story_id=db_story.id,
                character_name=character_name
            )
            db.add(db_character)
        db.commit()
    
    return db_story

def get_story_by_id(db: Session, story_id: int) -> Optional[models.StoryHistory]:
    """
    Get a story by its ID
    """
    return db.query(models.StoryHistory).filter(models.StoryHistory.id == story_id).first()

def get_recent_stories(db: Session, page: int = 1, items_per_page: int = 10) -> List[models.StoryHistory]:
    """
    Get the most recent stories with pagination
    
    Args:
        db: Database session
        page: Page number (starting from 1)
        items_per_page: Number of items per page
        
    Returns:
        List of stories for the requested page
    """
    # Calculate offset
    offset = (page - 1) * items_per_page
    
    return db.query(models.StoryHistory).order_by(
        models.StoryHistory.created_at.desc()
    ).offset(offset).limit(items_per_page).all()

def get_story_elements_frequency(db: Session, days: int = 14) -> Dict[str, Dict[str, int]]:
    """
    Calculate frequency of story elements to help with randomization
    Returns a dictionary of frequency counts for universes, settings, themes, and characters
    """
    # Calculate date threshold
    threshold_date = datetime.utcnow() - timedelta(days=days)
    
    try:
        # Get recent stories
        recent_stories = db.query(models.StoryHistory).filter(
            models.StoryHistory.created_at >= threshold_date
        ).all()
        
        # Initialize frequency counters
        frequencies = {
            "universes": {},
            "settings": {},
            "themes": {},
            "characters": {}
        }
        
        # Count frequencies
        for story in recent_stories:
            # Universe frequency
            universe = getattr(story, "universe", None)
            if universe:
                if universe in frequencies["universes"]:
                    frequencies["universes"][universe] += 1
                else:
                    frequencies["universes"][universe] = 1
                    
            # Setting frequency
            setting = getattr(story, "setting", None)
            if setting:
                if setting in frequencies["settings"]:
                    frequencies["settings"][setting] += 1
                else:
                    frequencies["settings"][setting] = 1
                    
            # Theme frequency
            theme = getattr(story, "theme", None)
            if theme:
                if theme in frequencies["themes"]:
                    frequencies["themes"][theme] += 1
                else:
                    frequencies["themes"][theme] = 1
                    
            # Character frequency
            for character in story.characters:
                char_name = getattr(character, "character_name", None)
                if char_name:
                    if char_name in frequencies["characters"]:
                        frequencies["characters"][char_name] += 1
                    else:
                        frequencies["characters"][char_name] = 1
    except Exception as e:
        # Handle any database errors or if the table doesn't exist yet
        frequencies = {
            "universes": {},
            "settings": {},
            "themes": {},
            "characters": {}
        }
        
    return frequencies

def save_preferences(db: Session, preferences: Dict[str, Any]) -> models.StoryPreferences:
    """
    Save or update user preferences for stories
    """
    # Check if preferences already exist
    db_preferences = db.query(models.StoryPreferences).first()
    
    if db_preferences:
        # Update existing preferences
        for key, value in preferences.items():
            if hasattr(db_preferences, key):
                setattr(db_preferences, key, value)
    else:
        # Create new preferences
        db_preferences = models.StoryPreferences(**preferences)
        db.add(db_preferences)
    
    db.commit()
    db.refresh(db_preferences)
    return db_preferences

def get_preferences(db: Session) -> Optional[models.StoryPreferences]:
    """
    Get user preferences for stories
    """
    return db.query(models.StoryPreferences).first()

def update_story_audio_path(db: Session, story_id: int, audio_path: str, tts_duration: Optional[float] = None) -> Optional[models.StoryHistory]:
    """
    Update the audio path and TTS duration for a story
    
    Args:
        db: Database session
        story_id: ID of the story to update
        audio_path: New audio path
        tts_duration: Time in seconds taken to generate audio
        
    Returns:
        Updated story object or None if story not found
    """
    story = db.query(models.StoryHistory).filter(models.StoryHistory.id == story_id).first()
    if story is not None:
        # Use setattr instead of direct assignment
        setattr(story, "audio_path", audio_path)
        if tts_duration is not None:
            setattr(story, "tts_duration", tts_duration)
        db.commit()
        db.refresh(story)
    return story

def delete_story(db: Session, story_id: int) -> bool:
    """
    Delete a story and its associated characters
    
    Args:
        db: Database session
        story_id: ID of the story to delete
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # First delete associated characters
        db.query(models.StoryCharacter).filter(models.StoryCharacter.story_id == story_id).delete()
        
        # Then delete the story
        db.query(models.StoryHistory).filter(models.StoryHistory.id == story_id).delete()
        
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise e

def get_story_count(db: Session) -> int:
    """
    Get the total number of stories in the database
    
    Args:
        db: Database session
        
    Returns:
        Total number of stories
    """
    return db.query(models.StoryHistory).count()
