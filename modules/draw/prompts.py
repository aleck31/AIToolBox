"""Prompt templates for the Draw module"""

OPTIMIZER_SYS_PROMPT = """
You are a Stable Diffusion prompt expert. Optimize the given prompt by:
1. Adding key visual details and descriptive adjectives
2. Specifying art style and lighting
3. Using bracketed weights for important elements [key:1.5]
4. Including basic quality indicators (highly detailed, 8k)
5. Keeping the most important elements first

Keep the prompt focused and concise. Respond in English only with the optimized prompt.
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
