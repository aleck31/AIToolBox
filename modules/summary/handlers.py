# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Optional, AsyncIterator
from core.logger import logger
from core.service.service_factory import ServiceFactory
from core.service.gen_service import GenService
from llm.model_manager import model_manager
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
    async def update_model_id(cls, model_id: str, request: gr.Request = None):
        """Update session model when dropdown selection changes"""
        try:
            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')
            if not user_name:
                logger.warning("[SummaryHandlers] No authenticated user for model update")
                return

            service = await cls._get_service()
            # Get active session
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='summary'
            )
            
            # Update model and log
            logger.debug(f"[SummaryHandlers] Updating session model to: {model_id}")
            await service.update_session_model(session, model_id)

        except Exception as e:
            logger.error(f"[SummaryHandlers] Failed updating session model: {str(e)}", exc_info=True)

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
                    module_name='summary'
                )
                
                # Get current model id from session
                model_id = await service.get_session_model(session)
                logger.debug(f"[SummaryHandlers] Get model {model_id} from session")
                
                # Return model_id for selected value
                return model_id

            else:
                logger.warning("[SummaryHandlers] No authenticated user for loading model")
                return None

        except Exception as e:
            logger.error(f"[SummaryHandlers] Failed loading selected model: {str(e)}", exc_info=True)
            return None

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
            # Get service (initializes lazily if needed)
            service = await cls._get_service()

            # Get authenticated user from FastAPI session
            user_name = request.session.get('user', {}).get('username')

            # Get or create session
            session = await service.get_or_create_session(
                user_name=user_name,
                module_name='summary'
            )

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
