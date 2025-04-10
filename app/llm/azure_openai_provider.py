from typing import Dict, Any, AsyncGenerator
import openai
import logging
from app.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT
from app.llm.base import LLMProvider

logger = logging.getLogger(__name__)

class AzureOpenAIProvider(LLMProvider):
    """
    LLM provider implementation for Azure OpenAI
    """
    
    def __init__(self, 
                 deployment_name: str,
                 api_key: str = AZURE_OPENAI_API_KEY,  # type: ignore
                 api_base: str = AZURE_OPENAI_ENDPOINT,  # type: ignore
                 api_version: str = "2023-05-15"):
        """
        Initialize the Azure OpenAI provider
        
        Args:
            deployment_name: Azure deployment name
            api_key: Azure OpenAI API key
            api_base: Azure OpenAI API base URL
            api_version: Azure OpenAI API version
        """
        # Call parent constructor to initialize StorySeedBank
        super().__init__()
        
        self.deployment_name = deployment_name
        self.api_key = api_key or AZURE_OPENAI_API_KEY
        
        # Ensure the API base has the https:// prefix
        self.api_base = api_base or AZURE_OPENAI_ENDPOINT
        if self.api_base and not (self.api_base.startswith('http://') or self.api_base.startswith('https://')):
            self.api_base = f"https://{self.api_base}"
            
        self.api_version = api_version
        
        logger.info(f"Initializing Azure OpenAI client with API base: {self.api_base}, deployment: {self.deployment_name}, API version: {self.api_version}")
        
        # Configure Azure OpenAI client
        self.client = openai.AzureOpenAI(
            api_key=self.api_key,
            api_version=self.api_version,
            azure_endpoint=self.api_base
        )
    
    def generate_story(self, story_elements: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a story based on provided elements using Azure OpenAI
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Dictionary containing the generated story text and the prompt used
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        try:
            logger.info(f"Calling Azure OpenAI with deployment name: {self.deployment_name}")
            
            # Call Azure OpenAI API
            response = self.client.chat.completions.create(
                model=self.deployment_name,  # For Azure, model is the deployment name
                messages=[
                    {"role": "system", "content": "You are a skilled children's storyteller who creates engaging, "
                                                "age-appropriate bedtime stories for toddlers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.9
            )
            
            # Extract and return the story
            content = response.choices[0].message.content
            story_text = content.strip() if content is not None else ""
            
            return {
                "story_text": story_text,
                "prompt": prompt
            }
        except Exception as e:
            logger.error(f"Azure OpenAI API Error: {str(e)}", exc_info=True)
            
            # Try to give more helpful error messages based on common issues
            if "404" in str(e):
                raise Exception(f"Azure OpenAI deployment '{self.deployment_name}' not found. Please check your deployment name and Azure endpoint URL: {self.api_base}")
            elif "401" in str(e) or "authentication" in str(e).lower():
                raise Exception(f"Authentication error with Azure OpenAI. Please check your API key.")
            elif "resource not found" in str(e).lower():
                raise Exception(f"Azure OpenAI resource not found. Check that deployment '{self.deployment_name}' exists at {self.api_base}")
            else:
                raise
    
    async def generate_story_streaming(self, story_elements: Dict[str, Any]) -> AsyncGenerator[str, None]: # type: ignore
        """
        Generate a story based on provided elements using Azure OpenAI with streaming
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Async generator yielding chunks of the story text as they're generated
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        try:
            logger.info(f"Calling Azure OpenAI with streaming and deployment name: {self.deployment_name}")
            
            # Call Azure OpenAI API with streaming
            stream = self.client.chat.completions.create(
                model=self.deployment_name,  # For Azure, model is the deployment name
                messages=[
                    {"role": "system", "content": "You are a skilled children's storyteller who creates engaging, "
                                                "age-appropriate bedtime stories for toddlers."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.9,
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
