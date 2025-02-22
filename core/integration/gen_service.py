from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session
from llm.api_providers.base import LLMConfig, Message
from .base_service import BaseService


class GenService(BaseService):
    """General content generation service"""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        enabled_tools: Optional[List[str]] = None,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize GenService with model configuration"""
        super().__init__(enabled_tools=enabled_tools, cache_ttl=cache_ttl)
        self.default_llm_config = llm_config

    def _prepare_message(self, content: Dict[str, str]) -> Message:
        """Create standardized message format"""
        return Message(
            role="user",
            content=content if isinstance(content, dict) else {"text": str(content)}
        )

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
            # Always use the default model for stateless operations
            llm = self._get_llm_provider(self.default_llm_config.model_id)
            
            logger.debug(f"[GenService] Content for stateless generation: {content}")
            
            # Create standardized message
            messages = [self._prepare_message(content)]

            # Generate response
            response = await llm.generate_content(
                messages=messages,
                system_prompt=system_prompt,
                **(option_params or {})
            )
            
            if not response.content:
                raise ValueError("Empty response from LLM")
                
            return response.content.get('text', '')

        except Exception as e:
            logger.error(f"[GenService] Failed to generate text stateless: {str(e)}")
            return "I apologize, but I encountered an error. Please try again."

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
            llm = self._get_llm_provider(model_id)
            
            logger.debug(f"[GenService] Content for session {session.session_id}: {content}")
            
            # Create message with multimodal content support
            message = self._prepare_message(content)

            # Generate response
            response = await llm.generate_content(
                messages=[message],
                system_prompt=session.context.get('system_prompt', ''),
                **(option_params or {})
            )

            if not response.content:
                raise ValueError("Empty response from LLM")
                
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
            await self.session_store.update_session(session)

            return response.content.get('text', '')

        except Exception as e:
            logger.error(f"[GenService] Failed to generate text in session {session.session_id}: {str(e)}")
            return "I apologize, but I encountered an error. Please try again."

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
            llm = self._get_llm_provider(model_id)

            logger.debug(f"[GenService] Content for session {session.session_name}: {content}")

            # Create message for generation
            message = self._prepare_message(content)

            # Track response state
            accumulated_text = []
            response_metadata = {}

            try:
                async for chunk in llm.generate_stream(
                    messages=[message],
                    system_prompt=session.context.get('system_prompt', ''),
                    **(option_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"[GenService] Unexpected chunk type: {type(chunk)}")
                        continue

                    # Update metadata
                    if metadata := chunk.get('metadata'):
                        response_metadata.update(metadata)
                    
                    # Process text content
                    if text := chunk.get('content', {}).get('text', ''):
                        accumulated_text.append(text)
                        yield text

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
                    await self.session_store.update_session(session)

            except Exception as e:
                logger.error(f"[GenService] Failed to get response from LLM: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."

        except Exception as e:
            logger.error(f"[GenService] Failed to generate text stream in session {session.session_id}: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
