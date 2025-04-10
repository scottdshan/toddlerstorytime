"""
ESP32 Schema Models.

This module contains Pydantic models for ESP32-related data structures
and request/response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ESP32CharacterRequest(BaseModel):
    """
    Request model for initiating a story from an ESP32 character selection.
    
    This is a simplified story request with defaults for most parameters,
    focused on the character selection from the ESP32 device.
    """
    character_name: str = Field(..., description="Name of the selected character")
    child_name: Optional[str] = Field("Wesley", description="Name of the child for personalized stories")
    universe: Optional[str] = Field("Paw Patrol", description="Story universe, defaults to Paw Patrol for these characters")
    story_length: Optional[str] = Field("short", description="Length of the story (short/medium/long)")
    audio: Optional[bool] = Field(True, description="Whether to generate audio for the story")
    llm_provider: Optional[str] = Field("openai", description="Language model provider")
    tts_provider: Optional[str] = Field("elevenlabs", description="Text-to-speech provider")
    
    class Config:
        schema_extra = {
            "example": {
                "character_name": "Skye",
                "child_name": "Wesley",
                "universe": "Paw Patrol",
                "story_length": "short",
                "audio": True
            }
        }

class ESP32DeviceInfo(BaseModel):
    """Information about a connected ESP32 device."""
    port: str
    connected: bool
    characters: List[str]

class ESP32StatusResponse(BaseModel):
    """Response model for ESP32 device status."""
    connected: bool
    port: Optional[str] = None
    available_ports: List[str]
    available_characters: List[str]
    message: str 