from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session, SessionStore
from llm.bedrock_provider import BedrockProvider
from llm.gemini_provider import GeminiProvider
from llm.model_manager import model_manager
from llm import LLMConfig, Message, LLMAPIProvider


#  GenService will be used by multiple modules, including text, vison, summary, coding, oneshot
class GenService:
    """General content generation service"""
    
    def __init__(
        self,
        llm_config: LLMConfig
    ):
        """Initialize text service with model configuration
        
        Args:
            llm_config: LLM configuration containing model ID and parameters
        """
        self.session_store = SessionStore()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self._active_sessions: Dict[str, Dict[str, str]] = {}
        
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
        
        # Create and cache provider
        if config.api_provider.upper() == 'BEDROCK':
            provider = BedrockProvider(config)
        elif config.api_provider.upper() == 'GEMINI':
            provider = GeminiProvider(config)
        else:
            raise ValueError(f"Unsupported API provider: {config.api_provider}")
            
        self._llm_providers[model_id] = provider
        return provider

    # Question: After this modification, has the get_or_create_session method become useless?
    async def get_or_create_session(
        self,
        user_id: str,
        module_name: str,
        session_name: Optional[str] = None
    ) -> Session:
        """Get existing active session or create new one"""
        try:
            # Check for existing active session
            user_sessions = self._active_sessions.get(user_id, {})
            if module_name in user_sessions:
                session_id = user_sessions[module_name]
                try:
                    # Verify session is still valid
                    session = await self.session_store.get_session(session_id, user_id)
                    return session
                except HTTPException:
                    # Session expired or invalid, remove from tracking
                    if user_id in self._active_sessions:
                        self._active_sessions[user_id].pop(module_name, None)

            # Create and cache session
            session_name = session_name or f"{module_name.title()} Session"
            
            # Create session through session store
            session = await self.session_store.create_session(
                user_id=user_id,
                module_name=module_name,
                session_name=session_name
            )
            
            # Track new session
            if user_id not in self._active_sessions:
                self._active_sessions[user_id] = {}
            self._active_sessions[user_id][module_name] = session.session_id
            
            logger.info(f"Created new session {session.session_id} for user {user_id}")
            return session

        except HTTPException as e:
            logger.error(f"Error in get_session: {str(e)}")
            raise e

    async def generate_stateless(
        self,
        content: Dict[str, str],
        system_prompt: Optional[str] = None,
        option_params: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate content using the configured LLM without session context
        
        Args:
            content: Dictionary containing text and optional files
            system_prompt: Optional system prompt for one-off generation
            option_params: Optional parameters for LLM generation
            
        Returns:
            str: Generated content
        """
        try:
            # Get model ID from config
            model_id = self.default_llm_config.model_id
            llm = self._get_llm_provider(model_id)
            
            # Debug input content
            logger.debug(f"Content received for stateless generation: {content}")
            
            # Create message with multimodal content support
            messages = [Message(
                role="user",
                content=content if isinstance(content, dict) else {"text": str(content)}
            )]

            # Generate response
            response = await llm.generate(
                messages=messages,
                system_prompt=system_prompt,
                **(option_params or {})
            )
            
            if not response:
                raise ValueError("Empty response from LLM")
            
            return response.content

        except Exception as e:
            logger.error(f"Error in generate_stateless: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {str(e)}"
            )

    async def generate_content(
        self,
        session_id: str,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate content using the configured LLM with session context
        
        Args:
            session_id: Session ID for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Returns:
            str: Generated content
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
            messages = [Message(
                role="user",
                content=content if isinstance(content, dict) else {"text": str(content)},
                # context={
                #     "current_time": datetime.now().isoformat()
                # }
            )]

            # Generate response
            response = await llm.generate(
                messages=messages,
                system_prompt=session.context.get('system_prompt', ''),
                **(option_params or {})
            )
            
            if not response:
                raise ValueError("Empty response from LLM")
            
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
            
            return response.content

        except Exception as e:
            logger.error(f"Error in generate_content: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Generation failed: {str(e)}"
            )

    async def generate_stream(
        self,
        session_id: str,
        content: Dict[str, str],
        option_params: Optional[Dict[str, float]] = None
    ) -> AsyncIterator[str]:
        """Generate content with streaming response and session context
        
        Args:
            session_id: Session ID for context management
            content: Dictionary containing text and optional files
            option_params: Optional parameters for LLM generation
            
        Yields:
            str: Generated content chunks in streaming fashion
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
            messages = [Message(
                role="user",
                content=content if isinstance(content, dict) else {"text": str(content)},
                # context={
                #     "current_time": datetime.now().isoformat()
                # }
            )]
            
            # Stream response
            full_response = ""
            stream_metadata = None
            
            try:
                async for chunk in llm.generate_stream(
                    messages=messages,
                    system_prompt=session.context.get('system_prompt', ''),
                    **(option_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"Unexpected chunk type: {type(chunk)}")
                        continue
                        
                    if 'metadata' in chunk:
                        stream_metadata = chunk['metadata']
                    elif 'text' in chunk:
                        text = chunk['text']
                        full_response += text
                        yield full_response
                    else:
                        logger.warning(f"Unknown chunk format: {chunk}")
                
                # Add assistant message to session after streaming completes
                if full_response:
                    session.add_interaction({
                        "role": "assistant",
                        "content": {"text": full_response},
                        "metadata": {
                            "usage": stream_metadata.get('usage', {}) if stream_metadata else {},
                            "metrics": stream_metadata.get('metrics', {}) if stream_metadata else {},
                            "stop_reason": stream_metadata.get('stop_reason') if stream_metadata else None,
                            "trace": stream_metadata.get('trace', {}) if stream_metadata else {}
                        }
                    })
                    await self.session_store.update_session(session, session.user_id)
                    
            except Exception as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in generate_stream: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
