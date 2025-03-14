from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from app.db.database import Base

class StoryHistory(Base):
    """Model to track story generation history"""
    __tablename__ = "story_history"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    universe = Column(String(100))
    setting = Column(String(100))
    theme = Column(String(100))
    story_length = Column(String(50))
    prompt = Column(Text)
    story_text = Column(Text)
    audio_path = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Track which characters were in the story
    characters = relationship("StoryCharacter", back_populates="story")

class StoryCharacter(Base):
    """Model to track characters used in stories"""
    __tablename__ = "story_characters"
    
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("story_history.id"))
    character_name = Column(String(100))
    
    # Relationship to story
    story = relationship("StoryHistory", back_populates="characters")

class StoryPreferences(Base):
    """Model to store user preferences for stories"""
    __tablename__ = "story_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    child_name = Column(String(100), default="Wesley")
    favorite_universe = Column(String(100))
    favorite_character = Column(String(100))
    favorite_setting = Column(String(100))
    favorite_theme = Column(String(100))
    preferred_story_length = Column(String(50))
    llm_provider = Column(String(50), default="openai")  # openai, anthropic, local
    voice_id = Column(String(100))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
