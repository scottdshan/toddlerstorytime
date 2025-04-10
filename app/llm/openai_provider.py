import openai
from typing import Dict, Any, Optional, AsyncGenerator

from app.config import OPENAI_API_KEY
from app.llm.base import LLMProvider
import logging

# Set up logger
logger = logging.getLogger(__name__)

class OpenAIProvider(LLMProvider):
    """
    LLM provider implementation for OpenAI
    """
    
    def __init__(self, model="gpt-4o", api_key=None, api_base=None):
        """
        Initialize the OpenAI provider
        
        Args:
            model: The model to use (default: "gpt-4o")
            api_key: Optional custom API key
            api_base: Optional custom API base URL (useful for Azure OpenAI)
        """
        # Call parent constructor to initialize StorySeedBank
        super().__init__()
        
        self.model = model
        self.api_key = api_key or OPENAI_API_KEY
        self.api_base = api_base
        
        # Configure OpenAI client
        if self.api_base is not None:
            self.client = openai.OpenAI(api_key=self.api_key, base_url=self.api_base)
        else:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def generate_story(self, story_elements: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a story based on provided elements using OpenAI
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Dictionary containing the generated story text and the prompt used
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a skilled children's storyteller who creates engaging, "
                                               "age-appropriate bedtime stories for toddlers."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        # Extract and return the story
        content = response.choices[0].message.content
        story_text = content.strip() if content is not None else ""
        
        return {
            "story_text": story_text,
            "prompt": prompt
        }
    
    async def generate_story_streaming(self, story_elements: Dict[str, Any]) -> AsyncGenerator[str, None]: # type: ignore
        """
        Generate a story based on provided elements using OpenAI with streaming
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Async generator that yields chunks of the story as they are generated
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        try:
            # Call OpenAI API with streaming
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skilled children's storyteller who creates engaging, "
                                                "age-appropriate bedtime stories for toddlers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.7,
                stream=True
            )
            
            # Stream the response chunks
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        except Exception as e:
            logger.error(f"Error in streaming story generation: {str(e)}")
            # Don't yield error message directly as it causes frontend issues
            # The error will be handled by the endpoint's try-except block
