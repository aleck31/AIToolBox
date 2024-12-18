from typing import Dict, List, Optional, AsyncIterator
from datetime import datetime
from fastapi import HTTPException

from llm import (
    BaseLLMProvider,
    LLMConfig,
    Message,
    ModelProvider,
    LLMException
)
from llm.bedrock_provider import BedrockProvider
from llm.gemini_provider import GeminiProvider
from ..session import ModuleSession, ModuleSessionManager, SessionException
from .module_config import module_config
from core.logger import logger

class ChatService:
    """Main service for handling chat interactions"""
    
    def __init__(
        self,
        session_manager: ModuleSessionManager,
        default_model_config: LLMConfig
    ):
        self.session_manager = session_manager
        self.default_model_config = default_model_config
        self._llm_providers: Dict[str, BaseLLMProvider] = {}

    def _get_llm_provider(self, model_id: str) -> BaseLLMProvider:
        """Get or create LLM provider for given model"""
        if model_id not in self._llm_providers:
            # Create provider based on model ID prefix
            if model_id.startswith("anthropic."):
                config = LLMConfig(
                    provider=ModelProvider.BEDROCK,
                    model_id=model_id,
                    max_tokens=self.default_model_config.max_tokens,
                    temperature=self.default_model_config.temperature,
                    top_p=self.default_model_config.top_p,
                    stop_sequences=self.default_model_config.stop_sequences
                )
                self._llm_providers[model_id] = BedrockProvider(config)
            elif model_id.startswith("gemini-"):
                config = LLMConfig(
                    provider=ModelProvider.GEMINI,
                    model_id=model_id,
                    max_tokens=self.default_model_config.max_tokens,
                    temperature=self.default_model_config.temperature,
                    top_p=self.default_model_config.top_p,
                    stop_sequences=self.default_model_config.stop_sequences
                )
                self._llm_providers[model_id] = GeminiProvider(config)
            else:
                raise ValueError(f"Unsupported model ID: {model_id}")
                
        return self._llm_providers[model_id]

    async def create_chat_session(
        self,
        user_id: str,
        session_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
        module_name: str = 'chatbot'  # Default to chatbot module
    ) -> ModuleSession:
        """Create a new chat session"""
        try:
            # Get model ID from module config
            model_id = module_config.get_default_model(module_name)
            
            # Create initial context with system prompt if provided
            initial_context = {
                'system_prompt': system_prompt or module_config.get_system_prompt(module_name),
                'chat_metadata': {
                    'start_time': datetime.utcnow().isoformat(),
                    'model_id': model_id
                }
            }
            
            # Create session
            session = await self.session_manager.create_session(
                user_id=user_id,
                module_name=module_name,
                model_id=model_id,
                session_name=session_name,
                initial_context=initial_context
            )
            
            logger.info(f"Created new chat session {session.session_id} for user {user_id}")
            return session
            
        except Exception as e:
            logger.error(f"Failed to create chat session: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    async def get_chat_session(
        self,
        session_id: str,
        user_id: str
    ) -> ModuleSession:
        """Get an existing chat session"""
        try:
            return await self.session_manager.get_session(
                session_id=session_id,
                user_id=user_id
            )
        except SessionException as e:
            logger.error(f"Failed to get chat session: {str(e)}")
            raise HTTPException(
                status_code=404 if "not found" in str(e) else 500,
                detail=str(e)
            )

    async def send_message(
        self,
        session_id: str,
        user_id: str,
        content: Dict[str, str]
    ) -> AsyncIterator[str]:
        """Send a message in a chat session and stream the response"""
        session = None
        try:
            # Get session
            session = await self.get_chat_session(session_id, user_id)
            
            # Create message
            user_message = Message(
                role="user",
                content=content
            )
            
            # Get model ID from session
            model_id = session.metadata.model_id
            llm = self._get_llm_provider(model_id)
            
            # Add user message to history
            session.add_interaction({
                "role": "user",
                "content": content
            })
            
            # Update session with user message
            await self.session_manager.update_session(session, user_id)
            
            # Stream response
            response_chunks = []
            try:
                async for chunk in llm.generate_stream(
                    messages=[user_message],
                    system_prompt=session.context.get('system_prompt')
                ):
                    response_chunks.append(chunk)
                    yield chunk
                    
                # After streaming completes, update session with full response
                full_response = "".join(response_chunks)
                session.add_interaction({
                    "role": "assistant",
                    "content": full_response
                })
                await self.session_manager.update_session(session, user_id)
                    
            except LLMException as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."

    async def list_chat_sessions(
        self,
        user_id: str,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[ModuleSession]:
        """List chat sessions for a user"""
        try:
            return await self.session_manager.list_sessions(
                user_id=user_id,
                module_name='chatbot',
                tags=tags,
                start_date=start_date,
                end_date=end_date
            )
        except SessionException as e:
            logger.error(f"Failed to list chat sessions: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=str(e)
            )

    async def delete_chat_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Delete a chat session"""
        try:
            return await self.session_manager.delete_session(
                session_id=session_id,
                user_id=user_id
            )
        except SessionException as e:
            logger.error(f"Failed to delete chat session: {str(e)}")
            raise HTTPException(
                status_code=404 if "not found" in str(e) else 500,
                detail=str(e)
            )
