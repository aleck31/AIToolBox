# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Union
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import ARCHITECT_PROMPT, CODER_PROMPT


DEV_LANGS = ["Python", "GoLang", "Rust", "Ruby", "Java", "Javascript", "Typescript", "HTML", "SQL", "Shell"]

class CodingHandlers:
    """Handlers for code generation and text formatting with streaming support"""
    
    # Shared service instance
    _service = None
    
    @classmethod
    def initialize(cls):
        """Initialize shared service if not already initialized"""
        if cls._service is None:
            cls._service = ServiceFactory.create_gen_service('coding')

    @classmethod
    async def _get_service(cls):
        """Get or initialize service"""
        if not cls._service:
            cls.initialize()
        return cls._service

    @classmethod
    async def _build_content(
        cls,
        text: str,
        language: Optional[str] = None
    ) -> Dict[str, Union[str, str]]:
        """Build content for generation"""
        return {
            "text": text,
            "language": language or "python"
        }

    @classmethod
    async def gen_code(
        cls,
        requirement: str,
        language: str,
        request: gr.Request
    ) -> AsyncIterator[tuple[str, str]]:
        """Generate code based on requirements and language
        
        Args:
            requirement: User's requirements for code generation
            language: Target programming language
            request: FastAPI request object containing session data
            
        Yields:
            Dict: Chunks of the generated response
                thinking: Architecture thinking content
                response: Generated code with explanation
        """
        try:
            # Initialize services if needed
            cls.initialize()

            # Get authenticated user from FastAPI session if available
            try:
                user_id = request.session.get('user', {}).get('username')

                # Get or create session
                session = await cls._service.get_or_create_session(
                    user_id=user_id,
                    module_name='coding'
                )
            except Exception as e:
                logger.error(f"Failed to create session: {str(e)}")
                yield ("Error initializing session", f"Error: {str(e)}")
                return

            # First phase: Architecture design
            session.context['system_prompt'] = ARCHITECT_PROMPT
            await cls._service.session_store.update_session(session, user_id)

            content = await cls._build_content(
                text=f"Provide {language} code framework architecture according to the following requirements:\n{requirement}",
                language=language
            )

            architecture_buffer = ""
            async for chunk in cls._service.gen_text_stream(
                session_id=session.session_id,
                content=content
            ):
                architecture_buffer += chunk
                yield architecture_buffer, ""
                await asyncio.sleep(0)

            # Second phase: Code generation
            session.context['system_prompt'] = CODER_PROMPT
            await cls._service.session_store.update_session(session, user_id)

            content = await cls._build_content(
                text=f"Write code according to the following instruction:\n{architecture_buffer}",
                language=language
            )

            code_buffer = ""
            async for chunk in cls._service.gen_text_stream(
                session_id=session.session_id,
                content=content
            ):
                code_buffer += chunk
                yield architecture_buffer, code_buffer
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in [gen_code]: {str(e)}")
            yield ("Error during processing", f"Error: {str(e)}")
