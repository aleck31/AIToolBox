import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from fastapi import HTTPException
from core.logger import logger
from core.integration.chat_service import ChatService
from core.module_config import module_config
from llm import LLMConfig
from llm.model_manager import model_manager
from .prompts import CHAT_STYLES


class ChatHandlers:
    """Handlers for chat functionality with style support and session management"""
    
    # Shared service instances
    chat_service = None
    
    @classmethod
    def initialize(cls):
        """Initialize shared services if not already initialized"""
        if cls.chat_service is None:
            # Get model configuration from module config
            model_id = module_config.get_default_model('chatbot')
            params = module_config.get_inference_params('chatbot') or {}
            
            # Get model info from model manager
            model = model_manager.get_model_by_id(model_id)
            if not model:
                raise ValueError(f"Model not found: {model_id}")
            
            # Create LLM config with module parameters
            model_config = LLMConfig(
                api_provider=model.api_provider,
                model_id=model_id,
                temperature=params.get('temperature', 0.7),
                max_tokens=int(params.get('max_tokens', 2048)),
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
        style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Handle chat messages with streaming support
        
        Args:
            message: User's message (can be string or dict with text and files)
            history: Chat history list (managed by Gradio)
            style: Selected chat style
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
                    module_name='chatbot',
                    session_name="Chatbot Session"
                )
                
                # Get style-specific configuration
                style_config = CHAT_STYLES[style]
                
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
                    user_id=user_id,
                    content=content,
                    ui_history=history,
                    inference_params=inference_params
                ):
                    # Let Gradio handle the diffing - just yield each chunk
                    yield {
                        "role": "assistant",
                        "content": chunk
                    }

            except HTTPException as e:
                logger.error(f"Chat service error: {e.detail}")
                yield {
                    "role": "assistant",
                    "content": f"Error: {e.detail}"
                }
            except Exception as e:
                logger.error(f"Unexpected error in chat service: {str(e)}")
                yield {
                    "role": "assistant",
                    "content": "An unexpected error occurred. Please try again."
                }

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield {
                "role": "assistant",
                "content": "I apologize, but I encountered an error. Please try again."
            }
