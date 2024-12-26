import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from fastapi import HTTPException
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import GEMINI_CHAT_STYLES

class GeminiChatHandlers:
    """Handlers for Gemini chat functionality with session management"""
    
    # Shared service instance
    chat_service = None
    
    @classmethod
    def initialize(cls):
        """Initialize shared services if not already initialized"""
        if cls.chat_service is None:
            cls.chat_service = ServiceFactory.create_chat_service('chatbot-gemini')
    
    @classmethod
    async def clear_history(
        cls,
        request: gr.Request
    ) -> List[Dict[str, str]]:
        """Clear chat history while preserving session"""
        try:
            # Initialize services if needed
            cls.initialize()
            
            # Get user info from FastAPI session
            user_info = request.session.get('user', {})
            user_id = user_info.get('username')
            
            if not user_id:
                return []
                
            # Get current session
            session = await cls.chat_service.get_or_create_session(
                user_id=user_id,
                module_name='chatbot-gemini'
            )
            
            # Clear session history
            await cls.chat_service.clear_chat_session(
                session_id=session.session_id,
                user_id=user_id
            )
            
            return []
            
        except Exception as e:
            logger.error(f"Error clearing history: {str(e)}")
            return []

    @classmethod
    async def streaming_reply(
        cls,
        message: Union[str, Dict],
        history: List[Dict[str, str]],
        addn_style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Reply chat messages in streaming to load content progressively
        
        Args:
            message: User's message (can be string or dict with text and files)
            history: Chat history list (managed by Gradio)
            addn_style: Selected chat style
            request: Gradio request object containing session data
            
        Yields:
            Dict with role and content for assistant's response
        """
        try:
            # Initialize services if needed
            cls.initialize()
            
            # Handle Gradio chatbox format
            if isinstance(message, dict):
                if not message.get("text"):
                    yield {
                        "role": "assistant",
                        "content": "Please provide a message."
                    }
                    return
                content = {
                    "text": message["text"],
                    "files": message.get("files", [])
                }
            else:
                if not message:
                    yield "Please provide a message."
                    return
                
                content = {"text": message}
                
            # Get user info from FastAPI session
            user_info = request.session.get('user', {})
            user_id = user_info.get('username')
            
            if not user_id:
                yield {
                    "role": "assistant",
                    "content": "Authentication required. Please log in again."
                }
                return

            try:
                # Get or create chat session
                session = await cls.chat_service.get_or_create_session(
                    user_id=user_id,
                    module_name='chatbot-gemini'
                )
                
                # Get style-specific configuration (default to 'default' style if not found)
                style_config = GEMINI_CHAT_STYLES.get(addn_style, GEMINI_CHAT_STYLES['default'])
                
                # Update session with style-specific system prompt
                session.context['system_prompt'] = style_config["prompt"]
                
                # Persist updated context to session store
                await cls.chat_service.session_store.update_session(session, user_id)
                
                # Prepare style-specific inference parameters
                inference_params = {
                    k: v for k, v in style_config["options"].items()
                    if v is not None
                }
                
                # Stream chat response with UI history sync and style parameters
                async for chunk in cls.chat_service.send_message(
                    session_id=session.session_id,
                    content=content,
                    ui_history=history,
                    option_params=inference_params
                ):
                    yield chunk

            except Exception as e:
                logger.error(f"Chat service error: {str(e)}")
                yield "Failed to process your message. Please try again."

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
