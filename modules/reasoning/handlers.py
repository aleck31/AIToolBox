# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Union
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import SYSTEM_PROMPT


class ReasoningHandlers:
    """Handlers for Reasoning generation with streaming support"""
    
    # Shared service instance
    _service = None
    
    @classmethod
    async def _get_service(cls):
        """Get or initialize service lazily"""
        if cls._service is None:
            cls._service = ServiceFactory.create_gen_service('reasoning')
        return cls._service

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
            # Get service (initializes lazily if needed)
            service = await cls._get_service()

            # Get authenticated user from FastAPI session if available
            try:
                user_name = request.session.get('user', {}).get('username')

                # Get or create session
                session = await service.get_or_create_session(
                    user_name=user_name,
                    module_name='reasoning'
                )
            except Exception as e:
                logger.error(f"Failed to create session: {str(e)}")
                yield ("Error initializing session", f"Error: {str(e)}")
                return

            # Update session with system prompt
            session.context['system_prompt'] = SYSTEM_PROMPT
            # Persist updated context
            await service.session_store.update_session(session, user_name)

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
            thinking_buffer = "```thinking"
            response_buffer = ""
            in_thinking_mode = True  # Always starts with thinking
            
            async for chunk in service.gen_text_stream(
                session_id=session.session_id,
                content=content
            ):
                if in_thinking_mode:
                    if "</thinking>" in chunk:
                        # Split chunk at </thinking> tag
                        parts = chunk.split("</thinking>", 1)
                        # Add content before </thinking> to thinking buffer (removing <thinking> if present)
                        thinking_buffer += parts[0].replace("<thinking>", "")
                        # Add content after </thinking> to response buffer
                        if len(parts) > 1:
                            response_buffer += parts[1]
                        in_thinking_mode = False
                    else:
                        # Add chunk to thinking buffer (removing <thinking> if present)
                        thinking_buffer += chunk.replace("<thinking>", "")
                else:
                    # After thinking mode, everything goes to response
                    response_buffer += chunk

                # Yield current state of both buffers
                yield thinking_buffer.strip(), response_buffer.strip()
                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming
                
        except Exception as e:
            logger.error(f"Error in [gen_with_think]: {str(e)}")
            yield ("Error during processing", f"Error: {str(e)}")
# Focus on lazy-initialization refactoring  without dealing with the backtick handling logic.
