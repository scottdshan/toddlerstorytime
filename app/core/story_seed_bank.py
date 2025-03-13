import random
import logging
from typing import Dict, List, Optional, Set, Tuple
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Ensure data directory exists
data_dir = Path("app/data/cache")
data_dir.mkdir(parents=True, exist_ok=True)

class StorySeedBank:
    """
    Manages pre-generated story seed scenarios to ensure story variety
    even when settings and characters remain the same.
    """
    
    # Dictionary of theme-specific story scenarios
    # Each theme has a list of specific story ideas
    SEED_BANK = {
        "Friendship": [
            "Character makes a new friend who is very different from them",
            "Character feels left out when friends play together without them",
            "Character learns to share their favorite toy with a friend",
            "Two characters who initially don't get along find common ground",
            "Character helps a shy friend join in group activities",
            "Character and friend have a disagreement but learn to compromise",
            "Character misses a faraway friend and finds a way to connect",
            "Character teaches a new skill to a friend who's struggling",
            "Character prepares a surprise for a friend who's feeling sad",
            "Friends work together to build something amazing",
            "Character learns that friends can have different opinions and still be friends",
            "Character feels jealous of friend's new toy but learns to be happy for them",
            "Friends get lost together and help each other find their way",
            "Character stands up for a friend who's being teased",
            "Friends take turns choosing what game to play",
        ],
        "Helping Others": [
            "Character rescues a small animal stuck in a tree",
            "Character helps someone who fell and hurt themselves",
            "Character notices someone forgot their lunch and shares theirs",
            "Character helps clean up a mess they didn't make",
            "Character builds a ramp for someone who can't use stairs",
            "Character reads a story to someone who can't read",
            "Character teaches a younger child how to tie their shoes",
            "Character helps find something important that was lost",
            "Character shares their umbrella during a rainstorm",
            "Character notices someone is sad and cheers them up",
            "Character helps carry heavy groceries for someone",
            "Character makes a card for someone who's sick",
            "Character helps plant a garden for the community",
            "Character rescues a toy that floated away in water",
            "Character helps translate for someone who speaks a different language",
        ],
        "Trying New Things": [
            "Character tries a new food they thought they wouldn't like",
            "Character tries a new sport or activity they've never done before",
            "Character is scared of swimming but tries it anyway",
            "Character makes a new recipe for the first time",
            "Character tries to make friends in a new place",
            "Character learns to ride a bike despite being afraid of falling",
            "Character tries a musical instrument for the first time",
            "Character tries speaking in front of a group despite being nervous",
            "Character tries a challenging puzzle that looks too hard",
            "Character learns words in a new language",
            "Character tries camping outdoors for the first time",
            "Character tries to grow a plant from a seed",
            "Character tries a new game with rules they don't understand at first",
            "Character tries to fix something broken instead of asking for help",
            "Character creates art using a new technique they've never tried",
        ],
        "Facing Fears": [
            "Character is afraid of the dark and learns to overcome it",
            "Character is scared of loud noises like thunder",
            "Character fears going to the doctor but finds it's not so bad",
            "Character is afraid of deep water but wants to swim",
            "Character fears big animals but meets a gentle one",
            "Character is scared to go down the big slide",
            "Character is afraid of getting lost in a crowded place",
            "Character fears sleeping away from home for the first time",
            "Character is scared of bugs but learns some are helpful",
            "Character fears performing in front of others",
            "Character is afraid of making mistakes when learning something new",
            "Character fears going to a new school or class",
            "Character is scared to try food that looks strange",
            "Character fears speaking to someone they don't know",
            "Character is afraid of heights but wants to see the view",
        ],
        "Being Kind": [
            "Character shares their favorite toy with someone who has none",
            "Character makes a get-well card for someone who's sick",
            "Character includes someone who's playing alone",
            "Character says kind words to someone who's feeling sad",
            "Character helps someone younger who's struggling with a task",
            "Character leaves a surprise gift for someone to find",
            "Character compliments others on things they do well",
            "Character gives up their seat for someone who needs it more",
            "Character notices when someone is left out and invites them to play",
            "Character helps clean up someone else's spill without being asked",
            "Character returns a lost item they found instead of keeping it",
            "Character apologizes when they accidentally hurt someone's feelings",
            "Character makes a welcome gift for a new neighbor",
            "Character shares an umbrella with someone caught in the rain",
            "Character takes care of someone else's pet or plant while they're away",
        ],
        "Learning New Skills": [
            "Character learns to tie their shoes for the first time",
            "Character practices riding a bike without training wheels",
            "Character learns to count to higher numbers",
            "Character tries to write their name by themselves",
            "Character learns to make their bed independently",
            "Character figures out how to build a tall tower that won't fall",
            "Character learns to use scissors safely",
            "Character practices catching a ball after many misses",
            "Character learns to use a new tool with help",
            "Character learns words in a different language",
            "Character practices drawing shapes and letters",
            "Character learns to brush their teeth properly",
            "Character figures out how to complete a puzzle",
            "Character learns to pour their own drink without spilling",
            "Character practices singing a song with all the right words",
        ],
        "Listening to Parents": [
            "Character remembers to look both ways before crossing the street",
            "Character stays close in a crowded place as told",
            "Character wants to play longer but comes when called",
            "Character remembers to wash hands before eating as taught",
            "Character picks up toys when asked without complaining",
            "Character doesn't touch something dangerous as warned",
            "Character holds hands in the parking lot as required",
            "Character goes to bed on time without fussing",
            "Character remembers to say please and thank you",
            "Character doesn't wander off in a store",
            "Character follows directions to help with a simple task",
            "Character waits patiently when asked instead of interrupting",
            "Character leaves something alone that's not for children",
            "Character tells a parent before going outside",
            "Character doesn't open the door to strangers as taught",
        ],
        "Sharing": [
            "Character shares their favorite toy with a friend",
            "Character takes turns with a popular playground equipment",
            "Character shares their snack with someone who has none",
            "Character shares art supplies during a project",
            "Character learns to share parent's attention with a sibling",
            "Character shares their umbrella during a rainstorm",
            "Character lets someone else have a turn with a new toy",
            "Character shares their knowledge by teaching a skill",
            "Character shares their space on a bench or mat",
            "Character divides treats equally among friends",
            "Character shares a book they've finished reading",
            "Character lets others use their toys at a playdate",
            "Character shares credit for an idea or creation",
            "Character shares their time to help someone else",
            "Character learns that sharing can make play more fun",
        ],
        "Patience": [
            "Character waits their turn on playground equipment",
            "Character works on a difficult puzzle without giving up",
            "Character waits quietly during an important meeting",
            "Character saves money for something they want",
            "Character plants seeds and waits for them to grow",
            "Character practices a skill many times before improving",
            "Character waits in line without pushing or complaining",
            "Character waits for dinner to be ready when hungry",
            "Character lets someone finish speaking before talking",
            "Character calmly waits for help instead of yelling",
            "Character waits for a special event that's coming soon",
            "Character tries repeatedly to learn a new skill",
            "Character must wait for a rainy day to end",
            "Character learns that sometimes good things take time",
            "Character must wait their turn to be picked for a game",
        ],
        "Being Brave": [
            "Character tries a big slide at the playground despite fear",
            "Character stands up to someone who's being unkind",
            "Character speaks in front of the class for the first time",
            "Character goes to the doctor despite being scared",
            "Character approaches new children to make friends",
            "Character tries a new food that looks strange",
            "Character sleeps without a nightlight for the first time",
            "Character enters a dark room to retrieve a toy",
            "Character defends a friend who's being teased",
            "Character tries to swim in the deep end",
            "Character tells the truth even when it's hard",
            "Character goes on a ride that seems scary",
            "Character stays alone for the first time",
            "Character performs in front of an audience",
            "Character stands up for what's right even when friends disagree",
        ],
        "Taking Turns": [
            "Characters take turns on a swing at the playground",
            "Characters create a system for taking turns with a new toy",
            "Character learns to wait while others have their turn in a game",
            "Characters take turns choosing which game to play",
            "Children take turns being the leader in an activity",
            "Characters take turns adding ingredients while baking",
            "Character struggles but learns to wait for their turn to speak",
            "Characters take turns reading pages of a book",
            "Character waits patiently for their turn on a special ride",
            "Characters take turns using limited art supplies",
            "Character learns that taking turns means everyone gets a chance",
            "Characters take turns carrying something heavy together",
            "Character feels frustrated waiting but finds ways to be patient",
            "Characters use a timer to ensure fair turns",
            "Character lets someone else go first as an act of kindness",
        ],
        "Apologizing": [
            "Character accidentally breaks something and apologizes",
            "Character says mean words and learns to say sorry",
            "Character accidentally hurts someone during play",
            "Character forgets an important promise and apologizes",
            "Character takes something without asking first",
            "Character makes a mess and apologizes while helping clean up",
            "Character learns that saying sorry isn't enough without changing behavior",
            "Character blames someone else but later admits the truth",
            "Character interrupts someone important and apologizes",
            "Character accidentally ruins something someone else made",
            "Character doesn't share and later feels sorry about it",
            "Character learns how to apologize properly and mean it",
            "Character understands how their actions affected someone's feelings",
            "Character apologizes even when it was an accident",
            "Character makes amends after an apology by doing something kind",
        ],
        "Gratitude": [
            "Character learns to say thank you for everyday kindnesses",
            "Character makes thank-you cards for people who help them",
            "Character appreciates nature during a walk outside",
            "Character feels grateful for family during a special moment",
            "Character shows gratitude for a meal someone prepared",
            "Character receives a gift and shows genuine appreciation",
            "Character realizes how lucky they are compared to others",
            "Character thanks someone for teaching them a new skill",
            "Character appreciates help during a difficult task",
            "Character keeps a gratitude journal or list",
            "Character creates a gift to show thanks to someone special",
            "Character learns to be grateful even for small things",
            "Character feels thankful when someone cheers them up",
            "Character appreciates the beauty in everyday moments",
            "Character expresses thanks to community helpers like mail carriers",
        ],
        "Sleep Routine": [
            "Character resists bedtime but learns why sleep is important",
            "Character creates a special bedtime routine with family",
            "Character overcomes fear of the dark at bedtime",
            "Character struggles to fall asleep and learns relaxation techniques",
            "Character wants 'one more story' but learns about time limits",
            "Character learns to prepare for bed independently",
            "Character experiences a dream and talks about it the next day",
            "Character has a special stuffed animal or blanket for bedtime",
            "Character helps create a calm, cozy sleep environment",
            "Character learns to set out clothes for the morning",
            "Character discovers the benefits of being well-rested",
            "Character deals with distractions at bedtime",
            "Character finds that a bath before bed helps them sleep",
            "Character learns a bedtime song or prayer routine",
            "Character has a special goodnight ritual with family",
        ],
        "Morning Routine": [
            "Character learns to get dressed independently",
            "Character helps prepare breakfast with a parent",
            "Character remembers all the steps in morning hygiene",
            "Character packs their own bag for school or daycare",
            "Character creates a morning checklist to follow",
            "Character deals with moving slowly when they need to hurry",
            "Character helps a sibling with their morning routine",
            "Character wakes up too early and learns to wait quietly",
            "Character struggles to get out of a warm, cozy bed",
            "Character remembers to feed a pet as part of morning responsibilities",
            "Character makes their bed without being reminded",
            "Character gets ready efficiently to have time for play",
            "Character prepares the night before to make morning easier",
            "Character learns what to do if they oversleep",
            "Character has a special morning greeting ritual with family",
        ],
        # Add more themes as needed
    }
    
    # Maps for different settings - each maps to specific scenario adjustments
    SETTING_ADJUSTMENTS = {
        "Beach": [
            "building a sandcastle together",
            "collecting seashells along the shore",
            "playing in the gentle waves",
            "having a picnic on a beach towel",
            "digging a hole to find water",
            "watching seagulls and other beach creatures",
            "flying a kite in the beach breeze",
            "helping someone who got sand in their eyes",
            "looking for crabs in tide pools",
            "making footprints in the wet sand",
            "cleaning up litter from the beach",
            "helping apply sunscreen to hard-to-reach spots",
            "rescuing a toy that floated away in the water",
            "sharing beach toys with others",
            "waiting patiently for turns on a boogie board",
        ],
        "Playground": [
            "taking turns on the slide",
            "pushing someone on the swings",
            "climbing the jungle gym together",
            "playing in the sandbox",
            "making friends with a new child",
            "helping someone who fell down",
            "waiting in line for the popular equipment",
            "sharing playground toys",
            "inviting someone to join a game",
            "helping a younger child navigate equipment",
            "finding a lost toy in the playground",
            "cleaning up trash on the playground",
            "resolving an argument over who goes next",
            "teaching someone how to use monkey bars",
            "helping someone who's stuck on equipment",
        ],
        # Add more settings as needed
    }
    
    def __init__(self, cache_file_path: Optional[str] = None):
        """
        Initialize the story seed bank
        
        Args:
            cache_file_path: Optional path to a file where generated scenarios can be cached
        """
        self.cache_file_path = cache_file_path or "app/data/cache/story_seeds.json"
        self.cached_scenarios = {}
        self.load_cache()
    
    def load_cache(self) -> None:
        """Load previously cached scenarios if available"""
        if not self.cache_file_path:
            return
            
        cache_path = Path(self.cache_file_path)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self.cached_scenarios = json.load(f)
                logger.info(f"Loaded {len(self.cached_scenarios)} cached scenario sets")
            except Exception as e:
                logger.error(f"Error loading scenario cache: {e}")
                self.cached_scenarios = {}
    
    def save_cache(self) -> None:
        """Save generated scenarios to cache file"""
        if not self.cache_file_path:
            return
            
        try:
            # Ensure directory exists
            cache_path = Path(self.cache_file_path)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_path, 'w') as f:
                json.dump(self.cached_scenarios, f, indent=2)
            logger.info(f"Saved {len(self.cached_scenarios)} scenario sets to cache")
        except Exception as e:
            logger.error(f"Error saving scenario cache: {e}")
    
    def get_random_story_seed(self, theme: str, setting: str) -> Dict[str, str]:
        """
        Get a random, specific story seed for the given theme and setting
        
        Args:
            theme: The general theme of the story (e.g., "Friendship")
            setting: The setting of the story (e.g., "Beach")
            
        Returns:
            Dictionary with specific story details
        """
        # Generate a cache key based on theme and setting
        cache_key = f"{theme}_{setting}"
        
        # Check if we already have generated scenarios for this combination
        if cache_key in self.cached_scenarios and self.cached_scenarios[cache_key]:
            # Return a random scenario from the cache
            return random.choice(self.cached_scenarios[cache_key])
            
        # If we don't have a cache entry or it's empty, generate new scenarios
        theme_scenarios = self.SEED_BANK.get(theme, [])
        if not theme_scenarios:
            # Fallback if theme not found
            theme_scenarios = ["Character learns something important about friendship",
                              "Character helps someone in need",
                              "Character overcomes a challenge together with friends"]
        
        setting_adjustments = self.SETTING_ADJUSTMENTS.get(setting, [])
        if not setting_adjustments:
            # Generic adjustments if setting not found
            setting_adjustments = ["playing together", "exploring together", 
                                  "discovering something new", "helping each other"]
                                  
        # Generate a list of specific scenarios by combining theme scenarios and setting adjustments
        specific_scenarios = []
        
        for _ in range(10):  # Generate 10 unique scenarios
            theme_base = random.choice(theme_scenarios)
            setting_detail = random.choice(setting_adjustments)
            
            # Combine with some variation
            scenario_options = [
                {
                    "problem": f"{theme_base} while {setting_detail}",
                    "activity": setting_detail,
                    "emotion": random.choice(["excited", "nervous", "curious", "worried", "happy"]),
                    "resolution": random.choice(["teamwork", "perseverance", "kindness", "creativity", "bravery"])
                },
                {
                    "problem": f"{setting_detail} becomes challenging when {theme_base.lower()}",
                    "activity": setting_detail,
                    "emotion": random.choice(["surprised", "confused", "determined", "unsure", "proud"]),
                    "resolution": random.choice(["asking for help", "trying again", "thinking creatively", "being patient", "working together"])
                },
                {
                    "problem": f"While {setting_detail}, character learns about {theme.lower()}",
                    "activity": setting_detail,
                    "emotion": random.choice(["amazed", "thoughtful", "joyful", "calm", "energetic"]),
                    "resolution": random.choice(["making a new friend", "solving a problem", "sharing with others", "helping someone", "learning something new"])
                }
            ]
            
            specific_scenarios.append(random.choice(scenario_options))
            
        # Cache the generated scenarios
        self.cached_scenarios[cache_key] = specific_scenarios
        self.save_cache()
        
        # Return a random scenario from the newly generated list
        return random.choice(specific_scenarios)
    
    def get_specific_scenario(self, theme: str, setting: str, characters: List[str]) -> str:
        """
        Generate a specific scenario for the story based on theme, setting, and characters
        
        Args:
            theme: The story theme (e.g., "Friendship")
            setting: The story setting (e.g., "Beach")
            characters: List of character names
            
        Returns:
            A detailed scenario description for the story
        """
        # Use default values if None is provided
        theme = theme or "Friendship"
        setting = setting or "Playground"
        characters = characters or ["The main character"]
        
        # Get a random seed for variation
        seed = self.get_random_story_seed(theme, setting)
        
        # Select a main character for this story
        main_character = random.choice(characters) if characters else "The main character"
        
        # Craft a specific scenario
        scenario = f"{main_character} {seed['problem']}. "
        
        # Add emotion component
        scenario += f"They feel {seed['emotion']} about this. "
        
        # Add supporting characters if available
        supporting_chars = [c for c in characters if c != main_character]
        if supporting_chars:
            helper = random.choice(supporting_chars)
            scenario += f"{helper} helps them by {seed['resolution']}. "
        else:
            scenario += f"They solve this by {seed['resolution']}. "
        
        # Add a specific setting detail
        scenario += f"This all happens while {seed['activity']} at the {setting.lower()}."
        
        return scenario 