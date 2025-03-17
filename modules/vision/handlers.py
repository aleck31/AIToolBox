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

    @classmethod
    async def _get_service(cls) -> GenService:
        """Get or initialize service lazily"""
        if cls._service is None:
            logger.info("[VisionHandlers] Initializing service")
            cls._service = ServiceFactory.create_gen_service('vision')
        return cls._service

    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Filter for models with vision capability
            if models := model_manager.get_models(filter={'category': 'vision'}):
                logger.debug(f"[VisionHandlers] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[VisionHandlers] No vision-capable models available")
                return []
        except Exception as e:
            logger.error(f"[VisionHandlers] Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    async def update_model_id(cls, model_id: str, request: gr.Request = None):
        """Update session model when dropdown selection changes"""
        try:
            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')
            if not user_name:
                logger.warning("[VisionHandlers] No authenticated user for model update")
                return

            service = await cls._get_service()
            # Get active session
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='vision'
            )
            
            # Update model and log
            await service.update_session_model(session, model_id)
            logger.debug(f"[VisionHandlers] Updating session model to: {model_id}")

        except Exception as e:
            logger.error(f"[VisionHandlers] Failed updating session model: {str(e)}", exc_info=True)

    @classmethod
    async def get_model_id(cls, request: gr.Request = None):
        """Get selected model id from session"""
        try:
            # Get authenticated user from FastAPI session
            if user_name := request.session.get('user', {}).get('username'):

                service = await cls._get_service()
                # Get active session
                session = await service.get_or_create_session(
                    user_name=user_name,
                    module_name='vision'
                )
                
                # Get current model id from session
                model_id = await service.get_session_model(session)
                logger.debug(f"[VisionHandlers] Loaded model {model_id} from session")
                
                # Return model_id for selected value
                return model_id
                # gr.Dropdown(choices=cls.get_available_models())   # Return dropdown with current choices and selected value

            else:
                logger.warning("[VisionHandlers] No authenticated user for loading model")
                return None

        except Exception as e:
            logger.error(f"[VisionHandlers] Failed loading selected model: {str(e)}", exc_info=True)
            return None

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
