# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Optional, AsyncIterator
from core.logger import logger
from llm.model_manager import model_manager
from modules import BaseHandler
from .prompts import VISION_SYSTEM_PROMPT


class VisionHandlers(BaseHandler):
    """Handlers for vision analysis with streaming support"""
    
    # Module configuration
    _module_name = "vision"
    _service_type = "gen"
    
    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Override to filter for models with vision capability
            if models := model_manager.get_models(filter={'category': 'vision'}):
                logger.debug(f"[{cls.__name__}] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning(f"[{cls.__name__}] No vision-capable models available")
                return []
        except Exception as e:
            logger.error(f"[{cls.__name__}] Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    async def analyze_image(
        cls,
        file_path: str,
        text: Optional[str],
        model_id: str,
        request: gr.Request
    ) -> AsyncIterator[str]:
        """Generate vision analysis using specified model with streaming response
        
        Args:
            file_path: Path to the image file
            text: Optional specific analysis requirement
            model_id: Model to use (e.g., 'anthropic.claude-3-5-sonnet-20241022-v2:0' or 'gemini-1.5-pro')
            
        Yields:
            str: Chunks of the analysis result
        """
        # Input validation
        if not file_path:
            yield "Please provide an image or document to analyze."
            return
            
        if not model_id:
            yield "Please select a model for analysis."
            return
        
        try:
            # Initialize session
            service, session = await cls._init_session(request)
 
            # Update session with system prompt
            session.context['system_prompt'] = VISION_SYSTEM_PROMPT
            # Persist updated context
            # await service.session_store.save_session(session)
            logger.info(f"[VisionHandlers] Vision analysis request - Model: {model_id}")

            # Build content
            user_requirement = text or "Describe the media or document in detail."
            content = {
                "text": f"<requirement>{user_requirement}</requirement>",
                "files": [file_path]
            }
            logger.debug(f"[VisionHandlers] Analysis content: {content}")

            # Generate streaming response
            buffered_text = ""
            async for chunk in service.gen_text_stream(
                session=session,
                content=content
            ):
                # Handle structured chunks from GenService
                if isinstance(chunk, dict):
                    # Only process text content (ignore thinking content)
                    if text := chunk.get('text'):
                        buffered_text += text
                        yield buffered_text
                else:
                    # Legacy format handling (string chunks)
                    buffered_text += chunk
                    yield buffered_text
                
                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

        except Exception as e:
            logger.error(f"[VisionHandlers] Failed to analyze image: {str(e)}", exc_info=True)
            yield f"An error occurred while analyzing the image. \n str(e.detail)"
