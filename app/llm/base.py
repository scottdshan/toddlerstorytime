from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import random
import os
from pathlib import Path
import logging

from app.core.story_seed_bank import StorySeedBank

# Initialize logging
logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    All LLM implementations should inherit from this class.
    """
    
    def __init__(self):
        """Initialize the LLM provider with a StorySeedBank"""
        # Initialize the story seed bank with a cache file in the app data directory
        cache_dir = os.environ.get("STORY_SEED_CACHE_DIR", "app/data/cache")
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        self.seed_bank = StorySeedBank(
            cache_file_path=os.path.join(cache_dir, "story_seeds.json")
        )
        logger.info("Initialized LLM provider with story seed bank")
    
    @abstractmethod
    def generate_story(self, story_elements: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a story based on provided elements
        
        Args:
            story_elements: Dictionary containing story elements (universe, setting, theme, etc.)
            
        Returns:
            Dictionary containing the generated story text and the prompt used
        """
        pass
    
    def create_story_prompt(self, story_elements: Dict[str, Any]) -> str:
        """
        Create a prompt for story generation based on provided elements.
        Common implementation that can be used by all providers.
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Formatted prompt string for story generation
        """
        # Extract story elements
        universe = story_elements.get("universe", "Magical World")
        setting = story_elements.get("setting", "Enchanted Forest")
        theme = story_elements.get("theme", "Friendship")
        characters = story_elements.get("characters", [])
        story_length = story_elements.get("story_length", "Short (3-5 minutes)")
        child_name = story_elements.get("child_name", "Wesley")
        
        # Generate a unique story scenario using the seed bank
        character_names = []
        if isinstance(characters, list):
            # If characters is already a list, extract names
            if characters and isinstance(characters[0], dict) and "character_name" in characters[0]:
                # Extract only string names, not objects
                for c in characters:
                    if isinstance(c, dict) and "character_name" in c:
                        name = c["character_name"]
                        if isinstance(name, str):
                            character_names.append(name)
            else:
                character_names = [str(c) for c in characters]
        elif isinstance(characters, str):
            # If characters is a string, split it
            character_names = [c.strip() for c in characters.split(",")]
            
        # Ensure the child's name is included in characters if appropriate
        if child_name and child_name not in character_names:
            character_names.append(child_name)
        
        # Ensure we have at least one character
        if not character_names:
            character_names = ["The main character"]
            
        # Generate a specific scenario for this story
        specific_scenario = self.seed_bank.get_specific_scenario(
            theme=theme,
            setting=setting,
            characters=character_names
        )
        
        # Generate a unique random seed for this story to ensure variation
        # Even with the same parameters, this will help the LLM generate different content
        story_seed = random.randint(1, 1000000)
        
        # Format characters into string
        characters_str = ", ".join(character_names)
        
        # Determine target length in words based on story_length
        if "Very Short" in story_length:
            target_words = 300  # About 2-3 minutes when read aloud
        elif "Short" in story_length:
            target_words = 600  # About 3-5 minutes when read aloud
        elif "Medium" in story_length:
            target_words = 900  # About 5-7 minutes when read aloud
        else:  # Long
            target_words = 1200  # About 7-10 minutes when read aloud
        
        # Craft prompt with the specific scenario
        prompt = f"""
        Create a bedtime story for a toddler named {child_name} with the following elements:
        
        Universe: {universe}
        Setting: {setting}
        Theme: {theme}
        Characters: {characters_str}
        
        SPECIFIC SCENARIO TO USE: {specific_scenario}
        
        Story should be approximately {target_words} words, designed to take about {story_length} to read aloud.
        
        Make the story age-appropriate for a toddler (2-4 years old), with simple language, short sentences, 
        and a clear beginning, middle, and end. Incorporate repetition, simple morals, and gentle humor.
        
        The story should engage a toddler's imagination while being soothing and appropriate for bedtime.
        Any conflict should be mild and quickly resolved with a happy ending.
        
        Use sensory details that toddlers can relate to - how things feel, sound, look, taste, and smell.
        Include some repetitive phrases or sounds that a toddler would enjoy repeating.
        
        IMPORTANT: Make this story UNIQUE from any other stories about these characters or in this setting.
        Use the specific scenario provided to create a distinct story experience.
        
        Format the story with a clear title, and divide it into short paragraphs for easy reading aloud.
        
        Random seed for variation: {story_seed}

        ONLY RETURN THE TITLE and the STORY TEXT, NOTHING ELSE, not intros and no music or anything like that, just the story text.
        """
        
        logger.debug(f"Created story prompt with scenario: {specific_scenario}")
        return prompt
