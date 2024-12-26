import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from fastapi import HTTPException
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import CHAT_STYLES


class ChatHandlers:
    """Handlers for chat functionality with style support and session management"""
    
    # Shared service instances
    chat_service = None
    
    @classmethod
    def initialize(cls):
        """Initialize shared services if not already initialized"""
        if cls.chat_service is None:
            cls.chat_service = ServiceFactory.create_chat_service('chatbot')
    
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
                    module_name='chatbot'
                )
                
                # Get style-specific configuration
                style_config = CHAT_STYLES[addn_style]
                
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
                    # Let Gradio handle the diffing - just yield each chunk
                    yield chunk

            except HTTPException as e:
                logger.error(f"Chat service error: {e.detail}")
                yield f"Error: {e.detail}"

            except Exception as e:
                logger.error(f"Unexpected error in chat service: {str(e)}")
                yield "An unexpected error occurred. Please try again."

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
