from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

class StoryCharacterBase(BaseModel):
    character_name: str

class StoryCharacterCreate(StoryCharacterBase):
    pass

class StoryCharacter(StoryCharacterBase):
    id: int
    story_id: int

    class Config:
        from_attributes = True

# New class for input validation that doesn't require IDs
class StoryCharacterInput(StoryCharacterBase):
    pass

class StoryBase(BaseModel):
    universe: str
    setting: str
    theme: str
    story_length: str
    characters: List[StoryCharacter]

class StoryCreate(StoryBase):
    pass

class StoryGenRequest(BaseModel):
    universe: str
    setting: str
    theme: str
    story_length: str
    characters: List[StoryCharacterInput]
    child_name: Optional[str] = "Wesley"
    randomize: Optional[bool] = False
    llm_provider: Optional[str] = "openai"  # openai, anthropic, azure, local
    model: Optional[str] = None
    deployment_name: Optional[str] = None  # For Azure OpenAI
    tts_provider: Optional[str] = "elevenlabs"
    voice_id: Optional[str] = None
    local_api_url: Optional[str] = None  # For local LLM provider

class StoryResponse(StoryBase):
    id: int
    title: Optional[str] = "Bedtime Story"
    prompt: str
    story_text: str
    audio_path: Optional[str] = None
    created_at: datetime
    characters: List[StoryCharacter]
    llm_duration: Optional[float] = None  # Time in seconds for LLM generation
    tts_duration: Optional[float] = None  # Time in seconds for TTS generation

    class Config:
        from_attributes = True

class StoryHistoryResponse(BaseModel):
    id: int
    title: Optional[str] = "Bedtime Story"
    universe: str
    setting: str
    theme: str
    story_length: str
    characters: List[StoryCharacter]
    created_at: datetime
    audio_path: Optional[str]
    llm_duration: Optional[float] = None  # Time in seconds for LLM generation
    tts_duration: Optional[float] = None  # Time in seconds for TTS generation

    class Config:
        from_attributes = True

class StoryPreferencesBase(BaseModel):
    child_name: Optional[str] = "Wesley"
    favorite_universe: Optional[str] = None
    favorite_character: Optional[str] = None
    favorite_setting: Optional[str] = None
    favorite_theme: Optional[str] = None
    preferred_story_length: Optional[str] = None
    
    # LLM Provider settings
    llm_provider: Optional[str] = "openai"
    llm_model: Optional[str] = None
    local_api_url: Optional[str] = None
    
    # TTS Provider settings
    tts_provider: Optional[str] = "elevenlabs"
    voice_id: Optional[str] = None
    
    # Storage settings
    audio_dir: Optional[str] = None
    network_share_path: Optional[str] = None
    network_share_url: Optional[str] = None

class StoryPreferencesCreate(StoryPreferencesBase):
    pass

class StoryPreferences(StoryPreferencesBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True

class StoryPreferencesResponse(StoryPreferencesBase):
    id: int
    
    class Config:
        orm_mode = True
