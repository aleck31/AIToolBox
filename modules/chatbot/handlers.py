import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Any
from core.logger import logger
from core.integration.chat_service import ChatService
from core.session.dynamodb_manager import DynamoDBSessionManager
from llm import LLMConfig, ModelProvider


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
            # Initialize session manager
            session_manager = DynamoDBSessionManager()
            
            # Initialize chat service with default model config
            default_model_config = LLMConfig(
                provider=ModelProvider.BEDROCK,
                model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                temperature=0.7,
                max_tokens=1000
            )
            cls.chat_service = ChatService(session_manager, default_model_config)
    
    @classmethod
    async def handle_chat(
        cls,
        message: str,
        history: List[Dict[str, str]],
        style: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, str], None]:
        """Handle chat messages with streaming support
        
        Args:
            message: User's message text
            history: Chat history list (managed by Gradio)
            style: Selected chat style
            request: Gradio request object containing session data
            
        Yields:
            Dict with role and content for assistant's response
        """
        try:
            # Initialize services if needed
            cls.initialize()
            
            if not message:
                yield {
                    "role": "assistant",
                    "content": "Please provide a message."
                }
                return
                
            # Get user info from FastAPI session
            user_info = request.session.get('user', {})
            user_id = user_info.get('username')
            
            if not user_id:
                yield {
                    "role": "assistant",
                    "content": "Authentication required. Please log in again."
                }
                return

            # Get or create chat session
            session = await cls.chat_service.create_chat_session(
                user_id=user_id,
                session_name="Chatbot Session",
                system_prompt=CHAT_STYLES[style]["prompt"],
                module_name='chatbot'
            )

            # Stream chat response
            async for chunk in cls.chat_service.send_message(
                session_id=session.session_id,
                user_id=user_id,
                content={"text": message}
            ):
                yield {
                    "role": "assistant",
                    "content": chunk
                }

        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}")
            yield {
                "role": "assistant",
                "content": "I apologize, but I encountered an error. Please try again."
            }
