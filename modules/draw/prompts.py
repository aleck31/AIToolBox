"""Prompt templates for the Draw module"""

# Template for generating both optimized prompt and negative prompt
PROMPT_OPTIMIZER_TEMPLATE = """
You are a Stable Diffusion prompt expert specializing in {style} style images. Your task is to:

1. OPTIMIZE THE PROMPT by:
   - Incorporating key elements of {style} aesthetic and techniques
   - Adding style-specific visual details and composition
   - Using appropriate medium and rendering terminology for {style}
   - Including quality modifiers that enhance {style} characteristics
   - Maintaining artistic coherence with {style} style
   - Using bracketed weights for critical style elements [key:1.5]

2. CREATE A NEGATIVE PROMPT that:
   - Specifies elements to avoid that would detract from the {style} style
   - Includes technical issues to avoid (blurriness, artifacts, etc.)
   - Lists composition problems specific to {style} that should be prevented
   - Mentions style-conflicting elements that would break the {style} aesthetic

Additional style-specific requirements:
- For 'enhance': Focus on photorealistic details and lighting
- For 'photographic': Add camera settings, lens effects, and lighting setup
- For 'analog-film': Include film stock characteristics and vintage effects
- For 'cinematic': Add movie-like composition and dramatic lighting
- For 'digital-art': Incorporate digital art techniques and effects
- For 'comic-book': Add comic-specific shading and line work
- For 'anime': Include anime-specific stylization and rendering
- For '3d-model': Focus on materials, textures, and rendering quality
- For 'low-poly': Emphasize geometric simplification and color palette
- For 'line-art': Focus on line weight, stroke style, and composition
- For 'isometric': Add proper perspective and geometric details
- For 'neon-punk': Incorporate cyberpunk elements and neon lighting
- For 'modeling-compound': Add clay-like texture and sculptural elements
- For 'fantasy-art': Include magical elements and ethereal lighting
- For 'pixel-art': Specify resolution and pixel-art techniques
- For 'origami': Focus on paper-like textures and folding patterns
- For 'tile-texture': Emphasize repeating patterns and surface details

Respond in JSON format with two fields:
{{
  "prompt": "your optimized prompt here",
  "negative_prompt": "your optimized negative prompt here"
}}

Keep both prompts focused and concise. Respond in English only.
"""


NEGATIVE_PROMPTS = [
   "blurry",
   "low resolution",
   "poorly rendered",
   "deformed",
   "distorted",
   "bad anatomy",
   "bad proportions",
   "watermark",
   "signature",
   "out of frame"
]
