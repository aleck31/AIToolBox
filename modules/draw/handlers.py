"""Handlers for the Draw module"""
import random
import re
import gradio as gr
from typing import Optional, Tuple
from PIL import Image
from core.logger import logger
from core.service.service_factory import ServiceFactory
from core.service.draw_service import DrawService
from core.service.gen_service import GenService
from core.module_config import module_config
from .prompts import STYLE_OPTIMIZER_TEMPLATE, NEGATIVE_PROMPTS


# Preset styles for SDXL
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
    _draw_service: Optional[DrawService] = None
    _gen_service: Optional[GenService] = None

    @classmethod
    def _get_services(cls) -> Tuple[DrawService, GenService]:
        """Get or initialize services"""
        if cls._draw_service is None:
            logger.info("[DrawHandlers] Initializing services")
            cls._draw_service = ServiceFactory.create_draw_service('draw')
            cls._gen_service = ServiceFactory.create_gen_service(
                module_name = 'draw', 
                # Initialize gen service using claude 3.7
                model_id = 'us.anthropic.claude-3-7-sonnet-20250219-v1:0'
            )
        return cls._draw_service, cls._gen_service

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
            _, gen_service = cls._get_services()

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
        try:
            # Get services
            draw_service, _ = cls._get_services()

             # Get authenticated user from FastAPI request
            user_name = request.session.get('user', {}).get('username')

            try:
                # Get active session
                session = await draw_service.get_or_create_session(
                    user_name=user_name,
                    module_name='draw'
                )

                # Process parameters
                used_seed = cls._random_seed() if is_random else int(seed)
                negative_prompts = NEGATIVE_PROMPTS.copy()
                if negative:
                    negative_prompts.append(negative)

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
                logger.error(f"[DrawHandlers] Service error: {str(e)}")
                return None, used_seed

        except Exception as e:
            logger.error(f"[DrawHandlers] Failed to generate image: {str(e)}", exc_info=True)
            raise
