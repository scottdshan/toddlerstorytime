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
    Get frequency of story elements used in recent stories to aid randomization
    """
    # Calculate date threshold
    threshold_date = datetime.utcnow() - timedelta(days=days)
    
    # Get recent stories
    recent_stories = db.query(models.StoryHistory).filter(
        models.StoryHistory.created_at >= threshold_date
    ).all()
    
    # Initialize frequency counters
    frequencies = {
        "universes": {},
        "settings": {},
        "themes": {}
    }
    
    # Count frequencies
    for story in recent_stories:
        # Count universe frequency
        if story.universe is not None:
            frequencies["universes"][story.universe] = frequencies["universes"].get(story.universe, 0) + 1
        
        # Count setting frequency
        if story.setting is not None:
            frequencies["settings"][story.setting] = frequencies["settings"].get(story.setting, 0) + 1
        
        # Count theme frequency
        if story.theme is not None:
            frequencies["themes"][story.theme] = frequencies["themes"].get(story.theme, 0) + 1
    
    # Get character frequencies
    character_counts = {}
    story_characters = db.query(models.StoryCharacter).join(
        models.StoryHistory
    ).filter(
        models.StoryHistory.created_at >= threshold_date
    ).all()
    
    for char in story_characters:
        character_counts[char.character_name] = character_counts.get(char.character_name, 0) + 1
    
    frequencies["characters"] = character_counts
    
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
