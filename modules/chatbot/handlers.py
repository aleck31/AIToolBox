import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Union
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
    async def send_message(
        cls,
        ui_input: Union[str, Dict],
        ui_history: List[Dict[str, str]],
        chat_style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Stream assistant's response to user input
        
        Args:
            ui_input: Raw input from Gradio (text string or dict with text/files)
            ui_history: Current chat history (managed by Gradio)
            chat_style: Selected chat style option
            request: Gradio request with session data
            
        Yields:
            Formatted message chunks for Gradio chatbot
        """
        try:
            # Initialize services if needed
            cls.initialize()
            
            # Validate and format user input
            if not ui_input:
                yield {"role": "assistant", "content": "Please provide a message or file."}
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
                yield {"role": "assistant", "content": "Please provide a message or file."}
                return

            # Get authenticated user from FastAPI session
            user_id = request.session.get('user', {}).get('username')
            if not user_id:
                yield {"role": "assistant", "content": "Authentication required. Please log in again."}
                return

            try:
                # Get or create chat session
                session = await cls.chat_service.get_or_create_session(
                    user_id=user_id,
                    module_name='chatbot'
                )
                
                # Apply chat style configuration
                style_config = CHAT_STYLES[chat_style]
                session.context['system_prompt'] = style_config["prompt"]
                
                # Get style-specific parameters
                style_params = {k: v for k, v in style_config["options"].items() if v is not None}
                
                # Stream response with optimized history sync
                async for response_chunk in cls.chat_service.streaming_reply(
                    session_id=session.session_id,
                    ui_input=unified_input,
                    ui_history=ui_history,
                    style_params=style_params
                ):
                    yield response_chunk

            except Exception as e:
                logger.error(f"Unexpected error in chat service: {str(e)}")
                yield "An unexpected error occurred. Please try again."

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield "I apologize, but I encountered an error. Please try again."
