from typing import List, Optional, Union, Dict, Any, Set
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

class StoryElementsRequest(BaseModel):
    """
    Request model for streaming story generation.
    
    Similar to StoryGenRequest but with fields specific to the streaming endpoint.
    """
    universe: str
    setting: str
    theme: str
    story_length: str
    characters: List[Union[StoryCharacterInput, str]]
    child_name: Optional[str] = "Wesley"
    title: Optional[str] = "Bedtime Story"
    age: Optional[int] = 3
    audio: Optional[bool] = True
    llm_provider: Optional[str] = "openai"
    tts_provider: Optional[str] = "elevenlabs"
    voice_id: Optional[str] = None
    model: Optional[str] = None
    
    def dict(
        self,
        *,
        include: Union[Set[str], Dict[str, Any]] = None,
        exclude: Union[Set[str], Dict[str, Any]] = None,
        by_alias: bool = False,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = False,
    ) -> Dict[str, Any]:
        """Convert to dict with proper character formatting."""
        data = super().dict(
            include=include,
            exclude=exclude,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
        )
        
        # Format characters if they're strings
        if data.get("characters"):
            formatted_chars = []
            for char in data["characters"]:
                if isinstance(char, str):
                    formatted_chars.append({"character_name": char})
                else:
                    formatted_chars.append(char)
            data["characters"] = formatted_chars
            
        return data
