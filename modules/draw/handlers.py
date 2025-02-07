"""Handlers for the Draw module"""
import random
import re
from typing import Optional, Tuple
from PIL import Image
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from .prompts import STYLE_OPTIMIZER_TEMPLATE, NEGATIVE_PROMPTS


# preset style for SDXL
IMAGE_STYLES = [
    "增强(enhance)", "照片(photographic)", "模拟胶片(analog-film)", "电影(cinematic)",
    "数字艺术(digital-art)",  "美式漫画(comic-book)",  "动漫(anime)", "3D模型(3d-model)", "低多边形(low-poly)",
    "线稿(line-art)", "等距插画(isometric)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",  
    "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)", "瓷砖纹理(tile-texture)"
]

IMAGE_RATIOS = ['16:9', '5:4', '3:2', '21:9', '1:1', '2:3', '4:5', '9:16', '9:21']


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
    async def optimize_prompt(cls, prompt: str, style: str,) -> str:
        """Convert simple Stable Diffusion prompt to a highly optimized prompt

        Args:
            prompt: The original text prompt for image generation        
            style: Style preset for generation
        """
        try:
            # Get services (initializes lazily if needed)
            _, gen_service = await cls._get_services()

            # Extract style name from parentheses if present
            if style:
                pattern = r'\((.*?)\)'
                style_name = re.findall(pattern, style)[0] if re.findall(pattern, style) else style
            else:
                style_name = 'enhance'

            # Validate input prompt
            if not prompt or len(prompt.strip()) == 0:
                logger.warning("Empty prompt received")
                return "a beautiful scene, highly detailed"

            # Use style-specific template for optimization
            system_prompt = STYLE_OPTIMIZER_TEMPLATE.format(style=style_name)
            
            # Use gen_service for prompt optimization
            optimized_prompt = await gen_service.gen_text_stateless(
                content={"text": prompt},
                system_prompt=system_prompt,
                option_params={
                    "temperature": 0.7,
                    "max_tokens": 600
                }
            )

            logger.info(f"Successfully optimized prompt for style: {style_name}")
            return optimized_prompt

        except Exception as e:
            logger.error(f"Error optimizing prompt: {str(e)}")
            # Return original prompt if optimization fails
            return prompt

    @classmethod
    async def generate_image(
        cls,
        prompt: str,
        negative: str,
        ratio: str,
        seed: Optional[int] = None,
        is_random: bool = True
    ) -> Tuple[Image.Image, int]:
        """Generate image from text prompt
        
        Args:
            prompt: Text prompt for image generation
            negative: Negative prompt to guide what not to generate
            ratio: The aspect ratio of the generated image
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

            # Add negative prompt to defaults
            negative_prompts = NEGATIVE_PROMPTS.copy()
            if negative:
                negative_prompts.append(negative)

            # Get model parameters from module config
            # params = module_config.get_inference_params('draw') or {}
            
            # Generate image using non-streaming method for Stable Diffusion
            image = await draw_service.text_to_image(
                prompt=prompt,
                negative_prompt="\n".join(negative_prompts),
                seed=used_seed,
                aspect_ratio=ratio, # Let model handle dimensions based on aspect_ratio
            )

            return image, used_seed

        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            raise
