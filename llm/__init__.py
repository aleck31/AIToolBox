# Copyright iX.
# SPDX-License-Identifier: MIT-0
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """Model-specific parameters for LLM providers"""
    api_provider: str
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.9
    top_p: float = 0.99
    top_k: Optional[int] = 200
    stop_sequences: Optional[List[str]] = None


@dataclass
class Message:
    """Basic message structure"""
    role: str
    content: Union[str, Dict]
    context: Optional[Dict] = None


@dataclass
class LLMResponse:
    """Basic LLM response structure"""
    content: str
    tool_calls: Optional[List[Dict]] = None
    tool_results: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None


VALID_MODEL_TYPES = ['text', 'multimodal', 'image', 'embedding']

@dataclass
class LLMModel:
    """Represents an LLM model configuration"""
    name: str
    model_id: str
    api_provider: str
    type: str
    vendor: str = ""      # Optional
    description: str = "" # Optional

    def __post_init__(self):
        """Validate model attributes after initialization"""
        if not self.name:
            raise ValueError("Model name is required")
        if not self.model_id:
            raise ValueError("Model ID is required")
        if not self.api_provider:
            raise ValueError("API provider is required")
        if self.type not in VALID_MODEL_TYPES:
            raise ValueError(f"Invalid model type. Must be one of: {', '.join(VALID_MODEL_TYPES)}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {
            'name': self.name,
            'model_id': self.model_id,
            'api_provider': self.api_provider,
            'type': self.type,
            'vendor': self.vendor,
            'description': self.description
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMModel':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            model_id=data['model_id'],
            api_provider=data['api_provider'],
            type=data.get('type', 'text'),
            vendor=data.get('vendor', ''),
            description=data.get('description', '')
        )

def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting
