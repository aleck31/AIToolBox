import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any, Union
from fastapi import HTTPException
from core.logger import logger
from core.integration.chat_service import ChatService
from core.module_config import module_config
from llm import LLMConfig
from llm.model_manager import model_manager


# Chat styles configuration
CHAT_STYLES = {
    "正常": {
        "description": "自然友好的对话风格",
        'prompt': "Maintain a balanced, approachable tone while providing informative and engaging responses. Be clear and articulate, but avoid being overly formal or casual.",
        "options": {}
    },
    "简洁": {
        "description": "简明扼要的表达方式",
        'prompt': "Provide concise and precise responses. Focus on essential information and eliminate unnecessary details. Use clear, direct language and short sentences. Get straight to the point while maintaining clarity and accuracy."
    },
    "专业": {
        "description": "专业正式, 用词严谨, 表意清晰",
        'prompt': "Communicate with professional expertise and academic rigor. Use industry-standard terminology, provide well-structured explanations, and maintain a formal tone. Support statements with logical reasoning and accurate information. Focus on precision and clarity in technical discussions."
    },
    "幽默": {
        "description": "诙谐有趣的对话风格",
        'prompt': "Engage with wit and humor while remaining informative. Use clever wordplay, appropriate jokes, and light-hearted analogies to make conversations entertaining. Keep the tone playful but ensure the core message remains clear and helpful."
    },
    "可爱": {
        "description": "活泼可爱的对话方式",
        'prompt': "Adopt a cheerful and endearing personality. Use gentle, friendly language with occasional emoticons. Express enthusiasm and warmth in responses. Make conversations feel light and pleasant while maintaining helpfulness. Add cute expressions where appropriate without compromising the message quality."
    }
}


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
                
                # Update session with style-specific system prompt
                session.context['system_prompt'] = CHAT_STYLES[style]["prompt"]
                
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
