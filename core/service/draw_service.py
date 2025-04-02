"""Service for AI image generation"""
import io
import json
import base64
from PIL import Image
from typing import Dict, Optional, Any
from core.logger import logger
from core.session import Session
from core.module_config import module_config
from llm.api_providers import LLMProviderError
from . import BaseService


class DrawService(BaseService):
    """Service for AI image generation using Text-to-Image models"""

    def __init__(
        self,
        module_name: str = 'draw',
        cache_ttl: int = 600  # 10 minutes default TTL
    ):
        """Initialize draw service
        
        Args:
            module_name: Name of the module using this service (defaults to 'draw')
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__(module_name=module_name, cache_ttl=cache_ttl)

    def _validate_model(self, model_id: str) -> None:
        """Validate model is a Stability AI model
        
        Args:
            model_id: Model ID to validate
            
        Raises:
            ValueError: If model is not a Stability AI model
        """
        if not model_id or 'stability' not in model_id:
            raise ValueError("Please use Stability AI's SD text-to-image model")

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
            # Get default model from module config
            model_id = module_config.get_default_model(self.module_name)
            if not model_id:
                raise ValueError(f"No default model configured for {self.module_name}")
            
            # Validate model is Stability AI
            self._validate_model(model_id)
            
            # Get provider with module's default configuration
            provider = self._get_llm_provider(model_id)
            
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

            response = await provider.generate_content(
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

        except LLMProviderError as e:
            # Log and re-raise LLM errors
            logger.error(f"[DrawService] Failed to generate image: {e.error_code}")
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
            # Get model_id with fallback to module default
            model_id = await self.get_session_model(session)
            
            # Validate model is Stability AI
            self._validate_model(model_id)

            # Get LLM provider
            provider = self._get_llm_provider(model_id)
            
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

            response = await provider.generate_content(
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

        except LLMProviderError as e:
            # Log and re-raise LLM errors
            logger.error(f"[DrawService] Failed to generate image: {e.error_code}")
            raise
