# Copyright iX.
# SPDX-License-Identifier: MIT-0
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator, Union
from llm import LLMParameters, GenImageParameters, LLMMessage, LLMResponse


class LLMProviderError(Exception):
    """Custom exception for LLM API provider errors with error code and user-friendly message"""
    def __init__(self, error_code: str, message: str, details: Optional[str] = None):
        """Initialize LLMProviderError
        
        Args:
            error_code: Error code (e.g. ThrottlingException, ValidationException)
            message: User-friendly error message
            details: Optional technical details for logging
        """
        self.error_code = error_code
        self.message = message
        self.details = details
        super().__init__(message)


class LLMAPIProvider(ABC):
    """Base class for LLM API providers"""
    
    def __init__(self, model_id: str, llm_params: Union[LLMParameters, GenImageParameters], tools):
        """Initialize provider with model ID, parameters and tools
        
        Args:
            model_id: Model identifier
            llm_params: LLM inference parameters (either LLMParameters for text or GenImageParameters for images)
            tools: List of tool module names to enable
        """
        self.model_id = model_id
        self.llm_params = llm_params
        self.tools = tools
        self._validate_config()
        self._initialize_client()
    
    @abstractmethod
    def _validate_config(self) -> None:
        """Validate provider-specific configuration"""
        pass
    
    @abstractmethod
    def _initialize_client(self) -> None:
        """Initialize provider-specific client"""
        pass
    
    @abstractmethod
    async def generate_content(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response
        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Return:
            Dict containing either:
            - {"content": dict} for content chunks
            - {"metadata": dict} for response metadata        
        """        
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[LLMMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate a streaming response
        Args:
            messages: user messages
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing either:
            - {"content": dict} for content chunks
            - {"metadata": dict} for response metadata        
        """
        pass

    @abstractmethod
    async def multi_turn_generate(
        self,
        message: LLMMessage,
        history: List[LLMMessage],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response for multi-turn chat
        Args:
            message: Current user message
            history: Optional chat history
            system_prompt: Optional system instructions
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing either:
            - {"content": dict} for content chunks
            - {"metadata": dict} for response metadata  
        """
        pass


def create_provider(provider_name: str, model_id: str, llm_params: Union[LLMParameters, GenImageParameters], tools: Optional[List[str]] = None) -> LLMAPIProvider:
    """Factory function to create appropriate provider instance
    
    Args:
        provider_name: Name of provider (e.g. 'Bedrock', 'Gemini', 'OpenAI')
        model_id: Model identifier
        llm_params: LLM inference parameters (either LLMParameters for text or GenImageParameters for images)
        tools: Optional list of tool module names to enable
        
    Returns:
        LLMAPIProvider: Provider instance with tools configured
        
    Raises:
        ValueError: If provider_type is not supported
    """
    from llm.api_providers.bedrock_converse import BedrockConverse
    from llm.api_providers.bedrock_invoke import BedrockInvoke
    from llm.api_providers.google_gemini import GeminiProvider
    from llm.api_providers.openai import OpenAIProvider
    
    # Map provider types to their implementations
    providers = {
        'BEDROCK': BedrockConverse,
        'BEDROCKINVOKE': BedrockInvoke,
        # 'ANTHROPIC': AnthropicProvider,
        'GEMINI': GeminiProvider, 
        'OPENAI': OpenAIProvider
    }
    
    # Get provider class
    provider_class = providers.get(provider_name.upper())
    if not provider_class:
        raise ValueError(f"Unsupported API provider: {provider_name}")

    # Create provider instance with tools
    # Tools will be initialized by the specific provider
    return provider_class(model_id, llm_params, tools or [])
