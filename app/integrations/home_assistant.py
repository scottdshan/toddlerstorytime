import logging
import requests
from typing import Dict, Any, Optional, List, cast
from urllib.parse import urljoin
import os

from app.config import HOME_ASSISTANT_URL, HOME_ASSISTANT_TOKEN

logger = logging.getLogger(__name__)

class HomeAssistantIntegration:
    """
    Integration with Home Assistant to send stories to media players
    and control satellite devices.
    """
    
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize Home Assistant integration.
        
        Args:
            base_url: Home Assistant URL (defaults to config value)
            token: Home Assistant long-lived access token (defaults to config value)
        """
        self.base_url = base_url if base_url is not None else HOME_ASSISTANT_URL
        self.token = token if token is not None else HOME_ASSISTANT_TOKEN
        
        if not self.base_url or not self.token:
            raise ValueError("Home Assistant URL and token must be configured")
        
        # Ensure base URL ends with trailing slash
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        
        self._headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
    
    def _make_request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make a request to the Home Assistant API.
        
        Args:
            endpoint: API endpoint (without leading slash)
            method: HTTP method
            data: Data to send with request
            
        Returns:
            Response data or None if request failed
        """
        # Fix for mypy: ensure base_url is not None before calling urljoin
        base_url = self.base_url or ""
        url = urljoin(base_url, f"api/{endpoint}")
        
        try:
            if method.upper() == "GET":
                print(f"GET request to {url}")
                response = requests.get(url, headers=self._headers, timeout=10)
            elif method.upper() == "POST":
                print(f"POST request to {url} with data: {data}")
                response = requests.post(url, headers=self._headers, json=data, timeout=10)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None
            
            response.raise_for_status()
            return response.json() if response.content else None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Home Assistant: {e}")
            return None
    
    def get_media_players(self) -> List[Dict[str, Any]]:
        """
        Get list of available media player entities.
        
        Returns:
            List of media player entities with formatted information
        """
        states = self._make_request("states")
        if not states:
            return []
        
        # Filter for media_player entities and format them
        media_players = []
        for entity in states:
            if isinstance(entity, dict) and entity.get("entity_id", "").startswith("media_player."):
                entity_id = entity.get("entity_id", "")
                # Get friendly name from attributes, or fallback to ID
                attributes = entity.get("attributes", {})
                friendly_name = attributes.get("friendly_name", entity_id.replace("media_player.", "").replace("_", " ").title())
                
                # Format the player information for the UI
                media_player = {
                    "entity_id": entity_id,
                    "name": friendly_name,
                    "state": entity.get("state", "unknown"),
                    "supported_features": attributes.get("supported_features", 0),
                    "device_class": attributes.get("device_class", ""),
                    "volume_level": attributes.get("volume_level", None)
                }
                media_players.append(media_player)
                
        return media_players
    
    def play_story(self, story_path: str, entity_id: str) -> bool:
        """
        Play a story on a specific media player.
        
        Args:
            story_path: Path to the story audio file within Home Assistant
            entity_id: The media_player entity ID to play on
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Using path: {story_path}")
        
        # Determine media content type based on path
        media_content_type = "audio/mp3"  # Default
        
        if story_path.startswith("media-source://"):
            media_content_type = "media_source"
            logger.info("Using media_source content type")
        elif story_path.startswith("smb://"):
            media_content_type = "music"
            logger.info("Using music content type for SMB path")
        elif story_path.startswith("/config/"):
            media_content_type = "music"
            logger.info("Using music content type for local path")
        
        service_data = {
            "entity_id": entity_id,
            "media_content_id": story_path,
            "media_content_type": media_content_type
        }
        
        logger.info(f"Sending play request to Home Assistant: {service_data}")
        logger.info(f"Home Assistant URL: {self.base_url}")
        
        try:
            # Fix for mypy: ensure base_url is not None before calling urljoin
            base_url = self.base_url or ""
            url = urljoin(base_url, f"api/services/media_player/play_media")
            logger.info(f"Full request URL: {url}")
            
            response = requests.post(
                url, 
                headers=self._headers, 
                json=service_data, 
                timeout=10
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content: {response.content}")
            
            response.raise_for_status()
            
            # Even if response is empty, return True if status code is successful
            return response.status_code < 400
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Home Assistant: {e}")
            return False
    
    def send_notification(self, message: str, targets: Optional[List[str]] = None) -> bool:
        """
        Send a notification to Home Assistant.
        
        Args:
            message: Notification message
            targets: List of target device IDs (optional)
            
        Returns:
            True if successful, False otherwise
        """
        service_data: Dict[str, Any] = {
            "message": message
        }
        
        if targets:
            service_data["target"] = targets
        
        response = self._make_request(
            "services/notify/notify",
            method="POST",
            data=service_data
        )
        
        return response is not None
    
    def pause_media(self, entity_id: str) -> bool:
        """
        Pause media playback on a specific media player.
        
        Args:
            entity_id: The media_player entity ID to pause
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Pausing media on entity: {entity_id}")
        
        service_data = {
            "entity_id": entity_id
        }
        
        logger.info(f"Sending pause request to Home Assistant: {service_data}")
        
        try:
            # Fix for mypy: ensure base_url is not None before calling urljoin
            base_url = self.base_url or ""
            url = urljoin(base_url, f"api/services/media_player/media_pause")
            logger.info(f"Full request URL: {url}")
            
            response = requests.post(
                url, 
                headers=self._headers, 
                json=service_data, 
                timeout=10
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content: {response.content}")
            
            response.raise_for_status()
            
            # Even if response is empty, return True if status code is successful
            return response.status_code < 400
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Home Assistant: {e}")
            return False
    
    def play_pause(self, entity_id: str) -> bool:
        """
        Toggle play/pause state on a specific media player.
        
        Args:
            entity_id: The media_player entity ID to toggle play/pause
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Toggling play/pause on entity: {entity_id}")
        
        service_data = {
            "entity_id": entity_id
        }
        
        logger.info(f"Sending play_pause request to Home Assistant: {service_data}")
        
        try:
            # Fix for mypy: ensure base_url is not None before calling urljoin
            base_url = self.base_url or ""
            url = urljoin(base_url, f"api/services/media_player/media_play_pause")
            logger.info(f"Full request URL: {url}")
            
            response = requests.post(
                url, 
                headers=self._headers, 
                json=service_data, 
                timeout=10
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response content: {response.content}")
            
            response.raise_for_status()
            
            # Even if response is empty, return True if status code is successful
            return response.status_code < 400
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error communicating with Home Assistant: {e}")
            return False 