# Copyright iX.
# SPDX-License-Identifier: MIT-0
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncIterator
from .. import LLMConfig, Message, LLMResponse


class LLMAPIProvider(ABC):
    """Base class for LLM providers"""
    
    def __init__(self, config: LLMConfig, tools):
        self.config = config
        self.tools = tools
        self._validate_config()
        self._initialize_client()

    @classmethod
    def create(cls, config: LLMConfig, tools: Optional[List[str]] = None) -> 'LLMAPIProvider':
        """Factory method to create appropriate provider instance
        
        Args:
            config: LLM configuration
            tools: Optional list of tool module names to enable
            
        Returns:
            LLMAPIProvider: Provider instance with tools configured
        """
        from llm.api_providers.bedrock_converse import BedrockConverse
        from llm.api_providers.bedrock_invoke import BedrockInvoke
        from llm.api_providers.google_gemini import GeminiProvider
        from llm.api_providers.openai import OpenAIProvider
        
        # Get provider class
        providers = {
            'BEDROCK': BedrockConverse,
            'BEDROCKINVOKE': BedrockInvoke,
            # 'ANTHROPIC': AnthropicProvider,
            'GEMINI': GeminiProvider, 
            'OPENAI': OpenAIProvider
        }
        provider_class = providers.get(config.api_provider.upper())
        if not provider_class:
            raise ValueError(f"Unsupported API provider: {config.api_provider}")
    
        # Create provider instance with tools
        # Tools will be initialized by the specific provider
        return provider_class(config, tools)
    
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
        messages: List[Message],
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
        messages: List[Message],
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
        message: Message,
        history: List[Message],
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
