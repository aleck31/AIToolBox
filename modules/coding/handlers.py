# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, List, Union
from core.logger import logger
from core.service.service_factory import ServiceFactory
from .prompts import ARCHITECT_PROMPT, CODER_PROMPT


DEV_LANGS = ["Python", "GoLang", "Rust", "Ruby", "Java", "Javascript", "Typescript", "HTML", "SQL", "Shell"]

class CodingHandlers:
    """Handlers for code generation with streaming support"""
    
    # Shared service instance
    _service = None
    
    @classmethod
    async def _get_service(cls):
        """Get or initialize service lazily"""
        if cls._service is None:
            cls._service = ServiceFactory.create_gen_service('coding')
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
    async def _init_session(cls, request: gr.Request):
        """Initialize service and session"""
        service = await cls._get_service()
        user_name = request.session.get('user', {}).get('username')
        
        session = await service.get_or_create_session(
            user_name=user_name,
            module_name='coding'
        )
        
        return service, session

    @classmethod
    async def design_arch(
        cls,
        requirement: str,
        language: str,
        request: gr.Request
    ) -> AsyncIterator[str]:
        """Generate architecture design
        
        Args:
            requirement: User's requirements
            language: Target programming language
            request: FastAPI request object
        """
        try:
            # Initialize session
            service, session = await cls._init_session(request)
            
            # Phase 1: Architecture design
            session.context['system_prompt'] = ARCHITECT_PROMPT
            await service.session_store.save_session(session)            
            content = await cls._build_content(
                text=f"Analyze and provide {language} architecture design for:\n{requirement}",
                language=language
            )

            # Stream architecture content
            arch_buffer = ""
            async for chunk in service.gen_text_stream(
                session=session,
                content=content
            ):
                arch_buffer += chunk
                yield arch_buffer
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in [design_arch]: {str(e)}")
            yield f"Error during processing: {str(e)}"

    @classmethod
    async def gen_code(
        cls,
        architecture: str,
        language: str,
        request: gr.Request
    ) -> AsyncIterator[str]:
        """Generate implementation code
        
        Args:
            architecture: Architecture design to implement
            language: Target programming language
            request: FastAPI request object
        """
        try:
            # Initialize session
            service, session = await cls._init_session(request)
            
            # Phase 2: code generation
            session.context['system_prompt'] = CODER_PROMPT
            await service.session_store.save_session(session)
            
            content = await cls._build_content(
                text=f"Implement the solution based on this architecture:\n{architecture}",
                language=language
            )

            code_buffer = ""
            async for chunk in service.gen_text_stream(
                session=session,
                content=content
            ):
                code_buffer += chunk
                yield code_buffer
                await asyncio.sleep(0)

        except Exception as e:
            logger.error(f"Error in [gen_code]: {str(e)}")
            yield f"Error during processing: {str(e)}"
