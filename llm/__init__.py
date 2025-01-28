# Copyright iX.
# SPDX-License-Identifier: MIT-0
from typing import Dict, List, Optional, Union
from dataclasses import dataclass, asdict


@dataclass
class LLMConfig:
    """Model-specific parameters for LLM providers"""
    # Do we need to update LLMConfig for compatibility with generative models like Stable Diffusion and Nova?
    api_provider: str
    model_id: str
    max_tokens: int = 4096
    temperature: float = 0.9
    top_p: float = 0.99
    top_k: Optional[int] = 200
    stop_sequences: Optional[List[str]] = None


@dataclass
class Message:
    """Chat message structure"""
    role: str
    content: Union[str, Dict]
    context: Optional[Dict] = None    
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert message to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class LLMResponse:
    """Basic LLM response structure"""
    content: Dict # text, image, video
    metadata: Optional[Dict] = None

@dataclass
class ResponseMetadata:
    """Metadata structure for LLM responses with stop_reason"""
    stop_reason: Optional[str] = None
    usage: Optional[Dict] = None
    metrics: Optional[Dict] = None
    performance_config: Optional[Dict] = None

    def update_from_chunk(self, chunk_metadata: Dict) -> None:
        """Update metadata fields from a chunk"""
        self.usage = chunk_metadata.get('usage', self.usage)
        self.metrics = chunk_metadata.get('metrics', self.metrics)
        self.performance_config = chunk_metadata.get('performanceConfig', self.performance_config)

    def to_dict(self) -> Dict:
        """Convert metadata to dictionary, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}


VALID_MODALITY = ['text', 'vision', 'image', 'video', 'embedding']

@dataclass
class LLMModel:
    """Represents an LLM model configuration"""
    name: str
    model_id: str
    api_provider: str
    modality: str
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
        if self.modality not in VALID_MODALITY:
            raise ValueError(f"Invalid model modality. Must be one of: {', '.join(VALID_MODALITY)}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage, excluding None values"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMModel':
        """Create from dictionary"""
        return cls(
            name=data['name'],
            model_id=data['model_id'],
            api_provider=data['api_provider'],
            modality=data.get('modality', 'text'),
            vendor=data.get('vendor', ''),
            description=data.get('description', '')
        )
