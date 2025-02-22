"""Service for AI image generation"""
import io
import json
import base64
from typing import Dict, Optional, Any
from PIL import Image
from core.logger import logger
from core.session import Session
from llm.api_providers.base import LLMConfig
from .base_service import BaseService


class DrawService(BaseService):
    """Service for AI image generation using Text-to-Image models"""

    def __init__(
        self,
        llm_config: LLMConfig,
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize draw service with model configuration"""
        super().__init__(cache_ttl=cache_ttl)  # No tools needed for image generation
        self.default_llm_config = llm_config

    async def text_to_image_stateless(
        self,
        prompt: str,
        negative_prompt: str,
        seed: int,
        aspect_ratio: str,
        option_params: Optional[Dict[str, Any]] = None
    ) -> Image.Image:
        """Generate image using the configured LLM without session context
        
        Args:
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to generate
            seed: Random seed for reproducibility
            aspect_ratio: Target aspect ratio for the image
            option_params: Optional parameters for generation
            
        Returns:
            Image.Image: Generated image
        """
        try:
            # Always use the default model for stateless operations
            llm = self._get_llm_provider(self.default_llm_config.model_id)
            
            # Prepare request body
            request_body = {
                "mode": "text-to-image",
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed if seed else 0,  # 0 for random seed
                # SD3.x specific parameters
                "aspect_ratio": aspect_ratio,
                "output_format": "png"  # explicitly set output image format (png/jpeg)
            }

            # Add optional parameters
            if option_params:
                request_body.update(option_params)

            # Generate image
            # logger.info(f"[DrawService] Generating image with model {model_id}")
            logger.debug(f"[DrawService] Request body: {json.dumps(request_body, indent=2)}")

            response = await llm.generate_content(
                request_body,
                accept="application/json",
                content_type="application/json"
            )

            if not response.content:
                raise ValueError("No response received from model")

            # Extract and log generation info
            response_body = response.content
            # Log generation metrics
            logger.debug(
                f"[DrawService] Text to Image generation completed - Seeds: {response_body.get('seeds')} - Finish reason: {response_body.get('finish_reasons')}"
            )

            # Convert base64 to image
            img_base64 = response_body["images"][0]
            return Image.open(io.BytesIO(base64.b64decode(img_base64)))

        except Exception as e:
            logger.error(f"[DrawService] Failed to generate image: {str(e)}")
            raise

    async def text_to_image(
        self,
        session: Session,
        prompt: str,
        negative_prompt: str,
        seed: int,
        aspect_ratio: str,
        option_params: Optional[Dict[str, Any]] = None
    ) -> Image.Image:
        """Generate image using the configured model
        
        Args:
            session: Active session for the request
            prompt: Text prompt for image generation
            negative_prompt: Negative prompt to guide what not to generate
            seed: Random seed for reproducibility
            aspect_ratio: Target aspect ratio for the image
            option_params: Optional parameters for generation
            
        Returns:
            Image.Image: Generated image
        """
        try:
            # Get model_id with fallback to module default if needed
            model_id = await self.get_session_model(session)
            if 'stability' not in model_id:
                raise ValueError("Please use Stability AI's SD text-to-image model")

            # Get LLM provider
            llm = self._get_llm_provider(model_id)
            
            # Prepare request body
            request_body = {
                "mode": "text-to-image",
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": seed if seed else 0,  # 0 for random seed
                # SD3.x specific parameters
                "aspect_ratio": aspect_ratio,
                "output_format": "png"  # explicitly set output image format (png/jpeg)
            }

            # Add optional parameters
            if option_params:
                request_body.update(option_params)

            # Generate image
            logger.info(f"[DrawService] Generating image with model {model_id}")
            logger.debug(f"[DrawService] Request body: {json.dumps(request_body, indent=2)}")

            response = await llm.generate_content(
                request_body,
                accept="application/json",
                content_type="application/json"
            )
            
            if not response.content:
                raise ValueError("No response received from model")
                
            # Extract and log generation info
            response_body = response.content
            # Log generation metrics
            logger.debug(
                f"[DrawService] Text to generation completed - Seeds: {response_body.get('seeds')} - Finish reason: {response_body.get('finish_reasons')}"
            )

            # Convert base64 to image
            img_base64 = response_body["images"][0]
            return Image.open(io.BytesIO(base64.b64decode(img_base64)))

        except Exception as e:
            logger.error(f"[DrawService] Failed to generate image: {str(e)}")
            raise
