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

class StoryResponse(StoryBase):
    id: int
    prompt: str
    story_text: str
    audio_path: Optional[str] = None
    created_at: datetime
    characters: List[StoryCharacter]

    class Config:
        from_attributes = True

class StoryHistoryResponse(BaseModel):
    id: int
    universe: str
    setting: str
    theme: str
    story_length: str
    created_at: datetime
    audio_path: Optional[str]

    class Config:
        from_attributes = True

class StoryPreferencesBase(BaseModel):
    child_name: Optional[str] = "Wesley"
    favorite_universe: Optional[str] = None
    favorite_character: Optional[str] = None
    favorite_setting: Optional[str] = None
    favorite_theme: Optional[str] = None
    preferred_story_length: Optional[str] = None
    llm_provider: Optional[str] = "openai"
    voice_id: Optional[str] = None

class StoryPreferencesCreate(StoryPreferencesBase):
    pass

class StoryPreferences(StoryPreferencesBase):
    id: int
    updated_at: datetime

    class Config:
        from_attributes = True
