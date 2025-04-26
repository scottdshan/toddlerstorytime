from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Generator, AsyncGenerator
import random
import os
from pathlib import Path
import logging

from app.core.story_seed_bank import StorySeedBank

# Initialize logging
logger = logging.getLogger(__name__)

# --- Universe Character Mapping ---
UNIVERSE_CHARACTERS = {
    "Paw Patrol": ["Ryder", "Chase", "Marshall", "Skye", "Rubble", "Zuma", "Rocky", "Everest", "Tracker", "Ella", "Tuck", "Rex", "Katie", "Alex Porter", "Jake"],
    "Disney Princesses": ["Cinderella", "Ariel", "Belle", "Jasmine", "Rapunzel", "Moana", "Snow White", "Aurora", "Pocahontas", "Mulan", "Tiana", "Merida"],
    "Toy Story": ["Woody", "Buzz Lightyear", "Jessie", "Mr. Potato Head", "Slinky Dog", "Rex", "Forky", "Bo Peep", "Hamm"],
    "Frozen": ["Elsa", "Anna", "Olaf", "Kristoff", "Sven", "Hans", "King Agnarr", "Queen Iduna", "Duke of Weselton", "Marshmallow", "Oaken"],
    "Cars": ["Lightning McQueen", "Mater", "Sally Carrera", "Doc Hudson", "Ramone", "Flo", "Fillmore", "Sarge", "Red", "Cruz Ramirez"],
    "Moana": ["Moana", "Maui", "Heihei", "Pua", "Gramma Tala", "Chief Tui", "Te Fiti", "Tamatoa"],
    "The Lion King": ["Simba", "Nala", "Timon", "Pumbaa", "Rafiki", "Zazu", "Scar", "Mufasa", "Sarabi"],
    "Finding Nemo": ["Nemo", "Dory", "Marlin", "Crush", "Squirt", "Mr. Ray"],
    "Monsters, Inc.": ["Sully", "Mike Wazowski", "Boo", "Randall Boggs", "Roz"],
    "Winnie the Pooh": ["Pooh", "Piglet", "Tigger", "Eeyore", "Rabbit", "Kanga", "Roo", "Owl"],
    "Mickey Mouse Clubhouse": ["Mickey Mouse", "Minnie Mouse", "Donald Duck", "Goofy", "Pluto", "Daisy Duck"],
    "Peppa Pig": ["Peppa", "George", "Mummy Pig", "Daddy Pig", "Suzy Sheep", "Rebecca Rabbit"],
    "SpongeBob SquarePants": ["SpongeBob", "Patrick Star", "Squidward Tentacles", "Mr. Krabs", "Sandy Cheeks", "Plankton"],
    "Dora the Explorer": ["Dora", "Boots", "Swiper", "Backpack", "Map", "Isa the Iguana"],
    "Thomas & Friends": ["Thomas", "Percy", "James", "Gordon", "Emily", "Sir Topham Hatt"],
    "Sesame Street": ["Elmo", "Big Bird", "Cookie Monster", "Grover", "Oscar the Grouch", "Bert", "Ernie", "Abby Cadabby"],
    "Transformers": ["Optimus Prime", "Bumblebee", "Megatron", "Starscream", "Ironhide", "Ratchet"], # (Simplified for toddlers)
    "Super Mario Bros.": ["Mario", "Luigi", "Princess Peach", "Toad", "Yoshi", "Bowser"],
    "Pokemon": ["Pikachu", "Ash Ketchum", "Charmander", "Bulbasaur", "Squirtle", "Jigglypuff"], # Focus on iconic early ones
    "Barbie": ["Barbie", "Ken", "Skipper", "Stacie", "Chelsea", "Teresa"],
    "Hello Kitty": ["Hello Kitty", "Mimmy", "Dear Daniel", "My Melody", "Keroppi"],
    "Bluey": ["Bluey", "Bingo", "Bandit (Dad)", "Chilli (Mum)", "Lucky", "Chloe"],
    "Octonauts": ["Captain Barnacles", "Kwazii", "Peso", "Shellington", "Dashi", "Inkling", "Tweak"],
    "Blippi": ["Blippi", "Meekah"]
}
# --- End Universe Character Mapping ---

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
    
    @abstractmethod
    async def generate_story_streaming(self, story_elements: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Generate a story with streaming output based on provided elements
        
        Args:
            story_elements: Dictionary containing story elements (universe, setting, theme, etc.)
            
        Returns:
            Async generator yielding chunks of the story text as they're generated
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
        story_length = story_elements.get("story_length", "Short (3-5 minutes)")
        child_name = story_elements.get("child_name", "Wesley")
        
        # Determine characters to use
        input_characters = story_elements.get("characters", [])
        character_names = []

        # If specific characters were provided, use them
        if input_characters:
            if isinstance(input_characters, list):
                if input_characters and isinstance(input_characters[0], dict) and "character_name" in input_characters[0]:
                    for c in input_characters:
                        if isinstance(c, dict) and "character_name" in c:
                            name = c["character_name"]
                            if isinstance(name, str):
                                character_names.append(name)
                else:
                    character_names = [str(c) for c in input_characters] # Assume list of strings
            elif isinstance(input_characters, str):
                character_names = [c.strip() for c in input_characters.split(",")]
        
        # If no characters provided, try to get them from the universe mapping
        if not character_names:
            universe_chars = UNIVERSE_CHARACTERS.get(universe, [])
            if universe_chars:
                # Sample 1 to 3 characters from the universe list if available
                k = random.randint(1, min(len(universe_chars), 3))
                character_names = random.sample(universe_chars, k=k)

        # Ensure the child's name is included if appropriate
        if child_name and child_name not in character_names:
            character_names.append(child_name)
        
        # Ensure we have at least one character as a fallback
        if not character_names:
            character_names = ["The main character"] # Fallback if no characters provided or found
            
        # Generate a unique story scenario using the seed bank
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
        
        # Craft prompt aligned with fine-tuning format
        prompt = f"""
Create a story for a toddler or pre-schooler named {child_name} with the following elements:

Universe: {universe}
Setting: {setting}
Theme: {theme}

SPECIFIC SCENARIO TO USE: {specific_scenario}

Story should be approximately {target_words} words, taking about {story_length} to read aloud.

Make the story age-appropriate for a 2-5 year old:
- Simple language, short sentences
- Clear beginning, middle, end
- Repetition, simple morals, gentle humor
- Sensory details kids can relate to
- Some repeating phrases for fun
- Use characters from the universe if possible. Potential characters: {characters_str}. Try to naturally include 1-2 characters from this list in the story.

Format with a title and short paragraphs. Unique story each time.

Random seed: {story_seed}

ONLY RETURN the TITLE and the STORY TEXT. DO NOT RETURN ANY FORMATTING, ASTERISKS, OR ANYTHING ELSE.
"""

        logger.debug(f"Created story prompt with scenario: {specific_scenario}")
        return prompt
