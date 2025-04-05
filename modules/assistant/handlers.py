import asyncio
import gradio as gr
from typing import List, Dict, AsyncGenerator, Union, Optional, Tuple
from core.logger import logger
from llm.model_manager import model_manager
from modules import BaseHandler
from .prompts import ASSISTANT_PROMPT


class AssistantHandlers(BaseHandler):
    """Handlers for chat functionality with style support and session management."""
    
    # Module name for the handler
    _module_name: str = "assistant"
    
    # Service type
    _service_type: str = "chat"
    
    MAX_DISPLAY_MSG: int = 30  # Number of messages to show in UI
    MAX_CONTEXT_MSG: int = 12  # Number of messages to send to LLM

    @classmethod
    def get_user_name(cls, request: gr.Request) -> Optional[str]:
        """Get authenticated user from FastAPI request."""
        if user_name := request.session.get('user', {}).get('username'):
            return user_name
        else:
            logger.warning("[AssistantHandlers] No authenticated user found")
            return None

    @classmethod
    def get_available_models(cls) -> List[Tuple[str, str]]:
        """Get list of available models with id and names."""
        try:
            # Filter for Bedrock models
            if models := model_manager.get_models(filter={'tool_use': True}):
                logger.debug(f"[AssistantHandlers] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[AssistantHandlers] No Bedrock models available")
                return []

        except Exception as e:
            logger.error(f"[AssistantHandlers] Failed to fetch models: {e}", exc_info=True)
            return []

    @classmethod
    async def load_history_confs(
        cls, request: gr.Request
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]], Optional[str]]:
        """
        Load chat history and configuration for current user.

        Args:
            request: Gradio request with session data

        Returns:
            Tuple containing:
            - List of message dictionaries for UI display
            - List of message dictionaries for chat state
            - Selected model_id for the dropdown
        """
        try:
            # Initialize session
            service, session = await cls._init_session(request)

            history_future = service.load_session_history(
                session=session,
                max_messages=cls.MAX_DISPLAY_MSG
            )
            model_future = service.get_session_model(session)
            
            latest_history, session_model_id = await asyncio.gather(
                history_future, model_future
            )

            # Return same history for both UI and state to maintain consistency
            return latest_history, latest_history, session_model_id

        except Exception as e:
            logger.error(f"[AssistantHandlers] Failed to load history: {e}", exc_info=True)
            return [], [], None

    @classmethod
    async def clear_chat_history(
        cls, chatbot_state: List, request: gr.Request
    ) -> Tuple[List, List]:
        """
        Clear chat history when clear button is clicked.

        Args:
            chatbot_state: Current chatbot state from ChatInterface
            request: Gradio request with session data

        Returns:
            Tuple of (updated chatbot state, empty list for UI)
        """
        try:
            # Initialize session
            service, session = await cls._init_session(request)

            # Clear history in session
            await service.clear_history(session)
            logger.debug(f"[AssistantHandlers] Cleared history for user: {session.user_name}")
            gr.Info(f"Cleared history for session {session.session_name}", duration=3)
            # Return empty state and chatbot
            return [], []
            
        except Exception as e:
            logger.error(f"[AssistantHandlers] Failed to clear history: {e}", exc_info=True)
            # Return current state and empty chatbot on error
            return chatbot_state, []

    @classmethod
    def _normalize_input(cls, ui_input: Union[str, Dict]) -> Dict[str, Union[str, List]]:
        """
        Normalize different input formats into unified dictionary.

        Args:
            ui_input: Raw input from Gradio UI (string or dict)

        Returns:
            Normalized dictionary with text and optional files
        """
        # for Text-only input
        if isinstance(ui_input, str):
            return {"text": ui_input.strip()}
        # for Dict input with potential files
        return {
            k: v for k, v in {
                "text": ui_input.get("text", "").strip(),
                "files": ui_input.get("files", [])
            }.items() if v  # Remove empty values
        }

    @classmethod
    async def send_message(
        cls,
        ui_input: Union[str, Dict],
        ui_history: List[Dict[str, str]],
        model_id: str,
        request: gr.Request
    ) -> AsyncGenerator[Dict[str, Union[str, List[str]]], None]:
        """
        Stream assistant's response to user input.

        Args:
            ui_input: Raw input from Gradio (text string or dict with text/files)
            ui_history: Current chat history (managed by Gradio)
            model_id: Selected model identifier
            request: Gradio request with session data

        Yields:
            Dict with text and optional files list
        """
        # Input validation
        if not model_id:
            yield {"text": "Please select a model for Assistant module."}
            return

        try:
            # Convert Gradio input to a unified dictionary format
            unified_input = cls._normalize_input(ui_input)
            if not unified_input:
                yield {"text": "Please provide a message or file."}
                return
            logger.debug(f"[AssistantHandlers] User message from Gradio UI: {ui_input}")

            # Initialize session
            service, session = await cls._init_session(request)

            # Configure assistant prompt
            session.context['system_prompt'] = ASSISTANT_PROMPT
            logger.debug(f"[AssistantHandlers] Processing message: {unified_input}")

            # Stream response
            accumulated_text = ""
            accumulated_files = []

            async for chunk in service.streaming_reply(
                session=session,
                ui_input=unified_input,
                ui_history=ui_history[-cls.MAX_CONTEXT_MSG:]
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
                # For legacy text only content (when chunk is a string)
                else:
                    accumulated_text += chunk
                    yield {"text": accumulated_text}

                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

        except Exception as e:
            logger.error(f"[AssistantHandlers] Failed to send message: {e}", exc_info=True)
            yield {"text": "I apologize, but I encountered an error. Please try again."}
