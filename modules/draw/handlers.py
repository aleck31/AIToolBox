"""Handlers for the Draw module"""
import random
import re
from typing import Optional, Tuple
from PIL import Image

from core.logger import logger
from core.module_config import module_config
from core.integration.service_factory import ServiceFactory
from llm.api_providers.base import LLMConfig
from .prompts import OPTIMIZER_SYS_PROMPT, NEGATIVE_PROMPTS


class DrawHandlers:
    """Handlers for image generation functionality"""

    # Shared service instances
    _draw_service = None
    _gen_service = None

    @classmethod
    async def _get_services(cls):
        """Get or initialize services lazily"""
        if cls._draw_service is None:
            # Get model configs
            # draw_model_id = module_config.get_default_model('draw')
            # text_model_id = module_config.get_default_model('text')

            # Initialize services using factory
            cls._draw_service = ServiceFactory.create_draw_service('draw')    # Draw service for image generation
            cls._gen_service = ServiceFactory.create_gen_service('text')    # Gen service for prompt optimization
        return cls._draw_service, cls._gen_service

    @classmethod
    def _random_seed(cls) -> int:
        """Generate random seed for image generation"""
        # Maximum 4294967295
        return random.randrange(1, 4294967295)

    @classmethod
    async def optimize_prompt(cls, prompt: str) -> str:
        """Convert simple Stable Diffusion prompt to a highly optimized prompt"""
        try:
            # Get services (initializes lazily if needed)
            _, gen_service = await cls._get_services()

            # Use gen_service for prompt optimization
            optimized_prompt = await gen_service.gen_text_stateless(
                content={"text": prompt},
                system_prompt=OPTIMIZER_SYS_PROMPT,
                option_params={"temperature": 0.7}  # Add some creativity while keeping coherence
            )
            # Return original prompt if optimization returns empty
            return optimized_prompt if optimized_prompt else prompt

        except Exception as e:
            logger.error(f"Error optimizing prompt: {str(e)}")
            # Return original prompt if optimization fails
            return prompt

    @classmethod
    async def generate_image(
        cls,
        prompt: str,
        negative: str = "",
        style: str = "",
        steps: int = 50,
        seed: Optional[int] = None,
        is_random: bool = True
    ) -> Tuple[Image.Image, int]:
        """Generate image from text prompt
        
        Args:
            prompt: Text prompt for image generation
            negative: Negative prompt to guide what not to generate
            style: Style preset for generation
            steps: Number of diffusion steps
            seed: Random seed for reproducibility
            is_random: Whether to use random seed
            
        Returns:
            Tuple[Image.Image, int]: Generated image and used seed
        """
        try:
            # Get services (initializes lazily if needed)
            draw_service, _ = await cls._get_services()

            # Process seed
            used_seed = cls._random_seed() if is_random else int(seed)

            # Extract style from parentheses if present
            if style:
                pattern = r'\((.*?)\)'
                style = re.findall(pattern, style)[0]
            else:
                style = 'enhance'

            # Add negative prompt to defaults
            negative_prompts = NEGATIVE_PROMPTS.copy()
            if negative:
                negative_prompts.append(negative)

            # Generate image using non-streaming method for Stable Diffusion
            image = await draw_service.gen_image(
                prompt=prompt,
                negative_prompt="\n".join(negative_prompts),
                seed=used_seed,
                style=style,
                steps=steps
            )

            return image, used_seed

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise
