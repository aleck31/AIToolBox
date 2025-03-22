from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger
from core.session import Session, SessionStore
from core.module_config import module_config
from llm.model_manager import model_manager
from llm.api_providers import LLMConfig, LLMAPIProvider, LLMProviderError


class BaseService:
    """Base service with common functionality, independent of model"""
        
    def __init__(
        self,
        enabled_tools: Optional[List[str]] = None,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize base service with optional tools and caching
        
        Args:
            enabled_tools: Optional list of tool module names to enable
            cache_ttl: Time in seconds to keep sessions in cache (default 10 min)
        """
        self.session_store = SessionStore.get_instance()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self._session_cache: Dict[str, tuple[Session, float]] = {}
        self.enabled_tools = enabled_tools or []
        self.cache_ttl = cache_ttl

    def _get_llm_provider(self, model_id: str, inference_params: Optional[Dict] = None) -> LLMAPIProvider:
        """Get or create LLM API provider for given model
        
        Args:
            model_id: ID of the model to get provider for
            inference_params: Optional inference parameters to override defaults
            
        Returns:
            LLMAPIProvider: Cached or newly created provider
        """
        try:
            # Use cached provider if available and no custom params
            if not inference_params and model_id in self._llm_providers:
                logger.debug(f"[BaseService] Using cached provider for model {model_id}")
                return self._llm_providers[model_id]

            # Get model info
            model = model_manager.get_model_by_id(model_id)
            if not model:
                raise ValueError(f"Model not found: {model_id}")
            logger.debug(f"[BaseService] Found model: {model.name} ({model.api_provider})")

            # Create config with model info and optional params
            config = LLMConfig(
                api_provider=model.api_provider,
                model_id=model_id,
                **(inference_params or {})
            )
            logger.debug(f"[BaseService] Created LLM config for {model_id} with params: {inference_params}")

            # Create provider with enabled tools
            provider = LLMAPIProvider.create(config, tools=self.enabled_tools)
            logger.debug(f"[BaseService] Created provider {provider.__class__.__name__} with tools: {self.enabled_tools}")

            # Cache provider if using default params
            if not inference_params:
                self._llm_providers[model_id] = provider

            return provider

        except LLMProviderError as e:
            logger.error(f"[BaseService] Failed to get LLM provider for {model_id}: {e.error_code}")
            raise

    async def get_or_create_session(
        self,
        user_name: str,
        module_name: str,
        session_name: Optional[str] = None,
        bypass_cache: bool = False
    ) -> Session:
        """Get latest existing session or create new one
        
        Args:
            user_name: User to get/create session for
            module_name: Module name for the session
            session_name: Optional custom session name
            bypass_cache: Whether to bypass cache lookup
            
        Returns:
            Session: Active session for user/module
        """
        cache_key = f"{user_name}:{module_name}"
        
        try:
            # Try cache first unless bypassed
            if not bypass_cache:
                if cached_session := self._session_cache.get(cache_key):
                    session, expiry = cached_session
                    if datetime.now().timestamp() < expiry:
                        return session
                    # Clear expired cache entry
                    del self._session_cache[cache_key]
            
            # Get most recent session from store
            if sessions := await self.session_store.list_sessions(
                user_name=user_name,
                module_name=module_name
            ):
                session = sessions[0]  # Most recent session
            else:
                # Create new session
                name = session_name or f"{module_name.title()} session for {user_name}"
                session = await self.session_store.create_session(
                    user_name=user_name,
                    module_name=module_name,
                    session_name=name
                )
            
            # Update cache with new session
            self._session_cache[cache_key] = (
                session,
                datetime.now().timestamp() + self.cache_ttl
            )
            
            return session

        except Exception as e:
            logger.error(f"[BaseService] Failed to get/create session for {user_name}: {str(e)}")
            raise

    async def get_session_model(self, session: Session) -> Optional[str]:
        """Get model ID from session or module defaults
        
        Args:
            session: Session to get model for
            
        Returns:
            str: Model ID if found, None otherwise
            
        Notes:
            - Checks session metadata first
            - Falls back to module config defaults
            - Updates session if default model found
        """
        try:
            # Return existing model_id if set
            if model_id := session.metadata.model_id:
                return model_id

            # Falls back to module config default model
            if model_id := module_config.get_default_model(session.metadata.module_name):
                logger.debug(f"[BaseService] Falls back to module default model: {model_id}")
                return model_id

            logger.warning(f"[BaseService] No model ID found for {session.metadata.module_name}")
            return None

        except Exception as e:
            logger.error(f"[BaseService] Failed to get model for session {session.session_id}: {str(e)}")
            return None

    async def update_session_model(self, session: Session, model_id: str) -> None:
        """Update model ID in session metadata
        
        Args:
            session: Session to update
            model_id: New model ID to set
        """
        try:
            if session.metadata.model_id != model_id:
                session.metadata.model_id = model_id
                await self.session_store.save_session(session)
                logger.debug(f"[BaseService] Updated model to {model_id} in session {session.session_id}")
        except Exception as e:
            logger.error(f"[BaseService] Failed to update model_id in session: {str(e)}")
            raise

    async def load_session_history(
        self,
        session: Session,
        max_number: int = 24
    ) -> List[Dict[str, str]]:
        """Load chat history from session
        
        Args:
            session: Session to load history from
            max_number: Maximum number of messages to return
            
        Returns:
            List[Dict]: List of message dictionaries
        """
        try:
            if not session.history:
                return []
                
            messages = []
            # Process only the most recent messages up to max_number
            for msg in session.history[-max_number:]:
                content = msg['content']
                
                if isinstance(content, dict):
                    # Handle text content
                    if text := content.get('text'):
                        messages.append({
                            "role": msg['role'],
                            "content": text
                        })
                    # Handle file content separately
                    if files := content.get('files'):
                        messages.append({
                            "role": msg['role'],
                            "content": files
                        })
                else:
                    # Handle legacy string content
                    messages.append({
                        "role": msg['role'],
                        "content": content
                    })
                    
            return messages
            
        except Exception as e:
            logger.error(f"[BaseService] Failed to load history from session {session.session_id}: {str(e)}")
            return []
