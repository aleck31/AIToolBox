from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session.models import Session, SessionError
from core.session import SessionManager
from llm.bedrock_provider import BedrockProvider
from llm.gemini_provider import GeminiProvider
from llm.model_manager import model_manager
from llm import LLMConfig, Message, LLMAPIProvider


# TobeFix: Implement GenService functions according to module requirements
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
        self.session_manager = SessionManager()
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

    async def get_gen_session(
        self,
        user_id: str,
        module_name: str = 'text',
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
                    session = await self.session_manager.get_session(session_id, user_id)
                    return session
                except SessionError:
                    # Session expired or invalid, remove from tracking
                    if user_id in self._active_sessions:
                        self._active_sessions[user_id].pop(module_name, None)

            # Create new session
            # model_id = module_config.get_default_model(module_name)
            session_name = session_name or f"{module_name.title()} Session"
            
            # Create session through session manager with standardized format
            session = await self.session_manager.create_session(
                user_id=user_id,
                module_name=module_name,
                session_name=session_name
                # initial_context={}
            )
            
            # Track new session
            if user_id not in self._active_sessions:
                self._active_sessions[user_id] = {}
            self._active_sessions[user_id][module_name] = session.session_id
            
            logger.info(f"Created new chat session {session.session_id} for user {user_id}")
            return session

        except SessionError as e:
            logger.error(f"Error in get_chat_session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    async def get_gen_session_by_id(
        self,
        session_id: str,
        user_id: str
    ) -> Session:
        """Get an existing chat session"""
        try:
            session = await self.session_manager.get_session(
                session_id=session_id,
                user_id=user_id
            )
            return session
            
        except SessionError as e:
            logger.error(f"Failed to get chat session: {str(e)}")
            raise HTTPException(
                status_code=404 if "not found" in str(e) else 500,
                detail=str(e)
            )

    async def generate_content():
        pass

    async def generate_stream(
        self,
        session_id: str,
        user_id: str,
        content: Dict[str, str]
    ) -> AsyncIterator[str]:
        """Send a message in a chat session and stream the response"""
        session = None
        try:
            # Get session
            session = await self.get_gen_session_by_id(session_id, user_id)
            
            # Create message
            user_message = Message(
                role="user",
                content=content
            )
            
            # Get model ID from session
            model_id = session.metadata.model_id
            llm = self._get_llm_provider(model_id)
            
            # Add user message to session
            session.add_interaction({
                "role": "user",
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            
            # Stream response
            full_response = ""
            stream_metadata = None
            
            try:
                # Get the stream from LLM
                async for chunk in llm.generate_stream(
                    messages=[user_message],
                    system_prompt=session.metadata.system_prompt
                ):
                    # Handle metadata events from the stream
                    if isinstance(chunk, dict) and chunk.get('type') == 'metadata':
                        stream_metadata = chunk['data']
                        continue
                    
                    # Handle text chunks
                    full_response += chunk
                    yield chunk
                
                # Add assistant message with metadata from stream
                interaction_data = {
                    "role": "assistant",
                    "content": {"text": full_response},
                    "timestamp": datetime.now().isoformat()
                }
                
                # Add metadata if available from stream
                if stream_metadata:
                    interaction_data["metadata"] = {
                        "usage": stream_metadata.get('usage', {}),
                        "metrics": stream_metadata.get('metrics', {}),
                        "stop_reason": stream_metadata.get('stop_reason'),
                        "trace": stream_metadata.get('trace', {})
                    }
                
                session.add_interaction(interaction_data)
                
                # Single update to DynamoDB after streaming
                await self.session_manager.update_session(session, user_id)
                    
            except Exception as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
            

    async def analyze_image():
        pass