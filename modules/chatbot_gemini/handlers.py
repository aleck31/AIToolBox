import asyncio
import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Union
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
    async def send_message(
        cls,
        ui_input: Union[str, Dict],
        ui_history: List[Dict[str, str]],
        chat_style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Reply chat messages in streaming to load content progressively
        
        Args:
            message: User's message (can be string or dict with text and files)
            ui_history: Current chat history (managed by Gradio)
            chat_style: Selected chat style option
            request: Gradio request with session data
            
        Yields:
            Message chunks for Gradio chatbot
        """
        try:
            # Initialize services if needed
            cls.initialize()

            # Validate and format user input
            if not ui_input:
                yield "Please provide a message or file."
                return
                        
            # Convert Gradio input to a unified dictionary format
            unified_input = (
                # Text-only input (string)
                {"text": ui_input} if isinstance(ui_input, str)
                # Dict input (could have text and/or files)
                else {
                    "text": ui_input.get("text", ""),  # Empty string if no text
                    "files": ui_input.get("files", []) # Empty list if no files
                }
            )

            # Require either text or files
            if not unified_input["text"] and not unified_input.get("files"):
                yield "Please provide a message or file."
                return
            
            # Get authenticated user from FastAPI session
            user_id = request.session.get('user', {}).get('username')
            if not user_id:
                yield "Authentication required. Please log in again."
                return

            try:
                # Get or create chat session
                session = await cls.chat_service.get_or_create_session(
                    user_id=user_id,
                    module_name='chatbot-gemini'
                )
                
                # Get style-specific configuration (default to 'default' style if not found)
                style_config = GEMINI_CHAT_STYLES.get(chat_style, GEMINI_CHAT_STYLES['default'])
                
                # Update session with style-specific system prompt
                session.context['system_prompt'] = style_config["prompt"]
                
                # Persist updated context to session store
                await cls.chat_service.session_store.update_session(session, user_id)
                
                # Prepare style-specific inference parameters
                style_params = {k: v for k, v in style_config["options"].items() if v is not None}
                
                # Stream chat response with UI history sync and style parameters
                buffered_text = ""
                async for chunk in cls.chat_service.streaming_reply(
                    session_id=session.session_id,
                    ui_input=unified_input,
                    ui_history=ui_history,
                    style_params=style_params
                ):
                    # Accumulate text for display while maintaining streaming
                    buffered_text += chunk
                    yield buffered_text
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

            except Exception as e:
                logger.error(f"Unexpected error in chat service: {str(e)}")
                yield "An unexpected error occurred. Please try again."

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
