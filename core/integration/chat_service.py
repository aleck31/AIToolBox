from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session, SessionStore
from llm.model_manager import model_manager
from llm.api_providers.base import LLMConfig, Message, LLMAPIProvider


class ChatService:
    """Main service for handling chat interactions"""
    
    def __init__(
        self,
        model_config: LLMConfig,
        enabled_tools: Optional[List[str]] = None,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize chat service with model configuration
        
        Args:
            model_config: LLM configuration containing model ID and parameters
            enabled_tools: Optional list of tool module names to enable
            cache_ttl: Time in seconds to keep sessions in cache (default 5 min)
        """
        self.session_store = SessionStore.get_instance()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self._session_cache: Dict[str, tuple[Session, float]] = {}  # (session, expiry)
        self.enabled_tools = enabled_tools or []
        self.cache_ttl = cache_ttl
        
        # Validate model exists and config matches
        model = model_manager.get_model_by_id(model_config.model_id)
        if not model:
            raise ValueError(f"Model not found: {model_config.model_id}")
        
        self.default_model_config = model_config

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
            max_tokens=self.default_model_config.max_tokens,
            temperature=self.default_model_config.temperature,
            top_p=self.default_model_config.top_p,
            stop_sequences=self.default_model_config.stop_sequences
        )
        
        # Create provider using factory method with enabled tools
        provider = LLMAPIProvider.create(config, tools=self.enabled_tools)
        self._llm_providers[model_id] = provider
        return provider

    def _prepare_chat_message(self, role: str, content: Dict, context: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Message:
        """Create standardized interaction entry
        
        Args:
            role: Message role (user/assistant/system)
            content: Raw content dict with text and/or files
            metadata: Optional metadata dict
            
        Returns:
            Interaction dict with standardized format
        """
        # message_meta = {"timestamp": datetime.now().isoformat()}
        # if metadata:
        #     message_meta.update(metadata)
        chat_message = Message(
            role = role,
            content=content,
            context=context if context else None,
            metadata=metadata if metadata else None,
        )
        return chat_message

    def _get_cache_key(self, user_id: str, module_name: str) -> str:
        """Generate cache key for session"""
        return f"{user_id}:{module_name}"

    def _is_cache_valid(self, cache_entry: tuple[Session, float]) -> bool:
        """Check if cached session is still valid"""
        session, expiry = cache_entry
        return datetime.now().timestamp() < expiry

    def _update_cache(self, user_id: str, module_name: str, session: Session) -> None:
        """Update session cache with new expiry"""
        cache_key = self._get_cache_key(user_id, module_name)
        expiry = datetime.now().timestamp() + self.cache_ttl
        self._session_cache[cache_key] = (session, expiry)
        logger.debug(f"Updated cache for session {session.session_id} (expires: {expiry})")

    def _cleanup_cache(self) -> None:
        """Remove expired sessions from cache"""
        now = datetime.now().timestamp()
        expired = [k for k, (_, exp) in self._session_cache.items() if exp < now]
        for key in expired:
            del self._session_cache[key]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired sessions from cache")

    async def get_or_create_session(
        self,
        user_id: str,
        module_name: str,
        session_name: Optional[str] = None
    ) -> Session:
        """Get existing active session or create new one
        
        Args:
            user_id: User identifier
            module_name: Module requesting the session
            session_name: Optional custom session name
            
        Returns:
            Active session for the user/module
            
        Note:
            First checks in-memory cache, then falls back to DynamoDB query
            Cache entries expire after TTL to prevent stale data
        """
        try:
            # Clean expired cache entries
            self._cleanup_cache()
            
            # Check cache first
            cache_key = self._get_cache_key(user_id, module_name)
            if cache_key in self._session_cache:
                cached = self._session_cache[cache_key]
                if self._is_cache_valid(cached):
                    session = cached[0]
                    logger.debug(
                        f"Cache hit: Found session {session.session_id} "
                        f"for user {user_id} in cache"
                    )
                    return session
                else:
                    # Remove expired entry
                    del self._session_cache[cache_key]
            
            # Cache miss - query database
            active_sessions = await self.session_store.list_sessions(
                user_id=user_id,
                module_name=module_name
            )
            
            if active_sessions:
                session = active_sessions[0]
                logger.debug(
                    f"Cache miss: Found existing {module_name} session {session.session_id} "
                    f"for user {user_id} (created: {session.created_time}"
                )
                # Update cache
                self._update_cache(user_id, module_name, session)
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
                f"for user {user_id} (created: {session.created_time}"
            )
            
            # Cache new session
            self._update_cache(user_id, module_name, session)
            return session

        except HTTPException as e:
            logger.error(f"Error in [get_or_create_session]: {str(e)}")
            raise e

    async def clear_chat_session(
        self,
        session_id: str,
        user_id: str
    ) -> Session:
        """Clear chat history while preserving session"""
        try:
            session = await self.session_store.get_session(session_id, user_id)
            # Clear history while preserving metadata and context
            session.history = []
            # Update session in store
            await self.session_store.update_session(session, user_id)
            return session
            
        except HTTPException as e:
            logger.error(f"Failed to clear chat session: {str(e)}")
            raise e

    async def streaming_reply(
        self,
        session_id: str,
        ui_input: Dict,
        ui_history: Optional[List[Dict]] = None,
        style_params: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        """Process user message and stream assistant's response
        
        Args:
            session_id: Active chat session ID
            ui_input: Dict with text and/or files
            ui_history: Current UI chat history state
            style_params: LLM generation parameters
            
        Yields:
            Message chunks for handler
        """
        try:
            # Get session (already validated by get_or_create_session)
            session = await self.session_store.get_session(session_id)

            # Get history before adding new message
            history = ui_history or session.history
            history_messages = []
            for msg in history:
                history_messages.append(
                    self._prepare_chat_message(
                        role=msg["role"], 
                        content=msg["content"]
                        # context={"local_time": msg["timestamp"]}  # history messages no need context 
                    )
                )

            # Convert new message to chat Message format
            user_message = self._prepare_chat_message(
                role="user",
                content=ui_input,
                # Add custom context that you want LLM to know
                context={
                    'local_time': datetime.now().astimezone().isoformat(),
                    'user_name': session.user_id
                }
            )
            logger.debug(f"New Message send to LLM Provider: {user_message}")

            # Add new message to session after processing history
            session.add_interaction(user_message.to_dict())
            
            # Get LLM provider
            llm = self._get_llm_provider(session.metadata.model_id)
            
            # Track complete response for session
            accumulated_text = []
            resp_metadata = {}
            assistant_message = None
            
            try:
                # Stream from LLM
                async for chunk in llm.multi_turn_generate(
                    message=user_message,
                    history=history_messages,
                    system_prompt=session.context.get('system_prompt'),
                    **(style_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"Unexpected chunk type: {type(chunk)}")
                        continue

                    # Handle metadata updates
                    if chunk_metadata := chunk.get('metadata'):
                        resp_metadata.update(chunk_metadata)
                    
                    # Handle content chunks
                    if chunk_text := chunk.get('content', {}).get('text'):
                        accumulated_text.append(chunk_text)
                        yield chunk_text
                
                # Add complete response to session
                if accumulated_text:
                    assistant_message = self._prepare_chat_message(
                        role="assistant",
                        content={"text": ''.join(accumulated_text)},
                        metadata=resp_metadata
                    )
                    logger.debug(f"Message replied by LLM Provider: {assistant_message}")
                    
                    # Add assistant message to session
                    session.add_interaction(assistant_message.to_dict())

                # Persist interaction history to session store
                await self.session_store.update_session(session, session.user_id)
                    
            except Exception as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in [streaming_reply]: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
