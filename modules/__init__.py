# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from typing import Optional, Any, Union
from core.logger import logger
from core.service.service_factory import ServiceFactory
from core.service.chat_service import ChatService
from core.service.gen_service import GenService
from core.service.draw_service import DrawService


class BaseHandler:
    """Base handler class with common model selection functionality"""
    
    # Shared service instances
    _service: Optional[Union[ChatService, DrawService, GenService]] = None
    
    # Module name for the handler
    _module_name: str = "base"
    
    # Service type (default to GenService)
    _service_type: str = "gen"
    
    @classmethod
    async def _get_service(cls) -> Union[ChatService, DrawService, GenService]:
        """Get or initialize service lazily based on service type"""
        if cls._service is None:
            logger.info(f"[{cls.__name__}] Initializing {cls._service_type} service")
            
            if cls._service_type == "chat":
                cls._service = ServiceFactory.create_chat_service(cls._module_name)
            elif cls._service_type == "draw":
                cls._service = ServiceFactory.create_draw_service(cls._module_name)
            else:  # Default to general service
                cls._service = ServiceFactory.create_gen_service(cls._module_name)

        return cls._service

    @classmethod
    async def _init_session(cls, request: gr.Request):
        """Initialize service and session
        
        A helper method to get both service and session in one call,
        reducing code duplication across handler methods.
        
        Args:
            request: Gradio request with session data
            
        Returns:
            Tuple containing:
            - Service instance (ChatService, DrawService, or GenService)
            - Session object for the current user and module
        """
        service = await cls._get_service()
        # Get authenticated user from FastAPI session
        if user_name := request.session.get('user', {}).get('username'):
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name=cls._module_name
            )
            return service, session
        else:
            logger.warning(f"[{cls.__name__}] No authenticated user for loading model")
            return service, None

    @classmethod
    async def update_model_id(cls, model_id: str, request: gr.Request = None):
        """Update session model when dropdown selection changes"""
        try:
            # Initialize service and session
            service, session = await cls._init_session(request)

            # Update model and log
            logger.debug(f"[{cls.__name__}] Updating session model to: {model_id}")
            await service.update_session_model(session, model_id)

        except Exception as e:
            logger.error(f"[{cls.__name__}] Failed updating session model: {str(e)}", exc_info=True)
            
    @classmethod
    async def get_model_id(cls, request: gr.Request = None):
        """Get selected model id from session"""
        try:
            # Initialize service and session
            service, session = await cls._init_session(request)

            # Get current model id from session
            model_id = await service.get_session_model(session)
            logger.debug(f"[{cls.__name__}] Get model {model_id} from session")

            # Return model_id for selected value
            return model_id

        except Exception as e:
            logger.error(f"[{cls.__name__}] Failed loading selected model: {str(e)}", exc_info=True)
            return None
