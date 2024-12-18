# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
import google.generativeai as gm
from common import get_secret
from common.logger import logger
from common.llm_config import get_module_config


# gemini/getting-started guide:
# https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_python.ipynb
try:
    gemini_api_key = get_secret('dev_gemini_api').get('api_key')
except Exception as e:
    logger.warning(f"Failed to get Gemini API key from Secrets Manager: {str(e)}")
    # Fallback to environment variable
    gemini_api_key = os.getenv('GEMINI_API_KEY')
    if not gemini_api_key:
        logger.warning("No Gemini API key found in Secrets Manager or environment variables")
        raise ValueError("Gemini API key not found")


def get_generation_config(module_name: str):
    """Get Gemini generation config from module configuration"""
    gm.configure(api_key=gemini_api_key)
    config = get_module_config(module_name)
    if config and 'parameters' in config:
        params = config['parameters']
        return gm.GenerationConfig(
            max_output_tokens=int(params.get('max_tokens', 8192)),
            temperature=float(params.get('temperature', 0.9)),
            top_p=float(params.get('top_p', 0.999)),
            top_k=int(params.get('top_k', 200)),
            candidate_count=1
        )
    
    # Default configuration if no module config found
    return gm.GenerationConfig(
        max_output_tokens=8192,
        temperature=0.9,
        top_p=0.999,
        top_k=200,
        candidate_count=1
    )

# Set customize safety settings
# See https://ai.google.dev/gemini-api/docs/safety-settings
safety_settings={
    'HATE': 'BLOCK_NONE',
    'HARASSMENT': 'BLOCK_NONE',
    'SEXUAL': 'BLOCK_NONE',
    'DANGEROUS': 'BLOCK_NONE'
}
