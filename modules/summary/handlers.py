# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import AsyncIterator
from core.logger import logger
from llm.model_manager import model_manager
from modules import BaseHandler
from .prompts import SYSTEM_PROMPT, build_user_prompt


class SummaryHandlers(BaseHandler):
    """Handlers for text summarization with streaming support"""
    
    # Module configuration
    _module_name = "summary"
    _service_type = "gen"
    
    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Filter for models with tool use capability
            if models := model_manager.get_models(filter={'tool_use': True}):
                logger.debug(f"[SummaryHandlers] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[SummaryHandlers] No text-capable models available")
                return []
        except Exception as e:
            logger.error(f"[SummaryHandlers] Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    async def summarize_text(
        cls,
        text: str,
        target_lang: str,
        model_id: str,
        request: gr.Request
    ) -> AsyncIterator[str]:
        """Generate a summary of the input text with streaming response
        
        Args:
            text: The text to summarize
            target_lang: Target language for the summary ('original', 'Chinese', or 'English')
            model_id: Model to use for summarization
            request: Gradio request object containing session information
            
        Yields:
            str: Chunks of the generated summary
        """
        if not text:
            yield "Please provide some text to summarize."
            return

        if not model_id:
            gr.Info("lease select a model for summarization.", duration=3)

        try:
            # Initialize session
            service, session = await cls._init_session(request)

            # Update session with system prompt
            session.context['system_prompt'] = SYSTEM_PROMPT
            # Persist updated context
            # await service.session_store.save_session(session)
            logger.info(f"[SummaryHandlers] Summary text request - Model: {model_id}")

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
            logger.error(f"[SummaryHandlers] Failed to summarize text: {str(e)}", exc_info=True)
            yield f"An error occurred while summarize the text. \n str(e.detail)"
