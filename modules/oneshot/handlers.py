# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Union
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import SYSTEM_PROMPT


class OneshotHandlers:
    """Handlers for one-shot generation with streaming support"""
    
    # Shared service instance
    _service = None
    
    @classmethod
    async def _get_service(cls):
        """Get or initialize service lazily"""
        if cls._service is None:
            cls._service = ServiceFactory.create_gen_service('oneshot')
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
                    module_name='oneshot'
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
            content = {
                "text": text,
                "files": input.get('files', [])
            }
            logger.debug(f"Build content: {content}")

            # Generate response with streaming
            thinking_buffer = ""
            response_buffer = ""
            backtick_count = 0  # Count of ``` occurrences
            in_thinking_mode = True
            
            async for chunk in service.gen_text_stream(
                session_id=session.session_id,
                content=content
            ):
                # the closing ``` should added to thinking_buffer to close the ```thinking tag
                # add chunk to appropriate buffer based on updated mode
                if in_thinking_mode:
                    thinking_buffer += chunk
                else:
                    response_buffer += chunk

                # Count occurrences of ``` in this chunk
                backtick_count += chunk.count("```")
                # Update mode based on backtick count
                in_thinking_mode = (backtick_count % 2 == 1)

                # Yield current state of both buffers
                yield thinking_buffer, response_buffer
                
                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming
                
        except Exception as e:
            logger.error(f"Error in [gen_with_think]: {str(e)}")
            yield ("Error during processing", f"Error: {str(e)}")
# Focus on lazy-initialization refactoring  without dealing with the backtick handling logic.
