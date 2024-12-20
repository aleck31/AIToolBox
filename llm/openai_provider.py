from typing import Dict, List, Optional, AsyncIterator, Union
import google.generativeai as genai
from google.generativeai.types import content_types
from core.logger import logger
from . import (
    LLMAPIProvider,
    LLMConfig,
    Message,
    LLMResponse
)


class OpenAIProvider(LLMAPIProvider):
    """Anthropic LLM API provider implementation"""

    pass   
 