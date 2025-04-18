from typing import Dict, List, Optional
from datetime import datetime
from core.logger import logger
from core.session import Session, SessionStore
from core.module_config import module_config
from llm.model_manager import model_manager
from llm import LLMParameters, GenImageParameters
from llm.api_providers import LLMAPIProvider, LLMProviderError, create_provider


class BaseService:
    """Base service with common functionality"""

    def __init__(
        self,
        module_name: str,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize base service without LLM params

        Args:
            module_name: Name of the module using this service
            cache_ttl: Time in seconds to keep sessions in cache (default 10 min)
        """
        self.module_name = module_name
        self.session_store = SessionStore.get_instance()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self._session_cache: Dict[str, tuple[Session, float]] = {}
        self.cache_ttl = cache_ttl
        self.model_id = None

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

    async def get_session_model(self, session: Session) -> str:
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
            if self.model_id:
                logger.debug(f"[BaseService] Get cached model id: {self.model_id}")
                return self.model_id
            elif model_id := session.metadata.model_id:
                logger.debug(f"[BaseService] Get session model id: {model_id}")
                self.model_id = model_id
                return self.model_id
            # Falls back to module config default model
            elif model_id := module_config.get_default_model(session.metadata.module_name):
                self.model_id = model_id
                logger.debug(f"[BaseService] Falls back to default model: {model_id}")
                return self.model_id
            else:
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
            if self.model_id != model_id:
                self.model_id = model_id
                session.metadata.model_id = model_id
                await self.session_store.save_session(session)
                logger.debug(f"[BaseService] Updated model to {model_id} in session {session.session_id}")
        except Exception as e:
            logger.error(f"[BaseService] Failed to update session model: {str(e)}")
            raise

    def _get_llm_provider(self, model_id: Optional[str], llm_params: Optional[LLMParameters] = None) -> LLMAPIProvider:
        """Get or create LLM API provider for given model
        
        Args:
            model_id: ID of the model to get provider for
            llm_params: Optional LLM inference parameters to override defaults
            
        Returns:
            LLMAPIProvider: Cached or newly created provider
            
        Note:
            If no llm_params provided, uses module's default inference parameters
        """
        try:
            # Use cached provider if available and no custom params
            if model_id in self._llm_providers and not llm_params:
                logger.debug(f"[BaseService] Using cached provider for model {model_id}")
                return self._llm_providers[model_id]

            # Get model info
            if model := model_manager.get_model_by_id(model_id):
                logger.debug(f"[BaseService] Found model: {model.name} ({model.api_provider})")
            else:
                raise ValueError(f"Model not found: {model_id}")

            # Get module's default tools and params if not provided
            if not llm_params:
                params = module_config.get_inference_params(self.module_name) or {}
                
                # Check if this is an image generation model
                if model.category == 'image':
                    # Use GenImageParameters for image generation models
                    # Ensure proper type conversion for numeric parameters
                    if 'height' in params:
                        params['height'] = int(params['height'])
                    if 'width' in params:
                        params['width'] = int(params['width'])
                    if 'img_number' in params:
                        params['img_number'] = int(params['img_number'])
                    if 'cfg_scale' in params:
                        params['cfg_scale'] = float(params['cfg_scale'])
                    
                    llm_params = GenImageParameters(**(params or {}))
                    logger.debug(f"[BaseService] Using GenImageParameters for model {model_id}")
                else:
                    # Use LLMParameters for text generation models
                    # Ensure proper type conversion for numeric parameters
                    if 'max_tokens' in params:
                        params['max_tokens'] = int(params['max_tokens'])
                    if 'temperature' in params:
                        params['temperature'] = float(params['temperature'])
                    if 'top_p' in params:
                        params['top_p'] = float(params['top_p'])
                    if 'top_k' in params:
                        params['top_k'] = int(params['top_k'])
                    
                    llm_params = LLMParameters(**(params or {}))

            enabled_tools = module_config.get_enabled_tools(self.module_name)

            # Create provider with module configuration
            provider = create_provider(
                model.api_provider,
                model_id,
                llm_params,
                enabled_tools
            )

            # Cache provider if no custom params
            if not llm_params:
                self._llm_providers[model_id] = provider

            return provider

        except LLMProviderError as e:
            logger.error(f"[BaseService] Provider error for {model_id}: {e.error_code}")
            raise
        except Exception as e:
            logger.error(f"[BaseService] Failed to get provider for {model_id}: {str(e)}")
            raise

    async def load_session_history(
        self,
        session: Session,
        max_messages: int = 24
    ) -> List[Dict[str, str]]:
        """Load formatted chat history from session"""
        try:
            if not session.history:
                return []
                
            messages = []
            # Process only the most recent messages up to max_number
            for msg in session.history[-max_messages:]:
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
            return []  # Return empty history on error
