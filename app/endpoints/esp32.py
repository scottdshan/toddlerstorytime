"""
ESP32 Integration Endpoints.

This module provides endpoints for managing and interacting
with an ESP32 device that selects story characters.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

from app.serial.esp32 import get_esp32_manager, CHARACTER_MAPPING
from app.serial.monitor import start_esp32_monitor, set_voice_id

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

class VoiceIDRequest(BaseModel):
    voice_id: str

@router.get("/status")
async def get_esp32_status():
    """Get the status of the ESP32 connection."""
    manager = get_esp32_manager()
    
    # Check if connected
    is_connected = manager.serial_conn is not None and manager.serial_conn.is_open
    
    # Get available ports
    available_ports = manager.list_available_ports()
    
    return {
        "connected": is_connected,
        "port": manager.port if is_connected else None,
        "available_ports": available_ports,
        "available_characters": list(CHARACTER_MAPPING.values()),
        "message": "ESP32 connected" if is_connected else "ESP32 not connected"
    }

@router.post("/connect")
async def connect_esp32(port: Optional[str] = None):
    """
    Connect to an ESP32 device.
    
    Args:
        port: Optional port to connect to. If not provided, auto-detection will be attempted.
    """
    manager = get_esp32_manager(port)
    success = manager.connect()
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to connect to ESP32. Check the port and device connection."
        )
    
    return {
        "connected": True,
        "port": manager.port,
        "message": f"Successfully connected to ESP32 on port {manager.port}"
    }

@router.post("/disconnect")
async def disconnect_esp32():
    """Disconnect from the ESP32 device."""
    manager = get_esp32_manager()
    manager.disconnect()
    
    return {
        "connected": False,
        "message": "Disconnected from ESP32"
    }

@router.post("/start-monitoring")
async def start_monitoring(background_tasks: BackgroundTasks):
    """
    Start monitoring the ESP32 for character selections in the background.
    
    This endpoint returns immediately but starts a background task that
    continues to monitor the ESP32 until the application is stopped or
    the disconnect endpoint is called.
    """
    manager = get_esp32_manager()
    
    # Ensure the ESP32 is connected
    if not manager.serial_conn or not manager.serial_conn.is_open:
        if not manager.connect():
            raise HTTPException(
                status_code=500,
                detail="Failed to connect to ESP32. Check the port and device connection."
            )
    
    # Start monitoring in the background
    background_tasks.add_task(start_esp32_monitor)
    
    return {
        "status": "monitoring_started",
        "message": "ESP32 monitoring started in the background"
    }

@router.post("/set-voice")
async def set_esp32_voice(request: VoiceIDRequest):
    """
    Set the voice ID to use for ESP32-initiated stories.
    
    Args:
        request: The voice ID request containing the ElevenLabs voice ID
    """
    set_voice_id(request.voice_id)
    
    return {
        "status": "voice_set",
        "voice_id": request.voice_id,
        "message": f"Voice ID for ESP32 stories set to: {request.voice_id}"
    } 