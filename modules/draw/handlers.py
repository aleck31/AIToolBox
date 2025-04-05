"""Handlers for the Draw module"""
import random
import re
import gradio as gr
from PIL import Image
from typing import Optional, Tuple
from core.logger import logger
from core.service.service_factory import ServiceFactory
from core.service.gen_service import GenService
from modules import BaseHandler
from .prompts import STYLE_OPTIMIZER_TEMPLATE, NEGATIVE_PROMPTS


# Preset styles for SDXL
IMAGE_STYLES = [
    "增强(enhance)", "照片(photographic)", "模拟胶片(analog-film)", "电影(cinematic)",
    "数字艺术(digital-art)",  "美式漫画(comic-book)",  "动漫(anime)", "3D模型(3d-model)", "低多边形(low-poly)",
    "线稿(line-art)", "等距插画(isometric)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",  
    "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)", "瓷砖纹理(tile-texture)"
]

IMAGE_RATIOS = ['16:9', '5:4', '3:2', '21:9', '1:1', '2:3', '4:5', '9:16', '9:21']


class DrawHandlers(BaseHandler):
    """Handlers for image generation functionality"""

    # Module name for the handler
    _module_name: str = "draw"
    
    # Service type
    _service_type: str = "draw"
    
    # Additional service for prompt optimization
    _gen_service: Optional[GenService] = None
    
    @classmethod
    async def _get_gen_service(cls) -> GenService:
        """Get or initialize gen services"""

        if cls._gen_service is None:
            logger.info("[DrawHandlers] Initializing gen service for prompt optimization")
            cls._gen_service = ServiceFactory.create_gen_service('text')
            
        return cls._gen_service

    @classmethod
    def get_available_models(cls):
        """Get list of available models with id and names"""
        try:
            # Filter for models with image output capability
            from llm.model_manager import model_manager
            if models := model_manager.get_models(filter={'category': 'image'}):
                logger.debug(f"[DrawHandlers] Get {len(models)} available image models")
                return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
            else:
                logger.warning("[DrawHandlers] No image generation models available")
                return []
        except Exception as e:
            logger.error(f"[DrawHandlers] Failed to fetch models: {str(e)}", exc_info=True)
            return []

    @classmethod
    def _random_seed(cls) -> int:
        """Generate random seed for image generation"""
        return random.randrange(1, 4294967295)  # Maximum 4294967295

    @classmethod
    async def optimize_prompt(cls, prompt: str, style: str) -> str:
        """Convert simple prompt to highly optimized version
        
        Args:
            prompt: Original text prompt
            style: Style preset name
            
        Returns:
            str: Optimized prompt for image generation
        """
        try:
            # Get services
            gen_service = await cls._get_gen_service()

            # Extract style name from parentheses
            if style:
                pattern = r'\((.*?)\)'
                style_name = re.findall(pattern, style)[0] if re.findall(pattern, style) else style
            else:
                style_name = 'enhance'

            # Validate input
            if not prompt or len(prompt.strip()) == 0:
                logger.warning("[DrawHandlers] Empty prompt received")
                return "a beautiful scene, highly detailed"

            # Get style-specific optimized template prompt
            system_prompt = STYLE_OPTIMIZER_TEMPLATE.format(style=style_name)
            optimized = await gen_service.gen_text_stateless(
                content={"text": prompt},
                system_prompt=system_prompt,
                option_params={
                    "temperature": 0.7,
                    "max_tokens": 600
                }
            )

            logger.info(f"[DrawHandlers] Optimized prompt for style: {style_name}")
            return optimized

        except Exception as e:
            logger.error(f"[DrawHandlers] Failed to optimize prompt: {str(e)}", exc_info=True)
            # Return original prompt if optimization fails
            return prompt

    @classmethod
    async def generate_image(
        cls,
        prompt: str,
        negative: str,
        ratio: str,
        seed: Optional[int] = None,
        is_random: bool = True,
        model_id: str = None,
        request: gr.Request = None
    ) -> Tuple[Image.Image, int]:
        """Generate image from text prompt
        
        Args:
            prompt: Text prompt for image generation
            negative: Negative prompt to guide generation
            ratio: Target aspect ratio (e.g. '16:9', '1:1')
            seed: Random seed for reproducibility
            is_random: Whether to use random seed
            request: Gradio request object containing session data
            
        Returns:
            Tuple[Image.Image, int]: Generated image and used seed
        """
        if not model_id:
            gr.Info("lease select a model for image generation.", duration=3)

        try:
            # Get services
            draw_service, session = await cls._init_session(request)

            # Process parameters
            used_seed = cls._random_seed() if is_random else int(seed)
            if negative:
                negative_prompts = negative
            else:
                logger.debug(f"[DrawHandlers] No negative prompts are specified, using default prompts")
                negative_prompts = NEGATIVE_PROMPTS

            # Validate aspect ratio
            if ratio not in IMAGE_RATIOS:
                logger.warning(f"[DrawHandlers] Invalid ratio {ratio}, using default 1:1")
                ratio = "1:1"

            # Generate image
            image = await draw_service.text_to_image(
                session=session,
                prompt=prompt,
                negative_prompt="\n".join(negative_prompts),
                seed=used_seed,
                aspect_ratio=ratio
            )

            return image, used_seed

        except Exception as e:
            logger.error(f"[DrawHandlers] Failed to generate image: {str(e)}", exc_info=True)
            gr.Info(f"{str(e)}", duration=3)
            return None, used_seed
