import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# App settings
APP_NAME = os.getenv("APP_NAME", "Toddler Storyteller")
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")

# Database settings
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/storyteller.db")

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Azure OpenAI Settings
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY") or "Error"
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT") or "Error"
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT") or "Error"

# Voice settings
DEFAULT_VOICE_ID = os.getenv("DEFAULT_VOICE_ID")
DEFAULT_TTS_PROVIDER = os.getenv("DEFAULT_TTS_PROVIDER", "elevenlabs")

# Home Assistant settings
HOME_ASSISTANT_URL = os.getenv("HOME_ASSISTANT_URL")
HOME_ASSISTANT_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN")

# Paths
AUDIO_DIR = BASE_DIR / "app" / "static" / "audio"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

# Story settings
STORY_SETTINGS = {
    "universes": [
        "Paw Patrol",
        "Disney Princess",
        "PJ Masks",
        "Bluey",
        "Peppa Pig",
        "Cocomelon",
        "Toy Story",
        "Mickey Mouse Clubhouse",
        "Sesame Street",
        "Original Fantasy World"
    ],
    "characters": [
        "Wesley",  # User's toddler
        "Mom",
        "Dad",
        "Chase",
        "Marshall",
        "Skye",
        "Rubble",
        "Rocky",
        "Zuma",
        "Ryder",
        "Elsa",
        "Anna",
        "Olaf",
        "Mickey Mouse",
        "Minnie Mouse",
        "Bluey",
        "Bingo",
        "Bandit",
        "Chilli"
    ],
    "settings": [
        "Bedtime",
        "Playground",
        "Beach",
        "Zoo",
        "Farm",
        "Space",
        "Underwater",
        "Forest",
        "Jungle",
        "Mountains",
        "School",
        "Doctor's Office",
        "Rainy Day",
        "Snowy Day",
        "Birthday Party"
    ],
    "themes": [
        "Friendship",
        "Helping Others",
        "Trying New Things",
        "Facing Fears",
        "Being Kind",
        "Learning New Skills",
        "Listening to Parents",
        "Sharing",
        "Patience",
        "Being Brave",
        "Taking Turns",
        "Apologizing",
        "Gratitude",
        "Sleep Routine",
        "Morning Routine"
    ],
    "story_length": [
        "Very Short (2-3 minutes)",
        "Short (3-5 minutes)",
        "Medium (5-7 minutes)",
        "Long (7-10 minutes)"
    ]
}

# Ensure audio directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)
