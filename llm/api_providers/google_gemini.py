from typing import Dict, List, Optional, Iterator, AsyncIterator
import google.generativeai as genai
from google.generativeai.types import content_types
from google.api_core import exceptions
from core.logger import logger
from core.config import env_config
from utils.aws import get_secret
from .base import LLMAPIProvider, LLMConfig, Message, LLMResponse


class GeminiProvider(LLMAPIProvider):
    """Google Gemini LLM provider implementation"""
    
    def __init__(self, config: LLMConfig, tools=None):
        """Initialize provider with config and tools
        
        Args:
            config: LLM configuration
            tools: Optional list of tool specifications
        """
        super().__init__(config, tools)
        self._initialize_client()
    
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
            if not api_key:
                raise ValueError("Gemini API key not configured")            
            genai.configure(api_key=api_key)
            
            # Initialize model with default system_instruction
            model_args = {
                "model_name": self.config.model_id,
                "generation_config": self._get_generation_config()
            }
            
            # Set a simple default system instruction
            DEFAULT_SYSTEM_PROMPT = """
            You are a helpful AI assistant. 
            Be direct, accurate, and professional in your responses.
            Acknowledge your limitations and ask for clarification when needed.
            """
            model_args["system_instruction"] = self._format_system_prompt(DEFAULT_SYSTEM_PROMPT)
            
            self.model = genai.GenerativeModel(**model_args)
        except Exception as e:
            raise exceptions.FailedPrecondition(f"Failed to initialize Gemini client: {str(e)}")

    def _get_generation_config(self) -> genai.GenerationConfig:
        """Get Gemini-specific generation configuration"""
        return genai.GenerationConfig(
            max_output_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            candidate_count=1
        )

    def _handle_gemini_error(self, error: Exception) -> None:
        """Handle Gemini-specific errors"""
        error_message = str(error).lower()
        logger.error(f"[GeminiProvider] {error_message}")
        if "quota exceeded" in error_message:
            raise exceptions.ResourceExhausted(f"Rate limit exceeded: {error}")
        elif "unauthorized" in error_message:
            raise exceptions.Unauthenticated(f"Authentication failed: {error}")
        elif "invalid request" in error_message:
            raise exceptions.InvalidArgument(f"Invalid request: {error}")
        elif "dangerous_content" in error_message:
            # Handle safety filter triggers
            logger.warning("[GeminiProvider] Safety filter triggered, please try again.")
            return
        else:
            raise exceptions.Unknown(f"Gemini error: {error}")

    def _format_system_prompt(self, system_prompt: str) -> List[str]:
        """Format system prompt into list of instructions"""
        if not system_prompt:
            return []
        return [
            instruction.strip() 
            for instruction in system_prompt.split('\n') 
            if instruction.strip()
        ]

    def _convert_messages(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None
    ) -> List[content_types.ContentType]:
        """Convert messages to Gemini-specific format with system prompt handling
        
        Args:
            messages: List of messages to format
            system_prompt: Optional system prompt to set
            
        Returns:
            List of Converted messages for Gemini API
        """
        # Update model with system prompt if provided
        if system_prompt:
            # Get current safety settings if model exists
            safety_settings = getattr(self.model, '_safety_settings', None)
            system_instruction = self._format_system_prompt(system_prompt)
            
            model_args = {
                "model_name": self.config.model_id,
                "generation_config": self._get_generation_config(),
                "system_instruction": system_instruction
            }
            
            # Only set safety settings if they exist
            if safety_settings:
                model_args["safety_settings"] = safety_settings
                
            self.model = genai.GenerativeModel(**model_args)
            logger.debug(f"Updated Provider's model with new system_instruction: {system_instruction}")

        # Convert each message using _convert_message
        return [self._convert_message(msg) for msg in messages]

    def _convert_message(self, message: Message) -> Dict:
        """Convert a single message into Gemini-specific format
        
        Args:
            message: Message to format
            
        Returns:
            Dict with role and parts formatted for Gemini API
        """
        parts = []
        
        # Handle context if present and not None
        context = getattr(message, 'context', None)
        if context and isinstance(context, dict):
            context_items = []
            for key, value in context.items():
                if value is not None:
                    # Convert snake_case to spaces and capitalize
                    readable_key = key.replace('_', ' ').capitalize()
                    context_items.append(f"{readable_key}: {value}")
            if context_items:
                # Add formatted context with clear labeling
                parts.append({
                    "text": f"Context Information:\n{' | '.join(context_items)}\n"
                })

        # Handle message content
        if isinstance(message.content, str):
            if message.content.strip():  # Skip empty strings
                parts.append({"text": message.content})
        # Handle multimodal content from Gradio chatbox
        elif isinstance(message.content, dict):
            # Add text if present
            if text := message.content.get("text", "").strip():
                parts.append({"text": text})

            # Add files if present
            if files := message.content.get("files", []):
                for file_path in files:
                    try:
                        # Handle files using genai.upload_file
                        file_ref = genai.upload_file(path=file_path)
                        parts.append(file_ref)
                    except Exception as e:
                        logger.error(f"Error uploading file {file_path}: {str(e)}")
                        continue

        return {"role": message.role, "parts": parts}

    def _generate_content_sync(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Synchronous implementation of content generation"""
        try:
            llm_messages = self._convert_messages(messages, system_prompt)
            logger.debug(f"Converted messages: {llm_messages}")
            
            # Update model args if new system prompt provided
            model_args = {
                "generation_config": self._get_generation_config()
            }
            
            # Generate response using generate_content
            response = self.model.generate_content(
                contents=llm_messages,
                **model_args
            )

            logger.debug(f"Raw Gemini response: {response}")
            
            return LLMResponse(
                content=response.text,
                metadata={
                    'usage': {
                        "prompt_tokens": response.usage_metadata.prompt_token_count,
                        "completion_tokens": response.usage_metadata.candidates_token_count,
                        "total_tokens": response.usage_metadata.total_token_count
                    },
                    'safety_ratings': [
                        {r.category: r.probability}
                        for r in response.safety_ratings
                    ] if hasattr(response, 'safety_ratings') else None
                }
            )
            
        except Exception as e:
            self._handle_gemini_error(e)

    def _generate_stream_sync(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Iterator[Dict]:
        """Synchronous implementation of streaming generation"""
        try:
            llm_messages = self._convert_messages(messages, system_prompt)
            logger.debug(f"Converted messages: {llm_messages}")
            
            # Update model args if new system prompt provided
            model_args = {
                "generation_config": self._get_generation_config()
            }
            
            # Generate streaming response using generate_content
            response = self.model.generate_content(
                contents=llm_messages,
                stream=True,
                **model_args
            )
            
            # Stream response chunks
            for chunk in response:
                if hasattr(chunk, 'text'):
                    yield {'content': {'text': chunk.text}}
                
                # Extract usage metadata if available
                if hasattr(chunk, 'usage_metadata'):
                    yield {
                        'metadata': {
                            'model': self.config.model_id,
                            'usage': {
                                'prompt_tokens': chunk.usage_metadata.prompt_token_count,
                                'completion_tokens': chunk.usage_metadata.candidates_token_count,
                                'total_tokens': chunk.usage_metadata.total_token_count
                            }
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
            self._handle_gemini_error(e)

    async def generate_content(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Generate a response from Gemini using generate_content"""
        return self._generate_content_sync(messages, system_prompt, **kwargs)

    async def generate_stream(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate a streaming response from Gemini using generate_content with stream=True"""
        for chunk in self._generate_stream_sync(messages, system_prompt, **kwargs):
            yield chunk

    async def multi_turn_generate(
        self,
        message: Message,
        history: Optional[List[Message]] = [],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[Dict]:
        """Generate streaming response using multi-turn chat
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
        try:
            # Format history message
            if history:
                logger.debug(f"[GeminiProvider] Unconverted history messages: {history}")
                history_messages = self._convert_messages(history, system_prompt)
                logger.debug(f"[GeminiProvider] Converted history messages: {history_messages}")

            # Format current user message
            current_message = self._convert_message(message)
            logger.debug(f"[GeminiProvider] Converted Current message: {current_message}")

            # Create chat session with history
            chat = self.model.start_chat(history=history_messages)
            logger.debug(f"[GeminiProvider] Processing multi-turn chat with {len(history_messages)+1} messages")

            # Update model args if new system prompt provided
            model_args = {
                "generation_config": self._get_generation_config()
            }
            
            # Stream response using formatted message parts
            for chunk in chat.send_message(
                current_message['parts'],
                stream=True,
                **model_args
            ):
                if hasattr(chunk, 'text'):
                    yield {
                        'content': {'text': chunk.text}
                    }
                
                # Extract usage metadata if available
                if hasattr(chunk, 'usage_metadata'):
                    yield {
                        'metadata': {
                            'model': self.config.model_id,
                            'usage': {
                                'prompt_tokens': chunk.usage_metadata.prompt_token_count,
                                'completion_tokens': chunk.usage_metadata.candidates_token_count,
                                'total_tokens': chunk.usage_metadata.total_token_count
                            }
                        }
                    }
                    
        except Exception as e:
            logger.error(f"Multi turn Generate Error: {str(e)}")
            self._handle_gemini_error(e)
