from typing import Dict, Optional, AsyncIterator
from core.logger import logger
from core.session import Session
from core.module_config import module_config
from llm.api_providers import LLMMessage, LLMProviderError
from llm.model_manager import model_manager
from . import BaseService


class GenService(BaseService):
    """General content generation service"""
    
    def __init__(
        self,
        module_name: str,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize GenService
        
        Args:
            module_name: Name of the module using this service
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(module_name=module_name, cache_ttl=cache_ttl)

    def _prepare_message(
        self,
        content: Dict[str, str],
        model_id: Optional[str] = None
    ) -> LLMMessage:
        """Create standardized message with content filtering
        
        Args:
            content: Message content (text and/or files)
            model_id: Optional model ID for content filtering
            
        Returns:
            LLMMessage: Standardized message instance
            
        Note:
            Filters content based on model's supported input modalities
        """
        # Normalize content to dict format
        if not isinstance(content, dict):
            content = {"text": str(content)}
            
        # Filter content based on model capabilities if model_id provided
        if model_id and "files" in content:
            model = model_manager.get_model_by_id(model_id)
            if model and model.capabilities:
                supported_modalities = model.capabilities.input_modality
                # Remove files for text-only models
                if len(supported_modalities) == 1 and supported_modalities[0] == "text":
                    content.pop("files")
                    content["text"] = (content.get("text", "") + 
                        "\n[Note: Files were removed as the current model does not support multimodal content.]").strip()
            
        return LLMMessage(role="user", content=content)

    async def gen_text_stateless(
        self,
        content: Dict[str, str],
        system_prompt: Optional[str] = None,
        option_params: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate text using the configured LLM without session context
        
        Args:
            content: Dictionary containing text and optional files
            system_prompt: Optional system prompt for one-off generation
            option_params: Optional parameters for LLM generation
            
        Returns:
            str: Generated text
        """
        try:
            # Get default model from module config
            model_id = module_config.get_default_model(self.module_name)
            if not model_id:
                raise ValueError(f"No default model configured for {self.module_name}")
            
            # Get provider with module's default configuration
            provider = self._get_llm_provider(model_id)
            
            logger.debug(f"[GenService] Content for stateless generation: {content}")
            
            # Create message with content filtering
            messages = [self._prepare_message(content, model_id)]

            # Generate response
            response = await provider.generate_content(
                messages=messages,
                system_prompt=system_prompt,
                **(option_params or {})
            )

            if not response.content:
                raise ValueError("Empty response from LLM Provider")

            return response.content.get('text', '')

        except LLMProviderError as e:
            logger.error(f"[GenService] Failed to generate text stateless: {e.error_code}")
            # Return user-friendly message from provider
            return f"I apologize, {e.message}"

    async def gen_text(
        self,
        session: Session,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate text using the configured LLM with session context
        
        Args:
            session: Session for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Returns:
            str: Generated text
        """
        try:
            # Get model_id with fallback to module default
            model_id = await self.get_session_model(session)

            # Get LLM provider
            provider = self._get_llm_provider(model_id)
            
            logger.debug(f"[GenService] Content for session {session.session_id}: {content}")
            
            # Create message with content filtering
            message = self._prepare_message(content, model_id)

            # Generate response
            response = await provider.generate_content(
                messages=[message],
                system_prompt=session.context.get('system_prompt', ''),
                **(option_params or {})
            )

            if not response.content:
                raise ValueError("Empty response from LLM Provider")
                
            # Add interactions to session
            session.add_interaction({
                "role": "user",
                "content": content
            })
            
            session.add_interaction({
                "role": "assistant",
                "content": response.content,
                "metadata": getattr(response, 'metadata', None)
            })
            
            # Update session
            await self.session_store.save_session(session)

            return response.content.get('text', '')

        except LLMProviderError as e:
            logger.error(f"[GenService] Failed to generate text in session {session.session_id}: {e.error_code}")
            # Return user-friendly message from provider
            return f"I apologize, {e.message}"

    async def gen_text_stream(
        self,
        session: Session,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> AsyncIterator[str]:
        """Generate text with streaming response and session context
        
        Args:
            session: Session for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Yields:
            str: Generated text chunks in streaming fashion
        """
        try:            
            # Get model_id with fallback to module default
            model_id = await self.get_session_model(session)

            # Get LLM provider
            provider = self._get_llm_provider(model_id)

            logger.debug(f"[GenService] Content for session {session.session_name}: {content}")

            # Create message with content filtering
            message = self._prepare_message(content, model_id)

            # Track response state
            accumulated_text = []
            response_metadata = {}

            try:
                async for chunk in provider.generate_stream(
                    messages=[message],
                    system_prompt=session.context.get('system_prompt', ''),
                    **(option_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"[GenService] Unexpected chunk type: {type(chunk)}")
                        continue

                    # Pass through thinking or content chunks
                    if thinking := chunk.get('thinking'):
                        yield {'thinking': thinking}
                    elif content := chunk.get('content', {}):
                        # Handle text
                        if text := content.get('text'):
                            yield {'text': text}
                            accumulated_text.append(text)

                    # Update metadata if it exists
                    if metadata := chunk.get('metadata'):
                        response_metadata.update(metadata)

                # Add complete interaction to session
                if accumulated_text:
                    # Add messages in order
                    session.add_interaction({
                        "role": "user",
                        "content": content
                    })

                    session.add_interaction({
                        "role": "assistant",
                        "content": {"text": ''.join(accumulated_text)},
                        "metadata": response_metadata or None
                    })

                    # Persist to session store
                    await self.session_store.save_session(session)

            except LLMProviderError as e:
                logger.error(f"[GenService] Failed to get response from LLM Provider: {e.error_code}")
                # Yield user-friendly message from provider
                yield f"I apologize, {e.message}"

        except Exception as e:
            logger.error(f"[GenService] Failed to generate text stream in session {session.session_id}: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
