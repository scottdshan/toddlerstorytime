import random
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.config import STORY_SETTINGS
from app.db import crud

class StoryRandomizer:
    """
    Class to handle randomization of story elements with intelligent selection
    to avoid repetition and ensure variety
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = STORY_SETTINGS
        # Get usage frequencies from the database
        self.frequencies = crud.get_story_elements_frequency(db)
    
    def _weighted_random_choice(self, options: List[str], element_type: str) -> Optional[str]:
        """
        Select a random option with weighting based on historical frequency
        Less frequently used elements have higher probability of selection
        """
        if not options:
            return None
            
        # If no frequency data or only one option, just return random choice
        if len(options) <= 1 or element_type not in self.frequencies:
            return random.choice(options)
        
        # Get frequency data for this element type
        freq_data = self.frequencies.get(element_type, {})
        
        # Calculate weights (inversely proportional to frequency)
        weights = []
        for option in options:
            # Default frequency of 0 if not in history
            freq = freq_data.get(option, 0)
            # Use inverse frequency as weight (add 1 to avoid division by zero)
            # Higher frequency = lower weight = less likely to be chosen
            weight = 1.0 / (freq + 1)
            weights.append(weight)
        
        # Normalize weights to sum to 1.0
        total_weight = sum(weights)
        norm_weights = [w / total_weight for w in weights]
        
        # Make weighted random choice
        return random.choices(options, weights=norm_weights, k=1)[0]
    
    def randomize_story_elements(self, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a randomized set of story elements, with bias toward user preferences
        if provided, but ensuring variety
        """
        # Start with empty selections
        selections = {}
        
        # Apply weighted random selection for each element type
        selections["universe"] = self._weighted_random_choice(
            self.settings["universes"], "universes")
        
        selections["setting"] = self._weighted_random_choice(
            self.settings["settings"], "settings")
            
        selections["theme"] = self._weighted_random_choice(
            self.settings["themes"], "themes")
        
        # Select 2-4 characters randomly
        num_characters = random.randint(2, 4)
        # Always include the child if we have preferences
        characters = []
        if preferences and preferences.get("child_name"):
            characters.append(preferences.get("child_name"))
            num_characters -= 1
        
        # Get remaining characters
        available_chars = [c for c in self.settings["characters"] if c not in characters]
        
        # Select characters with weighted randomization
        for _ in range(num_characters):
            if not available_chars:
                break
            
            char = self._weighted_random_choice(available_chars, "characters")
            if char is not None:
                characters.append(char)
                available_chars.remove(char)
        
        selections["characters"] = characters
        
        # Select story length
        selections["story_length"] = random.choice(self.settings["story_length"])
        
        return selections
    
    def apply_preferences(self, random_elements: Dict[str, Any], 
                          preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust randomized elements based on user preferences with some randomness
        """
        result = random_elements.copy()
        
        # Apply favorite universe with 70% probability if set
        if preferences.get("favorite_universe") and random.random() < 0.7:
            result["universe"] = preferences["favorite_universe"]
        
        # Apply favorite character with 80% probability if set
        # (but don't duplicate if already selected)
        if preferences.get("favorite_character") and random.random() < 0.8:
            if preferences["favorite_character"] not in result["characters"]:
                result["characters"].append(preferences["favorite_character"])
        
        # Apply favorite setting with 50% probability if set
        if preferences.get("favorite_setting") and random.random() < 0.5:
            result["setting"] = preferences["favorite_setting"]
        
        # Apply favorite theme with 50% probability if set
        if preferences.get("favorite_theme") and random.random() < 0.5:
            result["theme"] = preferences["favorite_theme"]
        
        # Apply preferred story length with 60% probability if set
        if preferences.get("preferred_story_length") and random.random() < 0.6:
            result["story_length"] = preferences["preferred_story_length"]
        
        return result
