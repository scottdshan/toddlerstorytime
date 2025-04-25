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
import json

from app.serial.esp32 import get_esp32_manager, ESP32Selections
from app.serial.converter import esp32_selection_to_story_request, esp32_selections_to_story_request

# Set up logger
logger = logging.getLogger(__name__)

# Global flag to track if monitoring is active
_monitoring_active = False

# Global flag to track if a story is currently being generated
_story_generation_in_progress = False

async def process_character_selection(selections: ESP32Selections) -> None:
    """
    Process character selections from the ESP32 JSON for all displays.
    
    This function converts the character selection into a story request
    and sends it to the story generation endpoint.
    
    Args:
        selections: The ESP32 selections
    """
    global _story_generation_in_progress
    
    # Check if a story generation is already in progress
    if _story_generation_in_progress:
        logger.info("Ignoring new ESP32 selections - story generation already in progress")
        return
    
    try:
        # Set the flag to indicate story generation in progress
        _story_generation_in_progress = True
        logger.info("Processing ESP32 selections...")

        # Convert all three display selections into a single story request
        story_request = esp32_selections_to_story_request(selections)
        async with httpx.AsyncClient() as client:
            try:
                # Use proper streaming approach with no timeout for the response
                async with client.stream(
                    "POST",
                    "http://localhost:8000/api/stories/generate_and_play_local_streaming",
                    json=story_request.dict(),
                    timeout=None  # No timeout for long stories
                ) as response:
                    if response.status_code != 200:
                        logger.error(f"Failed to generate story: Status {response.status_code}")
                    else:
                        logger.info(f"Successfully started local audio playback (status: {response.status_code})")
                        
                        # Process events from the stream in a non-blocking way
                        try:
                            story_id = None
                            title = None
                            
                            # Read key events up to a reasonable limit (avoid blocking indefinitely)
                            event_count = 0
                            max_events = 100  # Reasonable limit to prevent indefinite waiting
                            
                            async for line in response.aiter_lines():
                                if not line.strip():
                                    continue
                                    
                                # Process only a limited number of events to avoid blocking too long
                                event_count += 1
                                if event_count > max_events:
                                    logger.info(f"Reached max event count ({max_events}), stopping event processing")
                                    break
                                    
                                # Parse SSE format: "data: {...}"
                                if line.startswith("data:"):
                                    try:
                                        event_data = json.loads(line[5:].strip())
                                        # Extract key information
                                        if "event" in event_data and event_data["event"] == "complete":
                                            if "data" in event_data and "story_id" in event_data["data"]:
                                                story_id = event_data["data"]["story_id"]
                                                title = event_data["data"].get("title", "Unknown Title")
                                                logger.info(f"Story completed and saved with ID: {story_id}, Title: {title}")
                                                # Once we have the story ID, we can stop processing events
                                                break
                                        elif "status" in event_data:
                                            logger.info(f"Playback status: {event_data['status']}")
                                            # If we get "Playback complete", we can stop monitoring
                                            if event_data.get('status') == 'Playback complete':
                                                break
                                        elif "error" in event_data:
                                            logger.error(f"Playback error: {event_data['error']}")
                                    except json.JSONDecodeError:
                                        pass  # Skip lines that aren't valid JSON
                        except Exception as stream_err:
                            # Just log the error but don't fail - the endpoint is still working
                            # and the playback is happening on the server
                            logger.error(f"Error processing event stream: {stream_err}")
                            
                        logger.info("Story playback is in progress - monitor complete")
            except Exception as inner_e:
                logger.error(f"Error generating story: {inner_e}", exc_info=True)
    except Exception as e:
        logger.error(f"Error processing ESP32 selections: {e}", exc_info=True)
    finally:
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