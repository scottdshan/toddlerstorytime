from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.db import models

def create_story(db: Session, story_data: Dict[str, Any]) -> models.StoryHistory:
    """
    Create a new story entry in the database
    """
    # Create the story
    db_story = models.StoryHistory(
        universe=story_data.get("universe"),
        setting=story_data.get("setting"),
        theme=story_data.get("theme"),
        story_length=story_data.get("story_length"),
        prompt=story_data.get("prompt"),
        story_text=story_data.get("story_text"),
        audio_path=story_data.get("audio_path"),
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

def get_recent_stories(db: Session, limit: int = 10) -> List[models.StoryHistory]:
    """
    Get the most recent stories
    """
    return db.query(models.StoryHistory).order_by(models.StoryHistory.created_at.desc()).limit(limit).all()

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
            if story.universe:
                if story.universe in frequencies["universes"]:
                    frequencies["universes"][story.universe] += 1
                else:
                    frequencies["universes"][story.universe] = 1
                    
            # Setting frequency
            if story.setting:
                if story.setting in frequencies["settings"]:
                    frequencies["settings"][story.setting] += 1
                else:
                    frequencies["settings"][story.setting] = 1
                    
            # Theme frequency
            if story.theme:
                if story.theme in frequencies["themes"]:
                    frequencies["themes"][story.theme] += 1
                else:
                    frequencies["themes"][story.theme] = 1
                    
            # Character frequency
            for character in story.characters:
                if character.character_name in frequencies["characters"]:
                    frequencies["characters"][character.character_name] += 1
                else:
                    frequencies["characters"][character.character_name] = 1
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
