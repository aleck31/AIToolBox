# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from core.integration.gen_service import GenService
from .prompts import SYSTEM_PROMPT, build_user_prompt


class SummaryHandlers:
    """Handlers for text summarization with streaming support"""
    
    # Shared service instance
    _service : Optional[GenService] = None
    
    @classmethod
    async def _get_service(cls) -> GenService:
        """Get or initialize service lazily"""
        if cls._service is None:
            logger.info("[SummaryHandlers] Initializing service")
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
                await service.session_store.save_session(session)

                # Build content with system prompt
                content = {
                    "text": build_user_prompt(text, target_lang)
                }
                logger.debug(f"[SummaryHandlers] Build content: {content}")

                # Stream response with accumulated display
                buffered_text = ""
                async for chunk in service.gen_text_stream(
                    session=session,
                    content=content
                ):
                    # Accumulate text for display while maintaining streaming
                    buffered_text += chunk
                    yield buffered_text
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

            except Exception as e:
                logger.error(f"[SummaryHandlers] Service error: {str(e)}")
                yield f"Error: {str(e)}"

        except Exception as e:
            logger.error(f"[SummaryHandlers] Failed to summarize text: {str(e)}", exc_info=True)
            yield f"An error occurred while summarize the text. \n str(e.detail)"
