"""Handlers for the Draw module"""
import random
import re
from typing import Optional, Tuple
from PIL import Image

from core.logger import logger
from core.module_config import module_config
from core.integration.service_factory import ServiceFactory
from llm.api_providers.base import LLMConfig
from .prompts import PROMPT_OPTIMIZER_SYSTEM, NEGATIVE_PROMPTS


class DrawHandlers:
    """Handlers for image generation functionality"""

    def __init__(self):
        """Initialize draw handlers with required services"""
        # Get model configs
        draw_model_id = module_config.get_default_model('draw')
        text_model_id = module_config.get_default_model('text')

        # Initialize services using factory
        self.draw_service = ServiceFactory.create_draw_service('draw')    # Draw service for image generation
        self.gen_service = ServiceFactory.create_gen_service('draw')    # Gen service for prompt optimization

    def _random_seed(self) -> int:
        """Generate random seed for image generation"""
        # Maximum 4294967295
        return random.randrange(1, 4294967295)

    async def optimize_prompt(self, prompt: str) -> str:
        """Convert simple Stable Diffusion prompt to a highly optimized prompt"""
        try:
            # Use gen_service for prompt optimization
            optimized = await self.gen_service.gen_text_stateless(
                content={"text": prompt},
                system_prompt=PROMPT_OPTIMIZER_SYSTEM
            )
            return optimized

        except Exception as e:
            logger.error(f"Error optimizing prompt: {str(e)}")
            # Return original prompt if optimization fails
            return prompt

    async def generate_image(
        self,
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
            # Process seed
            seed = self._random_seed() if is_random else int(seed)

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

            # Generate image
            image, used_seed = await self.draw_service.gen_image_stream(
                prompt=prompt,
                negative_prompt="\n".join(negative_prompts),
                style=style,
                steps=steps,
                seed=seed
            )

            return image, used_seed

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise
