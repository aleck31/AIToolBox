# Copyright iX.
# SPDX-License-Identifier: MIT-0
import asyncio
import gradio as gr
from typing import Dict, Optional, AsyncIterator, Union
from core.logger import logger
from llm.model_manager import model_manager
from modules import BaseHandler
from .prompts import ARCHITECT_PROMPT, CODER_PROMPT


DEV_LANGS = ["Python", "GoLang", "Rust", "Ruby", "Java", "Javascript", "Typescript", "HTML", "SQL", "Shell"]

class CodingHandlers(BaseHandler):
    """Handlers for code generation with streaming support"""
    
    # Module configuration
    _module_name = "coding"
    _service_type = "gen"
    
    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Filter for models with text generation capability
            if models := model_manager.get_models(filter={'api_provider': 'Bedrock'}):
                logger.debug(f"[CodingHandlers] Get {len(models)} available models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[CodingHandlers] No text-capable models available")
                return []
        except Exception as e:
            logger.error(f"[CodingHandlers] Failed to fetch models: {str(e)}", exc_info=True)
            return []


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
            # await service.session_store.save_session(session)
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
            # await service.session_store.save_session(session)
            
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
