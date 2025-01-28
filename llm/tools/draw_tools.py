"""Tools for image generation"""
import random
import tempfile
from typing import Dict, Optional
from core.logger import logger
from core.integration.service_factory import ServiceFactory
from modules.draw.prompts import NEGATIVE_PROMPTS


async def generate_image(
    prompt: str,
    negative_prompt: str = "",
    style: str = "enhance",
    steps: int = 50,
    **kwargs  # Handle any additional parameters from the schema
) -> Dict:
    """Generate an image from text description
    
    Args:
        prompt: Text description of the image to generate
        negative_prompt: Optional text describing what to avoid
        style: Style preset for generation
        steps: Number of diffusion steps
        
    Returns:
        Dict containing base64 encoded image and metadata
    """
    try:
        # Get draw service instance
        draw_service = ServiceFactory.create_draw_service('draw')
        
        # Add negative prompt to defaults
        negative_prompts = NEGATIVE_PROMPTS.copy()
        if negative_prompt:
            negative_prompts.append(negative_prompt)
        
        # Ensure English prompt
        if not prompt:
            raise ValueError("Prompt is required")
        
        used_seed=random.randrange(1, 4294967295)

        # Generate image
        image = await draw_service.gen_image(
            prompt=prompt,
            negative_prompt="\n".join(negative_prompts),
            seed=used_seed,
            style=style or "enhance",  # Use default if not provided
            steps=min(max(steps or 50, 20), 50)  # Clamp between 20-50
        )
        
        # Save image to a temporary file that Gradio can serve
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        image.save(temp_file.name, format="PNG")
        temp_file.close()
        
        # Return the file path for Gradio to serve
        return {
            "file_path": temp_file.name,
            "metadata": {
                "seed": used_seed,
                "steps": steps,
                "style": style
            }
        }
        
    except Exception as e:
        logger.error(f"Error in generate_image tool: {str(e)}")
        return {"error": str(e)}


# Tool specifications in Bedrock format
list_of_tools_specs = [
    {
        "toolSpec": {
            "name": "generate_image",
            "description": "Generate an image from a text description using AI",
            "inputSchema": {
                "json": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "Text description written in English that explains the visual elements for the image to be generated"
                        },
                        "negative_prompt": {
                            "type": "string",
                            "description": "Optional text describing what to avoid in the image",
                            "default": ""
                        },
                        "style": {
                            "type": "string",
                            "description": "Optional style preset (Enum: enhance, photographic, digital-art, 3d-model, analog-film, animé, cinematic, comic-book, fantasy-art, isometric, line-art, low-poly, modeling-compound, neon-punk, origami, pixel-art, tile-texture)",
                            "default": "enhance"
                        },
                        "steps": {
                            "type": "integer",
                            "description": "Number of diffusion steps (20-50)",
                            "default": 50,
                            "minimum": 20,
                            "maximum": 50
                        }
                    },
                    "required": ["prompt"]
                }
            }
        }
    }
]
