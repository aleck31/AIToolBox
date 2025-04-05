# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Union
from core.logger import logger
from llm.model_manager import model_manager
from modules import BaseHandler
from .prompts import SYSTEM_PROMPT


class AskingHandlers(BaseHandler):
    """Handlers for Asking generation with streaming support"""
    
    # Module configuration
    _module_name = "asking"
    _service_type = "gen"
    
    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Filter for models with text generation capability
            if models := model_manager.get_models(filter={'tool_use': True}):
                logger.debug(f"[AskingHandlers] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[AskingHandlers] No text-capable models available")
                return []
        except Exception as e:
            logger.error(f"[AskingHandlers] Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    async def _build_content(
        cls,
        text: str,
        files: Optional[List[str]] = None
    ) -> Dict[str, Union[str, List[str]]]:
        """Build content for generation"""
        return {
            "text": text,
            "files": files or []
        }

    @classmethod
    async def gen_with_think(
        cls,
        input: Dict,
        history: List[Dict],
        request: gr.Request
    ) -> AsyncIterator[tuple[str, str]]:
        """Generate a response based on text description and optional files
        
        Args:
            input: raw data from Gradio MultimodalTextbox input, including:
                text: User's text input
                files: Optional list of file paths
            history: raw data from gr.State, which stores the history of questions and answers
            request: FastAPI request object containing session data
            
        Yields:
            Dict: Chunks of the generated response
                thinking: thinking content while in thinking mode
                response: response content after thinking ends
        """
        try:
            # Initialize session
            service, session = await cls._init_session(request)

            # Update session with system prompt
            session.context['system_prompt'] = SYSTEM_PROMPT
            # Persist updated context
            # await service.session_store.save_session(session)

            # Build content with option history
            text = input.get('text', '')
            if history:
                text = f"This is our previous interaction history:\n{history}\nFollowing is the follow-up question:\n{text}"
            if files := input.get('files') :
                content = {'text': text, 'files': files}
            else:
                content = {'text': text}

            logger.debug(f"Build content: {content}")

            # Generate response with streaming
            thinking_buffer = "```thinking\n"
            response_buffer = ""
            in_thinking_mode = True  # Start in thinking mode
            
            async for chunk in service.gen_text_stream(
                session=session,
                content=content
            ):
                # logger.debug(f"[AskingHandlers] Received chunk: {chunk}")
                # Process each chunk immediately
                if in_thinking_mode:
                    # Currently in thinking mode - look for closing tag
                    if "</thinking>" in chunk:
                        # Split chunk at closing tag
                        parts = chunk.split("</thinking>", 1)
                        thinking_buffer += parts[0]  # Add content before closing tag to thinking
                        response_buffer += parts[1]  # Add content after closing to response
                        in_thinking_mode = False  # Switch to response mode
                    elif "<" in chunk:
                        pass
                    else:
                        # No closing tag found, all content goes to thinking (removing <thinking> if present)
                        thinking_buffer += chunk.replace("<thinking>", "")
                else:
                    # Currently in response mode - look for opening tag
                    if "<thinking>" in chunk:
                        # Split chunk at opening tag
                        parts = chunk.split("<thinking>", 1)
                        response_buffer += parts[0]  # Add content before opening tag to response
                        thinking_buffer += parts[1]  # Add content after opening tag to thinking
                        in_thinking_mode = True  # Switch to thinking mode
                    else:
                        # No opening tag found, all content goes to response
                        response_buffer += chunk.replace("</thinking>", "\n```")

                # Yield current state of both buffers
                yield thinking_buffer.strip(), response_buffer.strip()
                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming

        except Exception as e:
            logger.error(f"[AskingHandlers] Failed to Generate with think]: {str(e)}", exc_info=True)
            yield {"text": "An unexpected error occurred. Please try again."}
