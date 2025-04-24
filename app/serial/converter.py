"""
Converter module for ESP32 to Story schema translation.

This module handles conversion between ESP32 character selection
and the full story generation request format.
"""

from typing import Dict, Any, Optional, cast
from sqlalchemy.orm import Session
from app.schemas.story import StoryGenRequest, StoryCharacterInput
import os
from app.serial.esp32 import ESP32Selections
from app.db.database import SessionLocal
from app.db import crud
import logging

logger = logging.getLogger(__name__)

def esp32_selection_to_story_request(character_name: str) -> StoryGenRequest:
    """
    Convert a character selection from ESP32 to a StoryGenRequest.
    
    Args:
        character_name: The name of the selected character
        
    Returns:
        A StoryGenRequest object ready for story generation
    """
    # Create a story character input
    character = StoryCharacterInput(character_name=character_name)
    
    # Default settings based on the character
    setting = "Adventure Bay"
    theme = "rescue mission"
    
    # Customize settings based on character
    character_settings = {
        "Skye": {"setting": "Sky High", "theme": "flying rescue"},
        "Rubble": {"setting": "Construction Site", "theme": "building adventure"},
        "Marshall": {"setting": "Fire Station", "theme": "fire rescue"},
    }
    
    if character_name in character_settings:
        char_setting = character_settings[character_name]
        setting = char_setting["setting"]
        theme = char_setting["theme"]
    
    # Default ElevenLabs voice ID for Adam - change this to your preferred voice
    voice_id = "pNInz6obpgDQGcFmaJgB"
    
    # Build the story request with default values
    return StoryGenRequest(
        universe="Paw Patrol",
        setting=setting,
        theme=theme,
        story_length="short",
        characters=[character],
        child_name="Wesley",  # Default child name
        randomize=False,      # Use defined parameters
        llm_provider="openai", # Use default provider
        tts_provider="elevenlabs", # Use default TTS provider
        voice_id=voice_id     # Specify a voice ID
    )

def esp32_selections_to_story_request(selections: ESP32Selections) -> StoryGenRequest:
    """
    Convert ESP32Selections JSON into a StoryGenRequest with character, setting, and theme.
    Reads preferences from the database to determine providers and voice.
    """
    # Build the story request using selections from each display
    character = StoryCharacterInput(character_name=selections.display1.name)
    
    # Define default values with correct types
    default_child_name = "Wesley"
    default_llm_provider = "openai"
    default_tts_provider = "elevenlabs"
    default_voice_id = None # Or a default like "pNInz6obpgDQGcFmaJgB"
    
    # Get preferences from the database
    db: Session = SessionLocal()
    try:
        preferences = crud.get_preferences(db)
        if preferences:
            logger.info(f"Using preferences for ESP32 story: LLM={preferences.llm_provider}, TTS={preferences.tts_provider}, Voice={preferences.voice_id}")
            # Explicitly cast preference attributes to expected types
            child_name = cast(Optional[str], preferences.child_name) if preferences.child_name is not None else default_child_name
            llm_provider = cast(Optional[str], preferences.llm_provider) if preferences.llm_provider is not None else default_llm_provider
            tts_provider = cast(Optional[str], preferences.tts_provider) if preferences.tts_provider is not None else default_tts_provider
            voice_id = cast(Optional[str], preferences.voice_id) if preferences.voice_id is not None else default_voice_id
        else:
            # Default values if no preferences are set
            logger.warning("No preferences found, using default values for ESP32 story.")
            child_name = default_child_name
            llm_provider = default_llm_provider
            tts_provider = default_tts_provider
            voice_id = default_voice_id
    except Exception as e:
        logger.error(f"Error fetching preferences for ESP32 story: {e}. Using defaults.")
        child_name = default_child_name
        llm_provider = default_llm_provider
        tts_provider = default_tts_provider
        voice_id = default_voice_id
    finally:
        db.close()
        
    return StoryGenRequest(
        universe="Paw Patrol",
        setting=selections.display2.name,
        theme=selections.display3.name,
        story_length="short",
        characters=[character],
        child_name=child_name,
        randomize=False,
        llm_provider=llm_provider,
        tts_provider=tts_provider,
        voice_id=voice_id
    ) 