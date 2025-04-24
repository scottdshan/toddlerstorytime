"""
Converter module for ESP32 to Story schema translation.

This module handles conversion between ESP32 character selection
and the full story generation request format.
"""

from typing import Dict, Any
from app.schemas.story import StoryGenRequest, StoryCharacterInput
import os
from app.serial.esp32 import ESP32Selections

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
    """
    # Build the story request using selections from each display
    character = StoryCharacterInput(character_name=selections.display1.name)
    return StoryGenRequest(
        universe="Paw Patrol",
        setting=selections.display2.name,
        theme=selections.display3.name,
        story_length="short",
        characters=[character],
        child_name=os.environ.get("CHILD_NAME", "Wesley"),
        randomize=False,
        llm_provider=os.environ.get("LLM_PROVIDER", "openai"),
        tts_provider=os.environ.get("TTS_PROVIDER", "elevenlabs"),
        voice_id=os.environ.get("ESP32_VOICE_ID")
    ) 