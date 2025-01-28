import asyncio
import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Union
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import CHAT_STYLES


def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting


class ChatHandlers:
    """Handlers for chat functionality with style support and session management"""
    
    # Shared service instances
    chat_service = None
    
    # Chat history limits
    MAX_DISPLAY_MSG = 30  # Number of messages to show in UI (N) - Shows last 15 conversation turns
    MAX_CONTEXT_MSG = 12  # Number of messages to send to LLM (M) - Provides the last 6 complete conversation turns

    @classmethod
    def initialize(cls):
        """Initialize or refresh chat service with current tool configuration"""
        from core.module_config import module_config
        
        # Get current enabled tools from module config
        current_tools = module_config.get_enabled_tools('chatbot')
        
        # Initialize service if not exists or tools have changed
        if cls.chat_service is None:
            cls.chat_service = ServiceFactory.create_chat_service('chatbot', updated_tools=current_tools)
            logger.info(f"Chat service initialized with tools: {current_tools}")
        elif set(current_tools) != set(cls.chat_service.enabled_tools):
            # Tools have changed, create new service instance
            cls.chat_service = ServiceFactory.create_chat_service('chatbot', updated_tools=current_tools)
            logger.info(f"Chat service refreshed with updated tools: {current_tools}")

    @classmethod
    async def load_history(cls, request: gr.Request) -> tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        """Load chat history for current user
        
        Args:
            request: Gradio request with session data
            
        Returns:
            Tuple of (visual_history, context_history) for Gradio chatbot display and state
        """
        try:
            # Initialize services if needed
            cls.initialize()

            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')
            if not user_name:
                return [], []

            # Load latest chat history from service
            latest_history = await cls.chat_service.load_chat_history(user_name, 'chatbot', cls.MAX_DISPLAY_MSG)
            
            return latest_history, latest_history
            
        except Exception as e:
            logger.error(f"Error loading chat history: {str(e)}")
            return [], []
    
    @classmethod
    async def send_message(
        cls,
        ui_input: Union[str, Dict],
        ui_history: List[Dict[str, str]],
        chat_style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, Union[str, List[str]]], None]:
        """Stream assistant's response to user input
        
        Args:
            ui_input: Raw input from Gradio (text string or dict with text/files)
            ui_history: Current chat history (managed by Gradio)
            chat_style: Selected chat style option
            request: Gradio request with session data
            
        Yields:
            Dict with 'text' and optional 'files' keys for Gradio chatbot
        """
        try:
            # Initialize services if needed
            cls.initialize()
            
            # Validate and format user input
            if not ui_input:
                yield {"text": "Please provide a message or file."}
                return

            logger.debug(f"Latest message from Gradio UI:\n {ui_input}")
            logger.debug(f"Chat history from Gradio UI:\n {ui_history}")

            # Convert Gradio input to a unified dictionary format
            if isinstance(ui_input, str):
                # Text-only input
                unified_input = {"text": ui_input}
            else:
                # Dict input with potential files
                unified_input = {"text": ui_input.get("text", "")}
                if files := ui_input.get("files"):
                    unified_input["files"] = files

            # Require either text or files
            if not unified_input["text"] and not unified_input.get("files"):
                yield {"text": "Please provide a message or file."}
                return

            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')
            if not user_name:
                yield {"text": "Authentication required. Please log in again."}
                return

            try:
                # Get or create chat session
                session = await cls.chat_service.get_or_create_session(
                    user_name=user_name,
                    module_name='chatbot'
                )
                
                # Apply chat style configuration
                style_config = CHAT_STYLES[chat_style]
                session.context['system_prompt'] = style_config["prompt"]
                
                # Get style-specific parameters
                style_params = {k: v for k, v in style_config["options"].items() if v is not None}
                
                # Stream response with accumulated display
                buffered_text = ""

                async for chunk in cls.chat_service.streaming_reply(
                    session_id=session.session_id,
                    ui_input=unified_input,
                    ui_history=ui_history,
                    style_params=style_params,
                    max_number=cls.MAX_CONTEXT_MSG
                ):
                    # we need to ensure the streaming_reply() method also correctly returns the file_path to the handler .
                    # Accumulate text for display while maintaining streaming
                    if isinstance(chunk, dict):
                        if 'file_path' in chunk:
                            # For file path content (from generate_image tool)
                            yield {
                                "text": buffered_text,
                                "files": [chunk['file_path']]
                            }
                    else:
                        # For text content, accumulate and yield
                        buffered_text += chunk
                        yield {"text": buffered_text}
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo
            except Exception as e:
                logger.error(f"Unexpected error in chat service: {str(e)}")
                yield {"text": "An unexpected error occurred. Please try again."}

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield {"text": "I apologize, but I encountered an error. Please try again."}
