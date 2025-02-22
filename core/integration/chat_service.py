from datetime import datetime
from itertools import groupby
from typing import Dict, List, Optional, AsyncIterator
from core.logger import logger
from core.session import Session
from llm.api_providers.base import Message, LLMConfig
from .base_service import BaseService


class ChatService(BaseService):
    """Chat service implementation with streaming capabilities"""
        
    def __init__(
        self,
        llm_config: LLMConfig,
        enabled_tools: Optional[List[str]] = None,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize ChatService with model configuration and tools"""
        super().__init__(enabled_tools=enabled_tools, cache_ttl=cache_ttl)  # Tools needed for function calling
        self.default_llm_config = llm_config

    def _prepare_chat_message(self, role: str, content: Dict, context: Optional[Dict] = None, metadata: Optional[Dict] = None) -> Message:
        """Create standardized interaction entry.
        
        Note:
            Creates a Message instance with role and content.
            Optional context and metadata can be provided for additional information.
        """            
        return Message(
            role=role,
            content=content,
            context=context,
            metadata=metadata
        )

    def _prepare_history(self, ui_history: List[Dict]) -> List[Message]:
        """Process history messages to chat Message format.
 
        Note:
            Messages are grouped by role and their content is combined with newlines.
            File content is converted to descriptive text using _get_file_desc.
        """
        if not ui_history:
            return []

        history_messages = []
        for role, group in groupby(ui_history, key=lambda x: x["role"]):
            texts = []
            for msg in group:
                content = msg.get("content")
                if not content:
                    continue
                    
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, (list, tuple)):
                    texts.extend(self._get_file_desc(f, role) for f in content)
                elif isinstance(content, dict):
                    if text := content.get("text"):
                        texts.append(text)
                    if files := content.get("files"):
                        texts.extend(self._get_file_desc(f, role) for f in files)
                
            if texts:
                history_messages.append(self._prepare_chat_message(
                    role=role,
                    content={"text": "\n".join(texts)}
                ))
                
        return history_messages

    # File type definitions
    _FILE_TYPES = {
        ('.png', '.jpg', '.jpeg', '.gif', '.webp'): ('image', '[User shared an image]', '[Generated an image in response]'),
        ('.mp4', '.mov', '.webm'): ('video', '[User shared a video]', '[Generated a video in response]'),
        ('.pdf', '.doc', '.docx'): ('document', '[User shared a document]', '[Generated a document in response]')
    }

    def _get_file_desc(self, file_path: str, role: str) -> str:
        """Get standardized file description based on type and role.
        
        Note:
            Returns appropriate description based on file extension and role.
            Empty string is returned for unrecognized file types.
        """
        file_path = file_path.lower()
        if matching_exts := next((exts for exts, _ in self._FILE_TYPES.items() if file_path.endswith(exts)), None):
            _, user_desc, assistant_desc = self._FILE_TYPES[matching_exts]
            return user_desc if role == 'user' else assistant_desc
        return ''

    async def streaming_reply(
        self,
        session: Session,
        ui_input: Dict,
        ui_history: Optional[List[Dict]] = [],
        style_params: Optional[Dict] = None
    ) -> AsyncIterator[Dict]:
        """Process user message and stream assistant's response
        
        Args:
            session: Active chat session
            ui_input: Dict with text and/or files
            ui_history: List of message dictionaries with role and content fields from UI state
            style_params: LLM generation parameters
            
        Yields:
            Message chunks for handler
        """
        try:
            # Convert new message to chat Message format
            user_message = self._prepare_chat_message(
                role="user",
                content=ui_input,
                # Add custom context here that you want LLM to know
                context={
                    'local_time': datetime.now().astimezone().isoformat(),
                    'user_name': session.user_name
                }
            )
            logger.debug(f"[ChatService] User message sent to LLM Provider: {user_message}")

            # Convert history messages to chat Message format
            history_messages = self._prepare_history(ui_history)
            logger.debug(f"[ChatService] History messages sent to LLM Provider: {history_messages}")

            # Get LLM provider with model fallback
            model_id = await self.get_session_model(session)
            llm = self._get_llm_provider(model_id)
            
            # Track response state
            accumulated_text = []
            accumulated_files = []
            response_metadata = {}
            
            try:
                # Stream from LLM
                async for chunk in llm.multi_turn_generate(
                    message=user_message,
                    history=history_messages,
                    system_prompt=session.context.get('system_prompt'),
                    **(style_params or {})
                ):
                    if not isinstance(chunk, dict):
                        logger.warning(f"[ChatService] Unexpected chunk type: {type(chunk)}")
                        continue

                    # Update metadata
                    if metadata := chunk.get('metadata'):
                        response_metadata.update(metadata)
                        
                    # Process content
                    if content := chunk.get('content', {}):
                        # Handle text
                        if text := content.get('text'):
                            yield {'text': text}
                            accumulated_text.append(text)
                        # Handle files
                        elif file_path := content.get('file_path'):
                            yield {'file_path': file_path}
                            accumulated_files.append(file_path)

                # Add complete interaction to session after successful LLM response
                if accumulated_text or accumulated_files:
                    # Add user message and assistant message in order
                    session.add_interaction(user_message.to_dict())
                    assistant_message = self._prepare_chat_message(
                        role="assistant",
                        content={
                            "text": ''.join(accumulated_text),
                            "files": accumulated_files
                        },
                        metadata=response_metadata or None
                    )
                    session.add_interaction(assistant_message.to_dict())
                    # Persist to session store
                    await self.session_store.update_session(session)

            except Exception as e:
                logger.error(f"[ChatService] Failed to get response from LLM: {str(e)}")
                yield {"text": "I apologize, but I encountered an error generating the response."}

        except Exception as e:
            logger.error(f"[ChatService] Failed to streaming reply in session {session.session_id}: {str(e)}")
            yield {"text": "I apologize, but I encountered an error. Please try again."}
