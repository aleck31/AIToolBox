# Copyright iX.
# SPDX-License-Identifier: MIT-0
from typing import Dict, List, Any
import asyncio
from fastapi import HTTPException
from core.integration.service_factory import ServiceFactory
from core.integration.module_config import module_config
from llm import ModelProvider
from core.auth import get_current_user
from core.logger import logger

# Lazy initialization of chat service
_chat_service = None

def get_chat_service():
    """Get or create chat service instance"""
    global _chat_service
    if _chat_service is None:
        try:
            _chat_service = ServiceFactory.create_chat_service(
                llm_config=ServiceFactory.create_default_llm_config(
                    provider=ModelProvider.GEMINI,
                    model_id=module_config.get_default_model('chatbot-gemini')
                ),
                with_auth=True  # Enable authentication
            )
            logger.debug("Gemini chat service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini chat service: {str(e)}")
            raise
    return _chat_service

async def prepare_message_content(message: Any) -> Dict:
    """
    Prepare message content for chat service
    
    Args:
        message: String or dict with format {"text": str, "files": List[str]}
        
    Returns:
        Dict: Formatted message content
        
    Raises:
        Exception: If message preparation fails
    """
    try:
        if isinstance(message, str):
            return {"text": message}
            
        content = {"text": message.get('text', '')}
        
        if message.get('files'):
            # Handle multiple files
            files = []
            for file_path in message.get('files'):
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                files.append({
                    "data": file_data,
                    "mime_type": "image/jpeg"  # TODO: Detect actual mime type
                })
            content["files"] = files
            
        return content
        
    except Exception as e:
        logger.error(f"Failed to prepare message content: {e}")
        raise

async def multimodal_chat(message: Any, history: List[Dict], request=None):
    """
    Handle multimodal chat interactions
    
    Args:
        message: String or dict with format {"text": str, "files": List[str]}
        history: List of previous messages
        request: FastAPI request object for getting authenticated user
        
    Yields:
        Dict: Assistant's response chunks
        
    Raises:
        HTTPException: If user is not authenticated
    """
    try:
        if not request:
            raise HTTPException(status_code=401, detail="Authentication required")
            
        # Get authenticated user from session
        user = request.session.get('user')
        if not user or not user.get('username'):
            raise HTTPException(status_code=401, detail="User not authenticated")
            
        user_id = user['username']
        chat_service = get_chat_service()
        
        # Get current session ID from user's active sessions or create new one
        sessions = await chat_service.list_chat_sessions(user_id=user_id)
        session = None
        
        # Try to find an active session
        for s in sessions:
            if s.metadata.model_id == module_config.get_default_model('chatbot-gemini'):
                session = s
                break
        
        # Create new session if none found
        if not session:
            session = await chat_service.create_chat_session(
                user_id=user_id,
                session_name="Gemini Chat",
                model_id=module_config.get_default_model('chatbot-gemini'),
                system_prompt=module_config.get_system_prompt('chatbot-gemini') or "\n".join([
                    "You are a friendly chatbot.",
                    "You are talkative and provides lots of specific details from its context.",
                    "If you are unsure or don't have enough information to provide a confident answer, just say 'I do not know' or 'I am not sure."
                ])
            )
            
            # Add history if exists
            if history:
                for msg in history:
                    await chat_service.send_message(
                        session_id=session.session_id,
                        content=msg["content"]
                    )
        
        # Prepare message content
        content = await prepare_message_content(message)
        
        # Send message and stream response
        response = await chat_service.send_message(
            session_id=session.session_id,
            content=content,
            stream=True
        )
        
        async for chunk in response:
            yield {"role": "assistant", "content": chunk}
            
    except HTTPException as e:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error in multimodal_chat: {e}")
        yield {"role": "assistant", "content": f"An error occurred: {str(e)}"}

async def _run_chat(message: Any, history: List[Dict], request=None):
    """Helper function to collect all chunks from the generator"""
    chunks = []
    async for chunk in multimodal_chat(message, history, request):
        chunks.append(chunk)
    return chunks[-1] if chunks else {"role": "assistant", "content": "No response generated"}

def sync_multimodal_chat(message: Any, history: List[Dict], request=None):
    """
    Synchronous wrapper for multimodal_chat
    
    Args:
        message: Message content
        history: Chat history
        request: FastAPI request object for authentication
        
    Returns:
        Dict: Final response chunk
    """
    return asyncio.run(_run_chat(message, history, request))
