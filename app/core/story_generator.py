import logging
import os
import json
import uuid
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from sqlalchemy.orm import Session

from app.llm.factory import LLMFactory
from app.tts.factory import TTSFactory
from app.core.randomizer import StoryRandomizer
from app.config import STORY_SETTINGS
from app.db import crud
from app.db.database import get_db

logger = logging.getLogger(__name__)

class StoryGenerator:
    """
    Class responsible for generating stories using LLM and TTS services
    """
    
    def __init__(self):
        """Initialize story generation components"""
        try:
            # Get a database session
            self.db = next(get_db())
            
            # Default provider names
            llm_provider_name = os.environ.get("LLM_PROVIDER", "openai")
            tts_provider_name = os.environ.get("TTS_PROVIDER", "elevenlabs")
            
            logger.info(f"Initializing StoryGenerator with LLM: {llm_provider_name}, TTS: {tts_provider_name}")
            
            # Use get_provider from LLMFactory with fallback options
            try:
                self.llm_provider = LLMFactory.get_provider(llm_provider_name)
            except ValueError as e:
                logger.warning(f"Error creating LLM provider '{llm_provider_name}': {e}")
                logger.info("Falling back to OpenAI provider")
                self.llm_provider = LLMFactory.get_provider("openai")
            
            # Use get_provider from TTSFactory with fallback options
            try:
                logger.info(f"Attempting to initialize TTS provider: {tts_provider_name}")
                self.tts_provider = TTSFactory.get_provider(tts_provider_name)
                logger.info(f"Successfully initialized TTS provider: {tts_provider_name}")
            except Exception as e:
                logger.error(f"Error creating TTS provider '{tts_provider_name}': {str(e)}", exc_info=True)
                
                # Check for TTS_FALLBACK_PROVIDER environment variable or use "none" for testing
                fallback_provider = os.environ.get("TTS_FALLBACK_PROVIDER", "none")
                logger.info(f"Falling back to {fallback_provider} TTS provider")
                try:
                    self.tts_provider = TTSFactory.get_provider(fallback_provider)
                except Exception as fallback_error:
                    logger.error(f"Error creating fallback TTS provider: {str(fallback_error)}")
                    # Ultimate fallback to NoneProvider
                    from app.tts.none_provider import NoneProvider
                    self.tts_provider = NoneProvider()
                    logger.info("Using NoneProvider as last resort fallback")
            
            # Initialize randomizer with DB session
            self.randomizer = StoryRandomizer(self.db)
            
            logger.info(f"StoryGenerator initialized with {self.llm_provider.__class__.__name__} and {self.tts_provider.__class__.__name__}")
        except Exception as e:
            logger.error(f"Error initializing StoryGenerator: {e}", exc_info=True)
            raise
        
    def generate_story(self, universe: Optional[str] = None, 
                      setting: Optional[str] = None,
                      theme: Optional[str] = None,
                      characters: Optional[Union[List[str], List[Dict[str, str]], str]] = None,
                      story_length: Optional[str] = None,
                      child_name: Optional[str] = None,
                      preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a new story with the given parameters
        
        Args:
            universe: Story universe (e.g., "Disney", "Paw Patrol")
            setting: Story setting (e.g., "Beach", "Space")
            theme: Story theme (e.g., "Friendship", "Courage")
            characters: List of character names or character objects
            story_length: Length of story (e.g., "Short (3-5 minutes)")
            child_name: Name of the child to include in the story
            preferences: Optional dictionary of user preferences
            
        Returns:
            Dictionary containing story details
        """
        try:
            # Log the incoming parameters
            logger.info(f"Generating story with: Universe={universe}, Setting={setting}, Theme={theme}, "
                       f"Characters={characters}, Length={story_length}, Child={child_name}")
            
            # Format characters if provided as string
            if characters and isinstance(characters, str):
                characters = [c.strip() for c in characters.split(",")]
            
            # Create a request dictionary with the story elements
            story_request = {
                "universe": universe or "",
                "setting": setting or "",
                "theme": theme or "",
                "characters": characters or [],
                "story_length": story_length or "Short (3-5 minutes)",
                "child_name": child_name or "Wesley",
                "randomize": True if not (universe and setting and theme and characters) else False
            }
            
            # Apply preferences and randomization
            if story_request["randomize"]:
                # Get randomized elements
                random_elements = self.randomizer.randomize_story_elements()
                
                # Apply preferences if provided
                if preferences:
                    story_elements = self.randomizer.apply_preferences(random_elements, preferences)
                else:
                    story_elements = random_elements
                    
                # Update the request with randomized elements
                story_request.update(story_elements)
            else:
                # Use provided elements directly
                story_elements = story_request.copy()
            
            # Set child's name if provided
            if child_name:
                story_elements["child_name"] = child_name
            
            # Generate story text using LLM provider
            logger.debug(f"Calling LLM provider with elements: {story_elements}")
            generated_content = self.llm_provider.generate_story(story_elements)
            
            # Extract content from response
            story_text = generated_content.get("story_text", "")
            prompt = generated_content.get("prompt", "")
            
            # Extract title from first line if possible
            title = "Bedtime Story"
            story_lines = story_text.strip().split("\n")
            if story_lines and not story_lines[0].startswith("Once upon a time"):
                title = story_lines[0].strip()
                # Remove common title markers
                for marker in ["Title:", "# ", "## "]:
                    if title.startswith(marker):
                        title = title[len(marker):].strip()
            
            # Create a unique ID for this story
            story_id = str(uuid.uuid4())
            
            # Format characters as objects
            formatted_characters = []
            if isinstance(story_elements.get("characters"), list):
                # Convert all characters to objects with character_name property
                char_id = 1
                for char in story_elements["characters"]:
                    if isinstance(char, dict) and "character_name" in char:
                        # Already in correct format - extract just the name
                        char_name = char["character_name"]
                        # Ensure we have a string, not another dict
                        if isinstance(char_name, str):
                            formatted_characters.append({
                                "character_name": char_name,
                                "id": char_id,
                                "story_id": story_id
                            })
                        char_id += 1
                    else:
                        # Convert to object format
                        formatted_characters.append({
                            "character_name": str(char),
                            "id": char_id,
                            "story_id": story_id
                        })
                        char_id += 1
            
            # Prepare story object for database
            story_data = {
                "universe": story_elements.get("universe", ""),
                "setting": story_elements.get("setting", ""),
                "theme": story_elements.get("theme", ""),
                "story_length": story_elements.get("story_length", ""),
                "characters": formatted_characters,
                "prompt": prompt,
                "story_text": story_text,
                "audio_path": None,  # Will be set if/when audio is generated
                "child_name": story_elements.get("child_name", ""),
            }
            
            # Save to database
            db_story = crud.create_story(self.db, story_data)
            logger.info(f"Story generated and saved with ID: {db_story.id}")
            
            # Format the response to match the expected schema
            story_obj = {
                "id": db_story.id,
                "title": title,
                "universe": db_story.universe,
                "setting": db_story.setting,
                "theme": db_story.theme,
                "characters": [
                    {"character_name": char.character_name, "id": char.id, "story_id": char.story_id}
                    for char in db_story.characters
                ],
                "story_text": db_story.story_text,
                "prompt": db_story.prompt,
                "story_length": db_story.story_length,
                "child_name": db_story.child_name if hasattr(db_story, "child_name") else story_elements.get("child_name", ""),
                "audio_path": db_story.audio_path,
                "created_at": db_story.created_at
            }
            
            return story_obj
            
        except Exception as e:
            logger.error(f"Error generating story: {str(e)}", exc_info=True)
            raise
    
    def generate_audio(self, story_id: Union[str, int]) -> str:
        """
        Generate audio for a story
        
        Args:
            story_id: ID of the story to generate audio for (can be string or integer)
            
        Returns:
            Path to the generated audio file
        """
        try:
            # Convert string ID to integer if necessary
            numeric_id = int(story_id) if isinstance(story_id, str) else story_id
            
            # Retrieve story from database
            story = crud.get_story_by_id(self.db, numeric_id)
            if not story:
                raise ValueError(f"Story with ID {story_id} not found")
            
            # Get voice ID from environment variable if set
            voice_id = os.environ.get("TTS_VOICE_ID")
            
            # Generate audio using TTS provider
            audio_path = self.tts_provider.generate_audio(str(story.story_text), voice_id=voice_id)
            
            # Update story with audio path in database - remove /static/ prefix for storage
            if audio_path:
                # Standardize the path by removing /static/ prefix if present
                db_path = audio_path.replace('/static/', '') if audio_path.startswith('/static/') else audio_path
                
                # Use setattr for SQLAlchemy models to avoid type errors
                setattr(story, "audio_path", db_path)
                self.db.commit()
                
                logger.info(f"Updated story {story_id} with audio path: {db_path}")
            
            return audio_path or ""
            
        except Exception as e:
            logger.error(f"Error generating audio: {str(e)}", exc_info=True)
            return ""
    
    def get_recent_stories(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a list of recently generated stories
        
        Args:
            limit: Maximum number of stories to retrieve
            
        Returns:
            List of story objects
        """
        try:
            db_stories = crud.get_recent_stories(self.db, limit)
            
            # Convert SQLAlchemy objects to dictionaries
            stories = []
            for story in db_stories:
                stories.append({
                    "id": story.id,
                    "universe": story.universe,
                    "setting": story.setting,
                    "theme": story.theme,
                    "story_length": story.story_length,
                    "created_at": story.created_at,
                    "audio_path": story.audio_path
                })
            
            return stories
        except Exception as e:
            logger.error(f"Error retrieving recent stories: {str(e)}", exc_info=True)
            return []
