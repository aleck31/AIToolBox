# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Tuple
from fastapi import HTTPException
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from llm.model_manager import model_manager
from .prompts import VISION_SYSTEM_PROMPT


class VisionHandlers:
    """Handlers for vision analysis with streaming support"""
    
    # Shared service instances for different models
    _services: Dict[str, 'ServiceFactory.GenService'] = {}

    # Cache for available models to avoid repeated API calls
    _cached_models = None

    @classmethod
    def initialize(cls, model_id: str) -> None:
        """Initialize shared service if not already initialized for the model
        
        Args:
            model_id: The model identifier to initialize service for
        """
        model_id = model_id.lower()
        if model_id not in cls._services:
            logger.info(f"Initializing vision service for model: {model_id}")
            cls._services[model_id] = ServiceFactory.create_gen_service('vision')

    @classmethod
    async def _get_service(cls, model_id: str) -> 'ServiceFactory.GenService':
        """Get or initialize service for specified model
        
        Args:
            model_id: The model identifier to get service for
            
        Returns:
            The service instance for the specified model
        """
        model_id = model_id.lower()
        if model_id not in cls._services:
            cls.initialize(model_id)
        return cls._services[model_id]

    @classmethod
    def get_available_models(cls) -> Tuple[List[str], Dict[str, str]]:
        """Get list of available multimodal models with display names
        
        Returns:
            Tuple containing:
            - List of model display names for UI
            - Dict mapping display names to model IDs
        """
        if cls._cached_models is None:
            cls._cached_models = model_manager.get_models(filter={'type': 'vision'})
            # logger.debug(f"Cached available multimodal models: {cls._cached_models}")
            
        if not cls._cached_models:
            return [], {}
            
        # Create mapping of display names to model IDs
        model_map = {
            f"{model.name} ({model.api_provider})": model.model_id 
            for model in cls._cached_models
        }
        return list(model_map.keys()), model_map

    @classmethod
    async def analyze_image(
        cls,
        file_path: str,
        text: Optional[str],
        model_display_name: str,
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
            
        if not model_display_name:
            yield "Please select a model for analysis."
            return
            
        # Get model ID from display name
        _, model_map = cls.get_available_models()
        model_id = model_map.get(model_display_name)
        if not model_id:
            yield f"Selected model is not available for vision analysis."
            return
        
        try:
            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')

            # Get service for the selected model
            service = await cls._get_service(model_id)
            logger.debug(f"Using vision service for model: {model_id}")
            
            # Get or create session
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='vision'
            )
            logger.debug(f"Created/retrieved session: {session.session_id}")

            # Update session with system prompt
            session.context['system_prompt'] = VISION_SYSTEM_PROMPT
            # Persist updated context
            await service.session_store.update_session(session, user_name)
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
                session_id=session.session_id,
                content=content
            ):
                buffered_text += chunk
                yield buffered_text
                await asyncio.sleep(0)  # Add sleep for Gradio UI streaming echo
        except HTTPException as e:
            error_msg = f"Authentication error: {e.detail}"
            logger.error(error_msg)
            yield error_msg
        except Exception as e:
            error_msg = f"Error during vision analysis: {str(e)}"
            logger.error(error_msg)
            yield "An error occurred while analyzing the content. Please try again or contact support if the issue persists."
