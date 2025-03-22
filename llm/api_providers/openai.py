from typing import Dict, List, Optional, Iterator, AsyncIterator
import openai
from openai import OpenAI
from openai import AsyncOpenAI
from core.logger import logger
from core.config import env_config
from utils.aws import get_secret
from . import LLMAPIProvider, LLMConfig, Message, LLMResponse, LLMProviderError


class OpenAIProvider(LLMAPIProvider):
    """OpenAI LLM API provider implementation"""
    
    def __init__(self, config: LLMConfig, tools=None):
        """Initialize provider with config and tools
        
        Args:
            config: LLM configuration
            tools: Optional list of tool specifications
        """
        super().__init__(config, tools)
        self._initialize_client()

    def _validate_config(self) -> None:
        """Validate OpenAI-specific configuration"""
        logger.debug(f"[OpenAIProvider] Model Configurations: {self.config}")
        if not self.config.model_id:
            raise ValueError("Model ID must be specified for OpenAI")
        if self.config.api_provider.upper() != 'OPENAI':
            raise ValueError(f"Invalid API provider: {self.config.api_provider}")

    def _initialize_client(self) -> None:
        """Initialize OpenAI client"""
        try:
            openai_secret_key = env_config.openai_config['secret_id']
            api_key = get_secret(openai_secret_key).get('api_key')
            if not api_key:
                raise ValueError("OpenAI API key not configured")
            
            # Initialize sync and async clients
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)
            
        except Exception as e:
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")

    def _handle_openai_error(self, error: Exception):
        """Handle OpenAI-specific errors by raising LLMProviderError
        
        Args:
            error: OpenAI API exception
            
        Raises:
            LLMProviderError with error code, user-friendly message, and technical details
        """
        error_code = type(error).__name__
        error_detail = str(error)
        
        logger.error(f"[OpenAIProvider] {error_code} - {error_detail}")
        
        # Format user-friendly message based on exception type
        if isinstance(error, openai.RateLimitError):
            message = "Rate limit exceeded. Please try again later."
        elif isinstance(error, openai.AuthenticationError):
            message = "Authentication failed. Please check your API key."
        elif isinstance(error, openai.BadRequestError):
            message = "Invalid request format. Please try again with different input."
        elif isinstance(error, openai.APITimeoutError):
            message = "The request timed out. Please try again."
        elif isinstance(error, openai.APIConnectionError):
            message = "Failed to connect to OpenAI API. Please check your network connection."
        elif isinstance(error, openai.InternalServerError):
            message = "OpenAI server error. Please try again later."
        elif isinstance(error, openai.APIStatusError):
            message = "API request failed. Please try again with different parameters."
        else:
            message = "An unexpected error occurred. Please try again."
            
        raise LLMProviderError(error_code, message, error_detail)

    def _convert_message(self, message: Message) -> Dict:
        """Convert a single message into OpenAI-specific format
        
        Args:
            message: Message to format
            
        Returns:
            Dict with role and content formatted for OpenAI API
        """
        content_parts = []

        # Handle context if present
        context = getattr(message, 'context', None)
        if context and isinstance(context, dict):
            context_items = []
            for key, value in context.items():
                if value is not None:
                    readable_key = key.replace('_', ' ').capitalize()
                    context_items.append(f"{readable_key}: {value}")
            if context_items:
                content_parts.append({
                    "type": "text",
                    "text": f"Context Information:\n{' | '.join(context_items)}\n"
                })

        # Handle message content
        if isinstance(message.content, str):
            if message.content.strip():
                content_parts.append({
                    "type": "text",
                    "text": message.content
                })
        # Handle multimodal content from Gradio chatbox
        elif isinstance(message.content, dict):
            if text := message.content.get("text", "").strip():
                content_parts.append({
                    "type": "text",
                    "text": text
                })
            # Add files if present
            if files := message.content.get("files", []):
                for file_path in files:
                    try:
                        if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                            with open(file_path, 'rb') as file:
                                content_parts.append({
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/jpeg;base64,{file.read()}", "detail": "auto"}
                                })
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")

        return {"role": message.role, "content": content_parts}

    def _convert_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Convert messages to OpenAI-specific format with system prompt handling
        
        Args:
            messages: List of messages to format
            system_prompt: Optional system prompt to set
            
        Returns:
            List of Converted messages for OpenAI API
        """
        converted_messages = []
        
        # Add system message if provided
        if system_prompt:
            converted_messages.append({
                "role": "system",
                "content": [{"type": "text", "text": system_prompt}]
            })
            
        # Convert each message
        converted_messages.extend([self._convert_message(msg) for msg in messages])
        
        return converted_messages

    def _extract_metadata(self, response) -> Dict:
        """Extract metadata from OpenAI response"""
        usage = response.usage if hasattr(response, 'usage') else None
        return {
            'metadata': {
                'model': self.config.model_id,
                'usage': {
                    'prompt_tokens': usage.prompt_tokens if usage else None,
                    'completion_tokens': usage.completion_tokens if usage else None,
                    'total_tokens': usage.total_tokens if usage else None
                } if usage else None
            }
        }

    async def generate_content(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from OpenAI
        
        Args:
            messages: List of messages
            system_prompt: Optional system prompt
            **kwargs: Additional parameters for inference
            
        Returns:
            LLMResponse containing generated content and metadata
        """
        try:
            llm_messages = self._convert_messages(messages, system_prompt)
            logger.debug(f"[OpenAIProvider] Converted messages: {llm_messages}")
            
            response = await self.async_client.chat.completions.create(
                model=self.config.model_id,
                messages=llm_messages,
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                top_p=kwargs.get('top_p', self.config.top_p),
                stream=False
            )
            
            # Extract content from response and convert to standard format
            resp_content = response.choices[0].message.content
            if isinstance(resp_content, list):
                # For multimodal responses, use first text content or empty string
                text_parts = [part["text"] for part in resp_content if part.get("type") == "text"]
                content = {"text": text_parts[0] if text_parts else ""}
            else:
                # For string content (older models), wrap in standard format
                content = {"text": resp_content}
            metadata = self._extract_metadata(response)
            
            return LLMResponse(
                content=content,
                metadata=metadata.get('metadata')
            )
            
        except Exception as e:
            self._handle_openai_error(e)

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate a streaming response from OpenAI
        
        Args:
            messages: List of messages
            system_prompt: Optional system prompt
            **kwargs: Additional parameters for inference
            
        Yields:
            Dict containing content chunks and metadata
        """
        try:
            llm_messages = self._convert_messages(messages, system_prompt)
            logger.debug(f"[OpenAIProvider] Converted messages for streaming: {llm_messages}")
            
            async for chunk in self.async_client.chat.completions.create(
                model=self.config.model_id,
                messages=llm_messages,
                temperature=kwargs.get('temperature', self.config.temperature),
                max_tokens=kwargs.get('max_tokens', self.config.max_tokens),
                top_p=kwargs.get('top_p', self.config.top_p),
                stream=True
            ):
                if content := chunk.choices[0].delta.content:
                    # Handle both string and list content formats
                    if isinstance(content, list):
                        text_parts = [part["text"] for part in content if part.get("type") == "text"]
                        if text_parts:
                            yield {'content': {'text': text_parts[0]}}
                    else:
                        # For backward compatibility with older models that return string content
                        yield {'content': {'text': content}}
                
                if chunk.choices[0].finish_reason:
                    yield {'metadata': {'stop_reason': chunk.choices[0].finish_reason}}
                    
        except Exception as e:
            self._handle_openai_error(e)

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = None,
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
            Dict containing content chunks and metadata
        """
        try:
            # Prepare conversation messages
            messages = []
            if history:
                messages.extend(history)   
            # Add current message
            messages.append(message)
            logger.info(f"[OpenAIProvider] Processing multi-turn chat with {len(messages)} messages")

            # Use generate_stream for streaming response
            async for chunk in self.generate_stream(
                    messages, 
                    system_prompt, 
                    **kwargs
                ):
                    yield chunk

        except Exception as e:
            self._handle_openai_error(e)
