import openai
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator

from app.config import LOCAL_OPENAI_API_URL, LOCAL_OPENAI_API_KEY
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class LocalOpenAIProvider(LLMProvider):
    """
    LLM provider implementation for Local OpenAI-compatible API servers
    (e.g., llama.cpp server with OpenAI API compatibility)
    """
    
    def __init__(self, model="llama3", api_key=None, api_base=None):
        """
        Initialize the Local OpenAI provider
        
        Args:
            model: The model to use (default: "llama3")
            api_key: Optional API key (many local deployments don't need this)
            api_base: Base URL for the local API server
        """
        # Call parent constructor to initialize StorySeedBank
        super().__init__()
        
        self.model = model
        self.api_key = api_key or LOCAL_OPENAI_API_KEY
        self.api_base = api_base or LOCAL_OPENAI_API_URL
        
        logger.info(f"Initializing Local OpenAI provider with API base: {self.api_base}, model: {self.model}")
        
        # Configure OpenAI client with the local API server URL
        self.client = openai.OpenAI(
            api_key=self.api_key if self.api_key else "not-needed",
            base_url=self.api_base
        )
        
        # Try to get available models and select a valid one
        try:
            available_models = self.get_available_models()
            logger.info(f"Available local models: {available_models}")
            
            # If the specified model doesn't exist, use the first available model
            if available_models and self.model not in available_models:
                self.model = available_models[0]
                logger.info(f"Specified model not available. Using model: {self.model}")
        except Exception as e:
            logger.warning(f"Failed to get available models: {str(e)}. Will try to use model '{self.model}' directly.")
    
    def get_available_models(self) -> List[str]:
        """
        Get a list of available models from the local API server
        
        Returns:
            List of model IDs/names
        """
        try:
            response = self.client.models.list()
            model_names = [model.id for model in response.data]
            return model_names
        except Exception as e:
            logger.error(f"Error fetching models from local API: {str(e)}")
            return []
    
    def generate_story(self, story_elements: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a story based on provided elements using a local LLM
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Dictionary containing the generated story text and the prompt used
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        try:
            # Log the model being used
            logger.info(f"Generating story with local model: {self.model}")
            
            # Call local API
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
            
            logger.info(f"Successfully generated story with local model, length: {len(story_text)} chars")
            
            return {
                "story_text": story_text,
                "prompt": prompt
            }
        except Exception as e:
            logger.error(f"Error generating story with local model: {e}", exc_info=True)
            # Provide a fallback response
            return {
                "story_text": f"Sorry, I couldn't generate a story. Error: {str(e)}",
                "prompt": prompt
            }
    
    async def generate_story_streaming(self, story_elements: Dict[str, Any]) -> AsyncGenerator[str, None]: # type: ignore
        """
        Generate a story based on provided elements using local OpenAI model with streaming
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Async generator yielding chunks of the story text as they're generated
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        try:
            logger.info(f"Calling local OpenAI with streaming using model: {self.model}")
            
            # Call OpenAI API with streaming
            streaming_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a skilled children's storyteller who creates engaging, "
                                                "age-appropriate bedtime stories for toddlers."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500,
                stream=True
            )
            
            # Process the streaming response
            for chunk in streaming_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                        
        except Exception as e:
            logger.error(f"Error in streaming story generation with local OpenAI: {str(e)}")
            # Don't yield error message directly as it causes frontend issues
            # The error will be handled by the endpoint's try-except block 