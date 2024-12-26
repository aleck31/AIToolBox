from fastapi import HTTPException
from datetime import datetime
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session, SessionStore
from llm.model_manager import model_manager
from llm import LLMConfig, Message, LLMAPIProvider


class ChatService:
    """Main service for handling chat interactions"""
    
    def __init__(
        self,
        model_config: LLMConfig
    ):
        """Initialize chat service with model configuration
        
        Args:
            model_config: LLM configuration containing model ID and parameters
        """
        self.session_store = SessionStore()
        self._llm_providers: Dict[str, LLMAPIProvider] = {}
        self._active_sessions: Dict[str, Dict[str, str]] = {}
        
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
        
        # Create provider using factory method
        provider = LLMAPIProvider.create(config)
        self._llm_providers[model_id] = provider
        return provider

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
            
            # Create session through session manager with standardized format
            session = await self.session_store.create_session(
                user_id=user_id,
                module_name=module_name,
                session_name=session_name
            )
            
            # Track new session
            if user_id not in self._active_sessions:
                self._active_sessions[user_id] = {}
            self._active_sessions[user_id][module_name] = session.session_id
            
            logger.info(f"Created new chat session {session.session_id} for user {user_id}")
            return session

        except HTTPException as e:
            logger.error(f"Error in get_or_create_session: {str(e)}")
            raise e

    async def list_chat_sessions(
        self,
        user_id: str,
        tags: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Session]:
        """List chat sessions for a user"""
        try:
            return await self.session_store.list_sessions(
                user_id=user_id,
                module_name='chatbot',
                tags=tags,
                start_date=start_date,
                end_date=end_date
            )
        except HTTPException as e:
            logger.error(f"Failed to list chat sessions: {str(e)}")
            raise e

    async def clear_chat_session(
        self,
        session_id: str,
        user_id: str
    ) -> Session:
        """Clear chat history while preserving session"""
        try:
            # Get existing session
            session = await self.session_store.get_session(session_id, user_id)
            
            # Clear history while preserving metadata and context
            session.history = []
            
            # Update session in store
            await self.session_store.update_session(session, user_id)
            return session
            
        except HTTPException as e:
            logger.error(f"Failed to clear chat session: {str(e)}")
            raise e

    async def delete_chat_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """Delete a chat session"""
        try:
            # Remove from active sessions if present
            user_sessions = self._active_sessions.get(user_id, {})
            for module_name, active_session_id in list(user_sessions.items()):
                if active_session_id == session_id:
                    user_sessions.pop(module_name)
                    break
            
            return await self.session_store.delete_session(
                session_id=session_id,
                user_id=user_id
            )
        except HTTPException as e:
            logger.error(f"Failed to delete chat session: {str(e)}")
            raise e

    async def sync_history(
        self,
        session: Session,
        ui_history: List[Dict[str, str]]
    ) -> None:
        """Sync session history with UI history state
        
        Args:
            session: Session to update
            ui_history: Current history state from UI
        """
        # Convert UI history to session format
        session.history = [
            {
                "role": msg["role"],
                "content": msg["content"] if isinstance(msg["content"], dict) else {"text": msg["content"]},
                "timestamp": msg.get("timestamp", datetime.now().isoformat())
            }
            for msg in ui_history
        ]
        # Update session in store
        await self.session_store.update_session(session, session.user_id)

    async def send_message(
        self,
        session_id: str,
        content: Dict[str, str],
        ui_history: Optional[List[Dict[str, str]]] = None,
        option_params: Optional[Dict[str, float]] = None
    ) -> AsyncIterator[str]:
        """Send a message in a chat session and stream the response
        
        Args:
            session_id: ID of the chat session
            content: Message content with text and optional files
            ui_history: Optional UI chat history for syncing
            option_params: Optional LLM generation parameters
            
        Yields:
            Generated response chunks for streaming
        """
        try:
            # Get session without redundant validation since it was already validated
            # when obtained through get_or_create_session
            session = await self.session_store.get_session(session_id)
            
            # Sync with UI history if provided
            if ui_history is not None:
                await self.sync_history(session, ui_history)

            logger.debug(f"Content from handler: {content}")

            # Get model ID from session
            model_id = session.metadata.model_id
            llm = self._get_llm_provider(model_id)
            
            # Add user message to session
            session.add_interaction({
                "role": "user",
                "content": content,
                "timestamp": datetime.now().astimezone().isoformat()  # timestamp with tzinfo
            })
            
            # Convert session history to messages
            messages = []
            for interaction in session.history:
                messages.append(Message(
                    role=interaction["role"],
                    content=interaction["content"],
                    # Provides context for when the message was sent
                    context={"local_time": interaction["timestamp"]}
                ))
            
            # Stream response
            full_response = ""
            stream_metadata = None
            
            try:
                # Get the stream from LLM with conversation history and style parameters
                async for chunk in llm.generate_stream(
                    messages=messages,
                    system_prompt=session.context['system_prompt'],
                    **(option_params or {})  # Unpack inference params if provided
                ):
                    # All chunks should be dictionaries with type indicators
                    if not isinstance(chunk, dict):
                        logger.warning(f"Unexpected chunk type: {type(chunk)}")
                        continue
                        
                    if 'metadata' in chunk:
                        # Store metadata for later use
                        stream_metadata = chunk['metadata']
                    elif 'text' in chunk:
                        # Process text chunk
                        text = chunk['text']
                        full_response += text
                        # Yield accumulated response for Gradio UI
                        yield full_response
                    else:
                        logger.warning(f"Unknown chunk format: {chunk}")
                
                # Add assistant message to session after streaming completes
                if full_response:  # Only add if we got a response
                    # Add assistant message with timezone-aware timestamp
                    current_time = datetime.now().astimezone()
                    interaction_data = {
                        "role": "assistant",
                        "content": {"text": full_response},
                        "timestamp": current_time.isoformat()
                    }
                    
                    # Add metadata if available from stream
                    if stream_metadata:
                        interaction_data["metadata"] = {
                            "usage": stream_metadata.get('usage', {}),
                            "metrics": stream_metadata.get('metrics', {}),
                            "stop_reason": stream_metadata.get('stop_reason'),
                            "trace": stream_metadata.get('trace', {})
                        }
                    
                    # Add interaction and update session
                    session.add_interaction(interaction_data)
                    await self.session_store.update_session(session, session.user_id)
                    
            except Exception as e:
                logger.error(f"LLM error in session {session_id}: {str(e)}")
                yield "I apologize, but I encountered an error while generating the response."
                
        except Exception as e:
            logger.error(f"Error in send_message: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
