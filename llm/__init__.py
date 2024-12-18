# Copyright iX.
# SPDX-License-Identifier: MIT-0
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, AsyncIterator
from dataclasses import dataclass
from enum import Enum


def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting


class ModelProvider(Enum):
    BEDROCK = "bedrock"
    GEMINI = "gemini"

@dataclass
class LLMConfig:
    """Configuration for LLM providers"""
    provider: ModelProvider
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.9
    top_p: float = 0.99
    stop_sequences: Optional[List[str]] = None

@dataclass
class Message:
    """Represents a chat message"""
    role: str
    content: Union[str, Dict]
    metadata: Optional[Dict] = None

class LLMResponse:
    """Wrapper for LLM responses"""
    def __init__(
        self,
        content: str,
        usage: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ):
        self.content = content
        self.usage = usage or {}
        self.metadata = metadata or {}

class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    def __init__(self, config: LLMConfig):
        self.config = config
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
    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response from the LLM"""
        pass
    
    def prepare_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Convert messages to provider-specific format"""
        pass

class LLMException(Exception):
    """Base exception for LLM-related errors"""
    pass

class ConfigurationError(LLMException):
    """Raised when there's an issue with LLM configuration"""
    pass

class AuthenticationError(LLMException):
    """Raised when there's an authentication issue"""
    pass

class RateLimitError(LLMException):
    """Raised when rate limit is exceeded"""
    pass

class ModelError(LLMException):
    """Raised when there's an error with the model"""
    pass
