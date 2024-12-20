# Copyright iX.
# SPDX-License-Identifier: MIT-0
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union, AsyncIterator
from dataclasses import dataclass


def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting


@dataclass
class LLMConfig:
    """Basic configuration for LLM providers"""
    api_provider: str
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.9
    top_p: float = 0.99
    top_k: int = 200
    stop_sequences: Optional[List[str]] = None


@dataclass
class Message:
    """Basic message structure"""
    role: str
    content: Union[str, Dict]
    context: Optional[Dict] = None


class LLMResponse:
    """LLM response wrapper"""
    def __init__(
        self,
        content: str,
        metadata: Optional[Dict] = None
    ):
        self.content = content
        self.metadata = metadata or {}


class LLMAPIProvider(ABC):
    """Base class for LLM providers"""
    
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
        """Generate a response"""
        pass
    
    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response"""
        pass

