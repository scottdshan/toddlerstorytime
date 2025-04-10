"""
ESP32 Monitoring Service.

This module provides functionality for monitoring an ESP32 device
and processing character selections to trigger story generation.
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any
import httpx

from app.serial.esp32 import get_esp32_manager, ESP32Selection
from app.serial.converter import esp32_selection_to_story_request

# Set up logger
logger = logging.getLogger(__name__)

# Global flag to track if monitoring is active
_monitoring_active = False

# Global flag to track if a story is currently being generated
_story_generation_in_progress = False

# Default voice ID - can be configured through environment variables
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam

async def process_character_selection(selection: ESP32Selection) -> None:
    """
    Process a character selection from the ESP32.
    
    This function converts the character selection into a story request
    and sends it to the story generation endpoint.
    
    Args:
        selection: The ESP32 character selection
    """
    global _story_generation_in_progress
    
    # Check if a story generation is already in progress
    if _story_generation_in_progress:
        logger.info(f"Ignoring character selection for {selection.character_name} - story generation already in progress")
        return
    
    try:
        # Set the flag to indicate a story is being generated
        _story_generation_in_progress = True
        
        logger.info(f"Processing character selection: {selection.character_name} (index: {selection.character_index})")
        
        # Get voice ID from environment or use default
        voice_id = os.environ.get("ESP32_VOICE_ID", DEFAULT_VOICE_ID)
        logger.info(f"Using voice ID: {voice_id}")
        
        # Convert to story elements request
        story_request = esp32_selection_to_story_request(selection.character_name)
        
        # Override voice ID from environment if available
        if voice_id:
            story_request.voice_id = voice_id
        
        # Use httpx to make an async request to the story endpoint
        # We use the local API to avoid circular dependencies
        async with httpx.AsyncClient() as client:
            logger.info(f"Sending story request for character: {selection.character_name}")
            
            # Use the regular story generation endpoint instead of streaming
            response = await client.post(
                "http://localhost:8000/api/stories/generate",
                json=story_request.dict(),
                timeout=120.0  # Longer timeout for story generation
            )
            
            if response.status_code != 201:
                logger.error(f"Failed to generate story: {response.text}")
            else:
                logger.info(f"Successfully generated story for {selection.character_name}")
                story_data = response.json()
                story_id = story_data.get("id")
                logger.info(f"Story generated with ID: {story_id}")
                
    except Exception as e:
        logger.error(f"Error processing character selection: {str(e)}", exc_info=True)
    finally:
        # Reset the flag to allow new story generations
        _story_generation_in_progress = False
        logger.info("Story generation completed, ready for new requests")

async def start_esp32_monitor() -> None:
    """
    Start monitoring the ESP32 for character selections.
    
    This function runs indefinitely until the application is stopped
    or the monitoring is explicitly disabled.
    """
    global _monitoring_active
    
    # If already monitoring, do nothing
    if _monitoring_active:
        logger.info("ESP32 monitoring already active")
        return
    
    logger.info("Starting ESP32 monitoring")
    _monitoring_active = True
    
    try:
        manager = get_esp32_manager()
        
        # Make sure we're connected
        if not manager.serial_conn or not manager.serial_conn.is_open:
            if not manager.connect():
                logger.error("Failed to connect to ESP32")
                _monitoring_active = False
                return
        
        # Start monitoring for selections
        logger.info("ESP32 monitor started, waiting for selections...")
        await manager.monitor_serial(process_character_selection)
        
    except Exception as e:
        logger.error(f"Error in ESP32 monitor: {str(e)}", exc_info=True)
    finally:
        _monitoring_active = False
        logger.info("ESP32 monitoring stopped")

def stop_esp32_monitor() -> None:
    """Stop the ESP32 monitoring."""
    global _monitoring_active
    
    if _monitoring_active:
        logger.info("Stopping ESP32 monitoring")
        _monitoring_active = False
        
        # Disconnect from the ESP32
        manager = get_esp32_manager()
        manager.disconnect()
    else:
        logger.info("ESP32 monitoring not active")

def set_voice_id(voice_id: str) -> None:
    """
    Set the voice ID to use for ESP32-initiated stories.
    
    Args:
        voice_id: The ElevenLabs voice ID to use
        
    Note:
        The ESP32 monitoring system is configured to handle only one
        story generation at a time. If a new character selection is
        received while a story is already being generated, the new
        selection will be ignored. This prevents overlapping story
        generations and ensures a complete story is generated before
        starting a new one.
    """
    os.environ["ESP32_VOICE_ID"] = voice_id
    logger.info(f"ESP32 voice ID set to: {voice_id}") 