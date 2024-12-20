from typing import Dict, List, Optional, AsyncIterator, Union
import google.generativeai as genai
from google.generativeai.types import content_types
from google.api_core import exceptions
from core.logger import logger
from core.config import env_config
from utils.aws import get_secret
from . import LLMAPIProvider, LLMConfig, Message, LLMResponse


class GeminiProvider(LLMAPIProvider):
    """Google Gemini LLM provider implementation"""
    
    def _validate_config(self) -> None:
        """Validate Gemini-specific configuration"""
        if not self.config.model_id:
            raise exceptions.InvalidArgument(
                "Model ID must be specified for Gemini"
            )
        if self.config.api_provider.upper() != 'GEMINI':
            raise exceptions.InvalidArgument(
                f"Invalid API provider: {self.config.api_provider}"
            )

    def _initialize_client(self) -> None:
        """Initialize Gemini client"""
        try:
            gemini_secret_key = env_config.gemini_config['secret_id']
            api_key = get_secret(gemini_secret_key).get('api_key')
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(
                model_name=self.config.model_id,
                generation_config=self._get_generation_config()
            )
        except Exception as e:
            raise exceptions.FailedPrecondition(f"Failed to initialize Gemini client: {str(e)}")

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
        error_message = str(error).lower()
        
        if "quota exceeded" in error_message:
            raise exceptions.ResourceExhausted(f"Rate limit exceeded: {error}")
        elif "unauthorized" in error_message:
            raise exceptions.Unauthenticated(f"Authentication failed: {error}")
        elif "invalid request" in error_message:
            raise exceptions.InvalidArgument(f"Invalid request: {error}")
        else:
            raise exceptions.Unknown(f"Gemini error: {error}")

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
                metadata={
                    'usage': {
                        "input_tokens": response.prompt_token_count,
                        "output_tokens": response.candidates[0].token_count,
                        "total_tokens": response.prompt_token_count + response.candidates[0].token_count
                    },
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
    ) -> AsyncIterator[Dict]:
        """Generate a streaming response from Gemini using generate_content with stream=True"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Yield message start event
            yield {
                "type": "messageStart",
                "message": {
                    "role": "assistant",
                    "metadata": {
                        "model": self.config.model_id,
                        "usage": {}  # Gemini doesn't provide token usage in stream
                    }
                }
            }
            
            # Generate streaming response using generate_content
            response = self.model.generate_content(
                formatted_messages,
                generation_config=self._get_generation_config(),
                stream=True
            )
            
            async for chunk in response:
                if chunk.text:
                    yield {
                        "type": "contentBlockDelta",
                        "delta": {
                            "text": chunk.text
                        }
                    }
            
            # Yield message stop event
            yield {
                "type": "messageStop",
                "metadata": {
                    "model": self.config.model_id,
                    "usage": {}  # Gemini doesn't provide final token usage in stream
                }
            }
                    
        except Exception as e:
            self._handle_gemini_error(e)

    async def multi_turn_generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response using multi-turn chat"""
        try:
            formatted_messages = self.prepare_messages(messages, system_prompt)
            
            # Yield message start event
            yield {
                "type": "messageStart",
                "message": {
                    "role": "assistant",
                    "metadata": {
                        "model": self.config.model_id,
                        "usage": {}
                    }
                }
            }
            
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
                    yield {
                        "type": "contentBlockDelta",
                        "delta": {
                            "text": chunk.text
                        }
                    }
            
            # Yield message stop event
            yield {
                "type": "messageStop",
                "metadata": {
                    "model": self.config.model_id,
                    "usage": {}
                }
            }
                    
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
                metadata={
                    'usage': {
                        "prompt_tokens": response.prompt_token_count,
                        "completion_tokens": response.candidates[0].token_count,
                        "total_tokens": response.prompt_token_count + response.candidates[0].token_count
                    },
                    'safety_ratings': [
                        {r.category: r.probability}
                        for r in response.safety_ratings
                    ] if hasattr(response, 'safety_ratings') else None
                }
            )
                
        except Exception as e:
            self._handle_gemini_error(e)
