"""Tools for image generation"""
import time
import random
from pathlib import Path
from typing import Dict
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from core.module_config import module_config
from modules.draw.prompts import NEGATIVE_PROMPTS


async def generate_image(
    prompt: str,
    negative_prompt: str = '',
    aspect_ratio: str = '16:9',
    **kwargs  # Handle any additional parameters from the schema
) -> Dict:
    """Generate an image from text description
    
    Args:
        prompt: Text description of the image to generate
        negative_prompt: Optional text describing what to avoid
        aspect_ratio: The aspect ratio of the generated image
        
    Returns:
        Dict containing base64 encoded image and metadata
    """
    try:
        # Initialize draw service
        draw_service = ServiceFactory.create_draw_service(
            module_name = 'draw', 
            # use draw module's default model
            model_id = module_config.get_default_model('draw')
        )

        # Add negative prompt to defaults
        negative_prompts = NEGATIVE_PROMPTS.copy()
        if negative_prompt:
            negative_prompts.append(negative_prompt)

        # Validate prompt
        if not prompt:
            raise ValueError("Prompt is required")

        # Generate a random seed for reproducibility
        used_seed = random.randrange(0, 4294967295)

        # Generate image with dimensions
        image = await draw_service.text_to_image_stateless(
            prompt=prompt,
            negative_prompt="\n".join(negative_prompts),
            seed=used_seed,
            aspect_ratio=aspect_ratio
        )

        # Save to project's assets directory
        images_dir = Path("assets/generated/images")
        images_dir.mkdir(parents=True, exist_ok=True)

        # Create a unique filename with timestamp and seed
        timestamp = int(time.time())
        filename = f"img_{timestamp}_{used_seed}.png"
        file_path = images_dir / filename

        # Save the image
        image.save(file_path, format="PNG")

        # Return the file path for Gradio to serve
        return {
            "image": image,
            "metadata": {
                "seed": used_seed,
                "aspect_ratio": aspect_ratio,
                "file_path": str(file_path)
            }
        }
        
    except ValueError as e:
        logger.error(f"[Tool] Validation error in generate_image tool: {str(e)}")
        return {"error": f"Validation error: {str(e)}"}
    except TypeError as e:
        logger.error(f"[Tool] Type error in generate_image tool: {str(e)}")
        return {"error": f"Type error: {str(e)}"}
    except IOError as e:
        logger.error(f"[Tool] I/O error in generate_image tool: {str(e)}")
        return {"error": f"Failed to save image: {str(e)}"}
    except Exception as e:
        logger.error(f"[Tool] Unexpected error in generate_image tool: {str(e)}")
        return {"error": f"An unexpected error occurred: {str(e)}"}


# Tool specifications in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "generate_image",
            "description": "Generate image from a text description using Stable Diffusion model.",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Stable Diffusion prompt written in English that specifies the content and style for the generated image."
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "Optional keywords of what you do not wish to see in the output image",
                            "default": ""
                        },
                        "aspect_ratio": {
                            "type": "string",
                            "description": "Desired aspect ratio in 'width:height' format (e.g., '16:9', '5:4', '3:2', '21:9', '1:1', '2:3', '4:5', '9:16', '9:21'). If provided, height will be calculated based on the width.",
                            "default": '16:9'
                        }
                    },
                    "required": ["prompt"]
                }
            }
        }
    }
]
