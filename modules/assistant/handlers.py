import asyncio
import gradio as gr
from typing import List, Dict, Optional, AsyncGenerator, Union
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from core.integration.chat_service import ChatService
from llm.model_manager import model_manager
from .prompts import ASSISTANT_PROMPT


class AssistantHandlers:
    """Handlers for chat functionality with style support and session management"""
    
    # Shared service instance
    _service: Optional[ChatService] = None

    # Message limits
    MAX_DISPLAY_MSG = 30  # Number of messages to show in UI
    MAX_CONTEXT_MSG = 12  # Number of messages to send to LLM

    @classmethod
    def _get_service(cls) -> ChatService:
        """Get or initialize shared service instance"""
        if cls._service is None:
            logger.info("Initializing Assistant service")
            cls._service = ServiceFactory.create_chat_service(
                module_name='assistant'
            )
        return cls._service

    @classmethod
    def get_user_name(cls, request) -> Optional[str]:
        """Get authenticated user from FastAPI request"""
        return request.session.get('user', {}).get('username')
        
    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Always fetch fresh models to avoid stale cache issues
            if models := model_manager.get_models(filter={'api_provider': 'Bedrock'}):
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("No Bedrock models available")
                return []
        except Exception as e:
            logger.error(f"Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    async def load_history_confs(cls, request: gr.Request) -> tuple[List[Dict[str, str]], List[Dict[str, str]], str]:
        """Load chat history and configuration for current user

        Args:
            request: Gradio request with session data

        Returns:
            Tuple containing:
            - List of message dictionaries for UI display
            - List of message dictionaries for chat state
            - Selected model_id for the dropdown
        """
        try:
            user_name = request.session.get('user', {}).get('username')
            if not user_name:
                logger.warning("No authenticated user found in session")
                return [], [], None

            service = cls._get_service()
            
            # Get fresh session and load data
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='assistant',
                bypass_cache=True
            )
            
            # Load history and model in parallel for better performance
            history_future = service.load_session_history(
                session=session,
                max_number=cls.MAX_DISPLAY_MSG
            )
            model_future = service.get_session_model(session)
            
            latest_history, session_model_id = await asyncio.gather(
                history_future, model_future
            )

            # Return same history for both UI and state to maintain consistency
            return latest_history, latest_history, session_model_id

        except Exception as e:
            logger.error(f"Failed to load history and configs: {str(e)}", exc_info=True)
            return [], [], None

    @classmethod
    async def update_model_id(cls, model_id: str, request: gr.Request = None):
        """Update session model when dropdown selection changes"""
        try:
            # Get authenticated user and service
            user_name = cls.get_user_name(request)
            if not user_name:
                logger.warning("No authenticated user for model update")
                return

            service = cls._get_service()
            # Get active session
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='assistant'
            )
            
            # Update model
            await service.update_session_model(session, model_id)

        except Exception as e:
            logger.error(f"Failed updating session model: {str(e)}", exc_info=True)

    @classmethod
    def _normalize_input(cls, ui_input: Union[str, Dict]) -> Optional[Dict]:
        """Normalize different input formats into unified dictionary"""
        # Text-only input
        if isinstance(ui_input, str):
            return {"text": ui_input.strip()}
        # Dict input with potential files
        normalized = {
            "text": ui_input.get("text", "").strip(),
            "files": ui_input.get("files", [])
        }        
        # Remove empty values
        return {k: v for k, v in normalized.items() if v}

    @classmethod
    async def send_message(
        cls,
        ui_input: Union[str, Dict],
        ui_history: List[Dict[str, str]],
        model_id: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, Union[str, List[str]]], None]:
        """Stream assistant's response to user input
        
        Args:
            ui_input: Raw input from Gradio (text string or dict with text/files)
            ui_history: Current chat history (managed by Gradio)
            chat_style: Selected chat style option
            request: Gradio request with session data
            
        Yields:
            Dict with 'text' and optional 'files' keys for Gradio
        """
        try:
            # Input validation and normalization
            if not model_id:
                yield {"text": "Please select a model for Assistant module."}
                return

            # Convert Gradio input to a unified dictionary format
            unified_input = cls._normalize_input(ui_input)
            # Require either text or files
            if not unified_input.get("text") and not unified_input.get("files"):
                yield {"text": "Please provide a text message or file."}
                return
            logger.debug(f"[AssistantHandlers] Latest message from Gradio UI: {ui_input}")
            # logger.debug(f"Chat history from Gradio UI:\n {ui_history}")

            # Get authenticated user and service
            user_name = cls.get_user_name(request)
            if not user_name:
                yield {"text": "Authentication required. Please log in again."}
                return
            service = cls._get_service()

            try:
                # Get or create chat session with error handling
                session = await service.get_or_create_session(
                    user_name=user_name,
                    module_name='assistant'
                )
                if not session:
                    raise ValueError("Failed to create or retrieve session")
                
                # Apply assistant prompt
                session.context['system_prompt'] = ASSISTANT_PROMPT

                # Stream response with optimized accumulated handling
                accumulated_text = ""
                accumulated_files = []

                async for chunk in service.streaming_reply(
                    session=session,
                    ui_input=unified_input,
                    ui_history=ui_history[-cls.MAX_CONTEXT_MSG:]  # Limit context window
                ):
                    # Handle streaming chunks for immediate UI updates
                    if isinstance(chunk, dict):
                        # Handle streaming chunks with state preservation
                        if text := chunk.get('text', ''):
                            accumulated_text += text
                        if file_path := chunk.get('file_path', ''):
                            accumulated_files.append(file_path)
                        # Always yield both text and files together to maintain state
                        yield {
                            "text": accumulated_text, 
                            "files": accumulated_files
                        }
                    else:
                        # For legacy text only content
                        accumulated_text += chunk
                        yield {"text": accumulated_text}
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

            except Exception as e:
                logger.error(f"[AssistantHandlers] Unexpected error in chat service: {str(e)}", exc_info=True)
                yield {"text": "An unexpected error occurred. Please try again."}

        except Exception as e:
            logger.error(f"[AssistantHandlers] Failed to send message: {str(e)}", exc_info=True)
            yield {"text": "I apologize, but I encountered an error. Please try again."}
