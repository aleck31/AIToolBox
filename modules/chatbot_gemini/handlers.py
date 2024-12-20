import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from core.logger import logger
from llm import LLMConfig
from core.integration.chat_service import ChatService
from core.module_config import module_config
from llm.model_manager import model_manager


SYSTEM_PROMPT = '''
    You are a friendly chatbot.
    You are talkative and provides lots of specific details from its context.
    If you are unsure or don't have enough information to provide a confident answer, just say 'I do not know' or 'I am not sure.'
'''

class GeminiChatHandlers:
    """Handlers for Gemini chat functionality with session management"""
    
    # Shared service instance
    chat_service = None
    
    @classmethod
    def initialize(cls):
        """Initialize shared services if not already initialized"""
        if cls.chat_service is None:
            # Get model configuration from module config
            model_id = module_config.get_default_model('chatbot-gemini')
            params = module_config.get_inference_params('chatbot-gemini') or {}
            
            # Get model info from model manager
            model = model_manager.get_model_by_id(model_id)
            if not model:
                raise ValueError(f"Model not found: {model_id}")
            
            # Create LLM config with module parameters
            model_config = LLMConfig(
                api_provider=model.api_provider,
                model_id=model_id,
                temperature=params.get('temperature', 0.7),
                max_tokens=params.get('max_tokens', 1000),
                top_p=params.get('top_p', 0.99),
                top_k=params.get('top_k', 200)
            )
            
            # Initialize chat service with model config
            cls.chat_service = ChatService(model_config=model_config)
    
    @classmethod
    async def handle_chat(
        cls,
        message: Union[str, Dict],
        history: List[Dict[str, str]],
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Handle chat messages with streaming support
        
        Args:
            message: User's message (can be string or dict with text and files)
            history: Chat history list (managed by Gradio)
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
                    yield {
                        "role": "assistant",
                        "content": "Please provide a message."
                    }
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
                session = await cls.chat_service.get_chat_session(
                    user_id=user_id,
                    module_name='chatbot-gemini',
                    session_name="Gemini Chat",
                    system_prompt=SYSTEM_PROMPT
                )

                # Stream chat response
                partial_msg = ""
                async for event in cls.chat_service.send_message(
                    session_id=session.session_id,
                    user_id=user_id,
                    content=content
                ):
                    # Handle different event types
                    if isinstance(event, dict):
                        event_type = event.get('type')
                        
                        if event_type == 'messageStart':
                            # Initialize new message
                            partial_msg = ""
                            
                        elif event_type == 'contentBlockDelta':
                            # Append new content
                            if delta := event.get('delta', {}):
                                if text := delta.get('text', ''):
                                    partial_msg += text
                                    # Gradio will optimize to only send the diff
                                    yield {
                                        "role": "assistant",
                                        "content": partial_msg
                                    }
                                    
                        elif event_type == 'messageStop':
                            # Final yield with complete message
                            if partial_msg:
                                yield {
                                    "role": "assistant",
                                    "content": partial_msg
                                }

            except Exception as e:
                logger.error(f"Chat service error: {str(e)}")
                yield {
                    "role": "assistant",
                    "content": "Failed to process your message. Please try again."
                }

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield {
                "role": "assistant",
                "content": "I apologize, but I encountered an error. Please try again."
            }
