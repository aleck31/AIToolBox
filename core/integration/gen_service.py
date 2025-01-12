from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session, SessionStore
from llm.model_manager import model_manager
from llm.api_providers.base import LLMConfig, Message, LLMAPIProvider


#  GenService will be used by multiple modules, including text, vison, summary, coding, oneshot
class GenService:
    """General content generation service"""
    
    def __init__(
        self,
        llm_config: LLMConfig,
        enabled_tools: Optional[List[str]] = None
    ):
        """Initialize text service with model configuration
        
        Args:
            llm_config: LLM configuration containing model ID and parameters
            enabled_tools: Optional list of tool module names to enable
        """
        self.session_store = SessionStore.get_instance()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self.enabled_tools = enabled_tools or []
        
        # Validate model exists and config matches
        model = model_manager.get_model_by_id(llm_config.model_id)
        if not model:
            raise ValueError(f"Model not found: {llm_config.model_id}")
        
        self.default_llm_config = llm_config

    def _get_llm_provider(self, model_id: str) -> LLMAPIProvider:
        """Get or create LLM API provider for given model
        
        Args:
            model_id: ID of the model to get provider for
            
        Returns:
            LLMAPIProvider: Cached or newly created provider
            
        Raises:
            ValueError: If model not found or provider not supported
        """
        # Return cached provider if exists
        if model_id in self._llm_providers:
            return self._llm_providers[model_id]
            
        # Get model info
        model = model_manager.get_model_by_id(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")
            
        # Create config using model info and default parameters
        config = LLMConfig(
            api_provider=model.api_provider,
            model_id=model_id,
            max_tokens=self.default_llm_config.max_tokens,
            temperature=self.default_llm_config.temperature,
            top_p=self.default_llm_config.top_p,
            stop_sequences=self.default_llm_config.stop_sequences
        )
        
        # Create provider using factory method with enabled tools
        provider = LLMAPIProvider.create(config, self.enabled_tools)
        self._llm_providers[model_id] = provider
        return provider

    def _prepare_message(self, content: Dict[str, str]) -> Message:
        """Create standardized message format
        
        Args:
            content: Dictionary containing text and optional files
            
        Returns:
            Message: Standardized message object
        """
        return Message(
            role="user",
            content=content if isinstance(content, dict) else {"text": str(content)}
            # context={"current_time": datetime.now().isoformat() }
        )

    async def get_or_create_session(
        self,
        user_id: str,
        module_name: str,
        session_name: Optional[str] = None
    ) -> Session:
        """Get existing active session or Create new session for stateful generation"""
        try:
            # Query existing sessions to prevent creating duplicate session for a module
            active_sessions = await self.session_store.list_sessions(
                user_id=user_id,
                module_name=module_name
            )

            if active_sessions:
                session = active_sessions[0]
                logger.debug(
                    f"Found existing {module_name} session {session.session_id} "
                    f"for user {user_id} (created: {session.created_time})"
                )
                return session

            # Create new session if none active
            session_name = session_name or f"{module_name.title()} Session"
            session = await self.session_store.create_session(
                user_id=user_id,
                module_name=module_name,
                session_name=session_name
            )

            logger.debug(
                f"Created new {module_name} session {session.session_id} "
                f"for user {user_id} (created: {session.created_time})"
            )
            
            return session
        except HTTPException as e:
            logger.error(f"Error in [get_or_create_session]: {str(e)}")
            raise e

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
            # Get model ID from config
            model_id = self.default_llm_config.model_id
            llm = self._get_llm_provider(model_id)
            
            # Debug input content
            logger.debug(f"Content received for stateless generation: {content}")
            
            # Create standardized message
            messages = [self._prepare_message(content)]

            # Generate response
            response = await llm.generate_content(
                messages=messages,
                system_prompt=system_prompt,
                **(option_params or {})
            )
            
            if response.content:
                return response.content.get('text')
            else:
                raise ValueError("Empty response from LLM")           

        except Exception as e:
            logger.error(f"Error in [generate_text_stateless]: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {str(e)}"
            )

    async def gen_text(
        self,
        session_id: str,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate text using the configured LLM with session context
        
        Args:
            session_id: Session ID for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Returns:
            str: Generated text
        """
        try:
            # Get session without redundant validation
            session = await self.session_store.get_session(session_id)
            
            # Get model ID from session or config
            model_id = session.metadata.model_id or self.default_llm_config.model_id
            llm = self._get_llm_provider(model_id)
            
            # Debug input content
            logger.debug(f"Content received for session {session_id}: {content}")
            
            # Create message with multimodal content support
            message = self._prepare_message(content)

            # Generate response
            response = await llm.generate_content(
                messages=[message],
                system_prompt=session.context.get('system_prompt', ''),
                **(option_params or {})
            )

            if response.content:
                # Add interactions to session
                session.add_interaction({
                    "role": "user",
                    "content": content
                })
                
                session.add_interaction({
                    "role": "assistant",
                    "content": response.content,
                    "metadata": response.metadata if hasattr(response, 'metadata') else None
                })
                
                # Update session
                await self.session_store.update_session(session, session.user_id)

                return response.content.get('text')            
            else:
                raise ValueError("Empty response from LLM")                

        except Exception as e:
            logger.error(f"Error in [generate_text]: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {str(e)}"
            )

    async def gen_text_stream(
        self,
        session_id: str,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> AsyncIterator[str]:
        """Generate text with streaming response and session context
        
        Args:
            session_id: Session ID for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Yields:
            str: Generated text chunks in streaming fashion
        """
        try:
            # Get session
            session = await self.session_store.get_session(session_id)
            
            # Get model ID from session or config
            model_id = session.metadata.model_id or self.default_llm_config.model_id
            llm = self._get_llm_provider(model_id)
            
            # Debug input content
            logger.debug(f"Content received for session {session_id}: {content}")
            
            # Add user message to session
            session.add_interaction({
                "role": "user",
                "content": content
            })
            
            # Create message for generation
            message = self._prepare_message(content)
            
            # Stream response
            accumulated_text = ''
            chunk_metadata = None
            
            try:
                async for chunk in llm.generate_stream(
                    messages=[message],
                    system_prompt=session.context.get('system_prompt', ''),
                    **(option_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"Unexpected chunk type: {type(chunk)}")
                        continue

                    # Extract metadata if present
                    if 'metadata' in chunk:
                        chunk_metadata = chunk['metadata']
                    
                    # Try to get text content, even if empty
                    if chunk_text := chunk.get('content', {}).get('text'):
                        accumulated_text += chunk_text
                        yield chunk_text

                # Add assistant message to session after streaming completes
                session.add_interaction({
                    "role": "assistant",
                    "content": {"text": accumulated_text},
                    "metadata": chunk_metadata
                })
                await self.session_store.update_session(session, session.user_id)
                    
            except Exception as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in [generate_text_stream]: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
