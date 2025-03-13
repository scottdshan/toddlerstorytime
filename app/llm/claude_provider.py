import anthropic
from typing import Dict, Any

from app.config import ANTHROPIC_API_KEY
from app.llm.base import LLMProvider

class ClaudeProvider(LLMProvider):
    """
    LLM provider implementation for Anthropic Claude
    """
    
    def __init__(self, model="claude-3-haiku-20240307", api_key=None):
        """
        Initialize the Claude provider
        
        Args:
            model: The model to use (default: "claude-3-haiku-20240307")
            api_key: Optional custom API key
        """
        # Call parent constructor to initialize StorySeedBank
        super().__init__()
        
        self.model = model
        self.api_key = api_key or ANTHROPIC_API_KEY
        
        # Configure Anthropic client
        self.client = anthropic.Anthropic(api_key=self.api_key)
    
    def generate_story(self, story_elements: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate a story based on provided elements using Claude
        
        Args:
            story_elements: Dictionary containing story elements
            
        Returns:
            Dictionary containing the generated story text and the prompt used
        """
        # Create prompt using the base class method
        prompt = self.create_story_prompt(story_elements)
        
        # Call Claude API
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system="You are a skilled children's storyteller who creates engaging, "
                   "age-appropriate bedtime stories for toddlers.",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # Extract and return the story
        story_text = response.content[0].text
        
        return {
            "story_text": story_text,
            "prompt": prompt
        }
