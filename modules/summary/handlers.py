# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator
from fastapi import HTTPException
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import SYSTEM_PROMPT, build_user_prompt


class SummaryHandlers:
    """Handlers for text summarization with streaming support"""
    
    # Shared service instance
    _service = None
    
    @classmethod
    async def _get_service(cls):
        """Get or initialize service lazily"""
        if cls._service is None:
            # Enable web_tools for URL handling
            cls._service = ServiceFactory.create_gen_service('summary')
        return cls._service

    @classmethod
    async def summarize_text(
        cls,
        text: str,
        target_lang: str,
        request: gr.Request
    ) -> AsyncIterator[str]:
        """Generate a summary of the input text with streaming response
        
        Args:
            text: The text to summarize
            target_lang: Target language for the summary ('original', 'Chinese', or 'English')
            user_name: User ID for session management
            
        Yields:
            str: Chunks of the generated summary
        """
        if not text:
            yield "Please provide some text to summarize."
            return

        try:
            # Get service (initializes lazily if needed)
            service = await cls._get_service()

            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')

            try:
                # Get or create session
                session = await service.get_or_create_session(
                    user_name=user_name,
                    module_name='summary'
                )

                # Update session with system prompt
                session.context['system_prompt'] = SYSTEM_PROMPT
                # Persist updated context
                await service.session_store.update_session(session, user_name)

                # Build content with system prompt
                content = {
                    "text": build_user_prompt(text, target_lang)
                }
                logger.debug(f"Build content: {content}")

                # Stream response with accumulated display
                buffered_text = ""
                async for chunk in service.gen_text_stream(
                    session_id=session.session_id,
                    content=content
                ):
                    # Accumulate text for display while maintaining streaming
                    buffered_text += chunk
                    yield buffered_text
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

            except Exception as e:
                logger.error(f"Service error: {str(e)}")
                yield f"Error: {str(e)}"

        except HTTPException as e:
            logger.error(f"Authentication error: {e.detail}")
            yield str(e.detail)
        except Exception as e:
            logger.error(f"Error in [summarize_text]: {str(e)}")
            yield "An error occurred while generating the summary. Please try again."
