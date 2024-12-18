from typing import Dict, List, Optional, AsyncIterator, Union
import google.generativeai as genai
from google.generativeai.types import content_types

from . import (
    BaseLLMProvider,
    LLMConfig,
    Message,
    LLMResponse,
    ModelProvider,
    ConfigurationError,
    AuthenticationError,
    RateLimitError,
    ModelError
)
from core.logger import logger

class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider implementation"""
    
    def _validate_config(self) -> None:
        """Validate Gemini-specific configuration"""
        if not self.config.api_key:
            raise ConfigurationError("API key must be specified for Gemini")
        if not self.config.model_id:
            raise ConfigurationError("Model ID must be specified for Gemini")

    def _initialize_client(self) -> None:
        """Initialize Gemini client"""
        try:
            genai.configure(api_key=self.config.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.config.model_id,
                generation_config=self._get_generation_config()
            )
        except Exception as e:
            raise ConfigurationError(f"Failed to initialize Gemini client: {str(e)}")

    def _get_generation_config(self) -> genai.GenerationConfig:
        """Get Gemini-specific generation configuration"""
        return genai.GenerationConfig(
            max_output_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=200,  # Gemini-specific parameter
            candidate_count=1
        )

    def _handle_gemini_error(self, error: Exception) -> None:
        """Handle Gemini-specific errors"""
        error_message = str(error)
        
        if "quota exceeded" in error_message.lower():
            raise RateLimitError(f"Rate limit exceeded: {error_message}")
        elif "unauthorized" in error_message.lower():
            raise AuthenticationError(f"Authentication failed: {error_message}")
        elif "invalid request" in error_message.lower():
            raise ConfigurationError(f"Invalid configuration: {error_message}")
        else:
            raise ModelError(f"Gemini error: {error_message}")

    def prepare_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[content_types.ContentType]:
        """Convert messages to Gemini-specific format"""
        formatted_messages = []
        
        if system_prompt:
            formatted_messages.append({
                "role": "user",
                "parts": [{"text": f"System: {system_prompt}"}]
            })
        
        for message in messages:
            parts = []
            
            if isinstance(message.content, str):
                parts.append({"text": message.content})
            else:
                # Handle multimodal content
                if "text" in message.content:
                    parts.append({"text": message.content["text"]})
                if "image" in message.content:
                    parts.append({
                        "inline_data": {
                            "mime_type": "image/jpeg",  # Adjust based on actual image type
                            "data": message.content["image"]
                        }
                    })
            
            formatted_messages.append({
                "role": "user" if message.role == "user" else "model",
                "parts": parts
            })
        
        return formatted_messages

    async def generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Gemini using generate_content"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Generate response using generate_content
            response = self.model.generate_content(
                formatted_messages,
                generation_config=self._get_generation_config()
            )
            
            return LLMResponse(
                content=response.text,
                usage={
                    "prompt_tokens": response.prompt_token_count,
                    "completion_tokens": response.candidates[0].token_count,
                    "total_tokens": response.prompt_token_count + response.candidates[0].token_count
                },
                metadata={
                    'model_id': self.config.model_id,
                    'safety_ratings': [
                        {r.category: r.probability}
                        for r in response.safety_ratings
                    ] if hasattr(response, 'safety_ratings') else None
                }
            )
            
        except Exception as e:
            self._handle_gemini_error(e)

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate a streaming response from Gemini using generate_content with stream=True"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Generate streaming response using generate_content
            response = self.model.generate_content(
                formatted_messages,
                generation_config=self._get_generation_config(),
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self._handle_gemini_error(e)

    async def multi_turn_generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response using multi-turn chat"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Create chat session with history
            chat = self.model.start_chat(history=formatted_messages[:-1])
            
            # Get last message for the actual query
            last_message = formatted_messages[-1]["parts"]
            
            # Stream response
            response = chat.send_message(
                last_message,
                generation_config=self._get_generation_config(),
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            self._handle_gemini_error(e)

    async def multi_turn_generate(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate complete response using multi-turn chat"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Create chat session with history
            chat = self.model.start_chat(history=formatted_messages[:-1])
            
            # Get last message for the actual query
            last_message = formatted_messages[-1]["parts"]
            
            # Get complete response
            response = chat.send_message(
                last_message,
                generation_config=self._get_generation_config()
            )
            
            return LLMResponse(
                content=response.text,
                usage={
                    "prompt_tokens": response.prompt_token_count,
                    "completion_tokens": response.candidates[0].token_count,
                    "total_tokens": response.prompt_token_count + response.candidates[0].token_count
                },
                metadata={
                    'model_id': self.config.model_id,
                    'safety_ratings': [
                        {r.category: r.probability}
                        for r in response.safety_ratings
                    ] if hasattr(response, 'safety_ratings') else None
                }
            )
                
        except Exception as e:
            self._handle_gemini_error(e)
