"""
ESP32 Integration Endpoints.

This module provides endpoints for managing and interacting
with an ESP32 device that selects story characters.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi import Body
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
import asyncio

from app.serial.esp32 import get_esp32_manager
from app.serial.monitor import start_esp32_monitor

# Set up logger
logger = logging.getLogger(__name__)

# Options available on each display
AVAILABLE_CHARACTERS = ["Rubble", "Skye", "Marshall"]
AVAILABLE_SETTINGS   = ["Space", "Playground", "Underwater"]
AVAILABLE_THEMES     = ["Listening", "Sleeping", "Exploring"]

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
        "available_characters": AVAILABLE_CHARACTERS,
        "available_settings": AVAILABLE_SETTINGS,
        "available_themes": AVAILABLE_THEMES,
        "message": "ESP32 connected" if is_connected else "ESP32 not connected"
    }

@router.post("/connect")
async def connect_esp32(port: Optional[str] = Body(None, embed=True)):
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
    """Disconnect from the ESP32 device and stop monitoring task."""
    manager = get_esp32_manager()
    # Cancel monitor task if running
    if manager.monitor_task and not manager.monitor_task.done():
        manager.monitor_task.cancel()
        await asyncio.sleep(0)  # allow cancellation to propagate
        manager.monitor_task = None
    manager.disconnect()
    return {
        "connected": False,
        "message": "Disconnected from ESP32"
    }

@router.post("/start-monitoring")
async def start_monitoring(background_tasks: BackgroundTasks):
    """
    Start monitoring the ESP32 for character selections in the background.
    """
    manager = get_esp32_manager()

    # Ensure connected
    if not manager.is_connected and not manager.connect():
        raise HTTPException(status_code=500, detail="Failed to connect to ESP32. Check the port and device connection.")

    # Prevent duplicate monitoring tasks
    if manager.monitor_task and not manager.monitor_task.done():
        return {"status": "already_monitoring"}

    # Create monitoring task
    manager.monitor_task = asyncio.create_task(start_esp32_monitor())
    return {"status": "monitoring_started", "message": "ESP32 monitoring started in background"} 