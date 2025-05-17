"""
ESP32 Serial Communication Module.

This module handles serial communication with an ESP32 device that
sends character selections for story generation.
"""
import serial
import serial.tools.list_ports
import asyncio
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ValidationError
import json

logger = logging.getLogger(__name__)

class DisplaySelection(BaseModel):
    """Model for a single display selection from the ESP32 JSON."""
    index: int
    name: str

class ESP32Selections(BaseModel):
    """Model representing selections from all displays via JSON."""
    display1: DisplaySelection
    display2: DisplaySelection
    display3: DisplaySelection

class ESP32SerialManager:
    """Manages serial communication with an ESP32 device."""
    
    def __init__(self, port: Optional[str] = None, baud_rate: int = 115200, timeout: float = 1.0):
        """
        Initialize the serial manager.
        
        Args:
            port: Serial port name. If None, will attempt to auto-detect.
            baud_rate: Baud rate for the serial connection.
            timeout: Read timeout in seconds.
        """
        self.port = port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self.monitor_task: Optional[asyncio.Task] = None
        
    @staticmethod
    def list_available_ports() -> List[str]:
        """List all available serial ports."""
        return [port.device for port in serial.tools.list_ports.comports()]
    
    @staticmethod
    def find_esp32_port() -> Optional[str]:
        """
        Attempt to find an ESP32 device among available serial ports.
        
        Returns:
            The port name if found, None otherwise.
        """
        for port in serial.tools.list_ports.comports():
            # ESP32 often shows up with certain keywords in the description
            if "CP210" in port.description or "CH340" in port.description or "SLAB" in port.description:
                return port.device
        return None
    
    def connect(self) -> bool:
        """
        Connect to the ESP32 device.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # If no port specified, try to find one
            if not self.port:
                self.port = self.find_esp32_port()
                if not self.port:
                    logger.error("No ESP32 device found")
                    return False
            
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=self.timeout
            )
            logger.info(f"Connected to ESP32 on port {self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to ESP32: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the ESP32 device."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("Disconnected from ESP32")
    
    def read_selection(self) -> Optional[ESP32Selections]:
        """
        Read JSON-formatted selections from the ESP32.
        
        Returns:
            ESP32Selections object if successful, None otherwise.
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.error("Not connected to ESP32")
            return None
        
        # Initialize line to ensure it's always defined
        line: str = ""
        
        try:
            # Read a line from the serial port and decode it
            raw = self.serial_conn.readline()
            line = raw.decode('utf-8').strip()
        except Exception as e:
            logger.error(f"Error reading line from serial: {e}")
            return None

        if not line:
            return None

        # Parse JSON and validate
        try:
            data = json.loads(line)
            return ESP32Selections.parse_obj(data)
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from line: {line}")
            return None
        except ValidationError as e:
            logger.error(f"JSON validation error: {e}")
            return None
    
    async def monitor_serial(self, callback) -> None:
        """
        Continuously monitor the serial port for selections.
        
        Args:
            callback: Function to call when a selection is received.
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            if not self.connect():
                return
        
        try:
            while self.serial_conn and self.serial_conn.is_open:
                selection = self.read_selection()
                if selection:
                    await callback(selection)
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.1)
        except Exception as e:
            logger.error(f"Error monitoring serial: {str(e)}")
        finally:
            self.disconnect()

    # New convenience properties -------------------------------------------------
    @property
    def is_connected(self) -> bool:
        """Return True if serial connection is open."""
        return self.serial_conn is not None and self.serial_conn.is_open
    
    @property
    def is_monitoring(self) -> bool:
        """Return True if a monitor task exists and is still running."""
        return self.monitor_task is not None and (not self.monitor_task.done())

    # ---------------------------------------------------------------------------

# Singleton instance
_esp32_manager: Optional[ESP32SerialManager] = None

def get_esp32_manager(port: Optional[str] = None) -> ESP32SerialManager:
    """
    Get or create the ESP32 serial manager singleton.
    
    Args:
        port: Optional port to use for the connection.
        
    Returns:
        The ESP32 serial manager instance.
    """
    global _esp32_manager
    if _esp32_manager is None:
        _esp32_manager = ESP32SerialManager(port=port)
    return _esp32_manager 