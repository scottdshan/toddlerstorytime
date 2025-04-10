from typing import Dict, Any, Optional, Union
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider
from app.llm.claude_provider import ClaudeProvider
from app.llm.azure_openai_provider import AzureOpenAIProvider
from app.llm.local_openai_provider import LocalOpenAIProvider
import os

class LLMFactory:
    """
    Factory class for creating LLM provider instances.
    Makes it easy to switch between different LLM providers.
    """
    
    @staticmethod
    def get_provider(provider_config: Union[Dict[str, Any], str]) -> LLMProvider:
        """
        Get an LLM provider instance based on configuration
        
        Args:
            provider_config: Configuration dictionary with at least a 'provider' key
                             and other provider-specific settings, or a string with the provider name
            
        Returns:
            LLMProvider instance
            
        Raises:
            ValueError: If the provider is not supported
        """
        if isinstance(provider_config, str):
            # If a string is passed, treat it as the provider name
            provider_name = provider_config.lower()
            provider_config = {"provider": provider_name}
        else:
            provider_name = provider_config.get("provider", "openai").lower()
        
        if provider_name == "openai":
            return OpenAIProvider(
                model=provider_config.get("model", "gpt-4o"),
                api_key=provider_config.get("api_key")
            )
        elif provider_name == "claude" or provider_name == "anthropic":
            return ClaudeProvider(
                model=provider_config.get("model", "claude-3-haiku-20240307"),
                api_key=provider_config.get("api_key")
            )
        elif provider_name in ["azure", "azure_openai", "azure-openai"]:
            # Get the deployment name from environment variable if not specified
            deployment_name = provider_config.get("deployment_name") or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            
            return AzureOpenAIProvider(
                deployment_name=deployment_name, # type: ignore
                api_key=provider_config.get("api_key"), # type: ignore
                api_base=provider_config.get("api_base"), # type: ignore
                api_version=provider_config.get("api_version", "2023-05-15")
            )
        elif provider_name in ["local", "local_openai", "local-openai"]:
            # Get the model from environment variable if not specified in config
            model = provider_config.get("model") or os.environ.get("LOCAL_MODEL", "llama3")
            
            return LocalOpenAIProvider(
                model=model,
                api_key=provider_config.get("api_key"),
                api_base=provider_config.get("api_base") or os.environ.get("LOCAL_OPENAI_API_URL")
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_name}")
