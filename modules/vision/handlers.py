# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Tuple
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from core.integration.gen_service import GenService
from llm.model_manager import model_manager
from .prompts import VISION_SYSTEM_PROMPT


class VisionHandlers:
    """Handlers for vision analysis with streaming support"""
    
    # Shared service instance
    _service : Optional[GenService] = None

    # Cache for available models to avoid repeated API calls
    _cached_models = None

    @classmethod
    async def _get_service(cls) -> GenService:
        """Get or initialize service lazily"""
        if cls._service is None:
            logger.info("[VisionHandlers] Initializing service")
            cls._service = ServiceFactory.create_gen_service('vision')
        return cls._service

    @classmethod
    def get_available_models(cls):
        """Get list of available multimodal models with display names
        
        Returns:
            List of tuple (model_name, model_id)

        """ 
        if cls._cached_models is None:
            try:
                if models := model_manager.get_models(filter={'modality': 'vision'}):
                    # Sort models by name for consistent display
                    cls._cached_models = sorted(models, key=lambda m: m.name)
                    # logger.debug(f"Cached available multimodal models: {cls._cached_models}")              
                else:
                    logger.warning("No vision models available")
            except Exception as e:
                logger.error(f"Error getting model list: {str(e)}")
                return [], {}
        return [(f"{m.name}, {m.api_provider}", m.model_id) for m in cls._cached_models]

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
            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')
            # Get service for the selected model
            service = await cls._get_service()

            try:
                # Get or create session
                session = await service.get_or_create_session(
                    user_name=user_name,
                    module_name='vision'
                )
                logger.debug(f"[VisionHandlers] Created/retrieved session: {session.session_id}")

                # Update session with system prompt
                session.context['system_prompt'] = VISION_SYSTEM_PROMPT
                # Persist updated context
                await service.session_store.update_session(session)
                logger.debug("Updated session with vision system prompt")

                # Build content
                user_requirement = text or "Describe the media or document in detail."
                content = {
                    "text": f"<requirement>{user_requirement}</requirement>",
                    "files": [file_path]
                }
                logger.info(f"Vision analysis request - Model: {model_id}")
                logger.debug(f"Analysis content: {content}")

                # Generate streaming response
                buffered_text = ""
                async for chunk in service.gen_text_stream(
                    session=session,
                    content=content
                ):
                    buffered_text += chunk
                    yield buffered_text
                    await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo

            except Exception as e:
                logger.error(f"[VisionHandlers] Service error: {str(e)}")
                yield f"Error: {str(e)}"

        except Exception as e:
            logger.error(f"[VisionHandlers] Failed to analyze image: {str(e)}", exc_info=True)
            yield f"An error occurred while analyzing the image. \n str(e.detail)"
