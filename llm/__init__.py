# Copyright iX.
# SPDX-License-Identifier: MIT-0
from typing import Dict, List, Optional, Union, Any
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
    content: Dict # text, image, video, file_path
    thinking: Optional[str] = None  # Thinking text from Reasoning models
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


# Model category and capabilities
VAILD_CATEGORY = ['text', 'vision', 'image', 'video', 'reasoning', 'embedding']
VALID_MODALITY = ['text', 'document', 'image', 'video', 'audio']

@dataclass
class MODEL_CAPABILITIES:
    """Model capabilities configuration"""
    input_modality: List[str] = None  # Support input modalities
    output_modality: List[str] = None # Support output modalities
    streaming: Optional[bool] = None  # Support for streaming responses
    tool_use: Optional[bool] = None  # Support for tool use / function calling
    context_window: Optional[int] = None  # Maximum tokens(context window) size

    def __post_init__(self):
        """Initialize default values if not provided"""
        self.input_modality = self.input_modality or ['text']
        self.output_modality = self.output_modality or ['text']
        self.streaming = True if self.streaming is None else self.streaming
        self.tool_use = False if self.tool_use is None else self.tool_use
        self.context_window = self.context_window or 128*1024

@dataclass
class LLMModel:
    """Represents an LLM model configuration with capabilities"""
    name: str
    model_id: str
    api_provider: str
    category: str   #Legacy to compatibility with existing models
    vendor: str = ""      # Optional
    description: str = "" # Optional
    capabilities: Optional[MODEL_CAPABILITIES] = None

    def __post_init__(self):
        """Validate model attributes after initialization"""
        if not self.name:
            raise ValueError("Model name is required")
        if not self.model_id:
            raise ValueError("Model ID is required")
        if not self.api_provider:
            raise ValueError("API provider is required")
        if self.category not in VAILD_CATEGORY:
            raise ValueError(f"Invalid model category. Must be one of: {VAILD_CATEGORY}")

        # Initialize capabilities if none provided
        self.capabilities = self.capabilities or MODEL_CAPABILITIES()

    def supports_input(self, modality: str) -> bool:
        """Check if model supports a specific input modality"""
        return modality in self.capabilities.input_modality

    def supports_output(self, modality: str) -> bool:
        """Check if model supports a specific output modality"""
        return modality in self.capabilities.output_modality

    def get_capability(self, name: str) -> Any:
        """Get a capability value by name"""
        if not hasattr(self.capabilities, name):
            raise ValueError(f"Invalid capability name: {name}")
        return getattr(self.capabilities, name)

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage, excluding None values"""
        data = {k: v for k, v in asdict(self).items() if v is not None}
        # Convert capabilities to dict if present
        if self.capabilities:
            data['capabilities'] = asdict(self.capabilities)
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'LLMModel':
        """Create from dictionary"""
        # Make a copy to avoid modifying the input
        data = data.copy()
        
        # Extract and convert capabilities data if present
        capabilities_data = data.pop('capabilities', None)
        capabilities = MODEL_CAPABILITIES(**capabilities_data) if capabilities_data else None
        
        # Create instance with remaining data
        return cls(
            name=data['name'],
            model_id=data['model_id'],
            api_provider=data['api_provider'],
            category=data.get('category', 'text'),
            vendor=data.get('vendor', ''),
            description=data.get('description', ''),
            capabilities=capabilities
        )
