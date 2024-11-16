# Copyright iX.
# SPDX-License-Identifier: MIT-0
from common import USER_CONF
from utils import format_msg
from llm import bedrock_stream
from common.logger import logger
from common.llm_config import get_module_config
from .prompts import system_prompt

inference_params = {
    "maxTokens": 4096,
    "temperature": 0.7,
    "topP": 0.8,
    "stopSequences": ["end_turn"]
}

additional_model_fields = {
    "top_k": 10
}

def gen_with_think(input_data):
    """
    Generate a response based on text description and optional files
    Args:
    - input_data: user's input from MultimodalTextbox (can contain text and files)
    """
    if not input_data:
        return "Please provide some input (text or files)."

    try:
        # Split text and files from input_data
        if isinstance(input_data, str):
            text = input_data
            files = []
        else:
            text = input_data.get("text", "")
            files = input_data.get("files", [])

        logger.debug(f"Input request - Text: {text}, Files: {files}")

        # Create message dictionary for format_msg
        message = {
            "text": text,
            "files": files if files else []
        }

        # Format the user message
        formatted_msg = format_msg(message, 'user')

        # Get module configuration
        module_config = get_module_config('oneshot')
        if not module_config:
            logger.error("Failed to get oneshot module configuration")
            return "Error: Could not load module configuration"

        # Get model ID from module configuration
        model_id = module_config.get('default_model')
        if not model_id:
            logger.error("No default model configured for oneshot module")
            return "Error: No default model configured"

        # Get streaming response from Claude
        stream_resp = bedrock_stream(
            messages=[formatted_msg],
            system=[{'text': system_prompt}],
            model_id=model_id,
            params=inference_params,
            additional_params=additional_model_fields
        )

        if not stream_resp:
            logger.error("No response received from model")
            return "Error: No response received from the model"

        # Initialize response
        partial_msg = ""
        for chunk in stream_resp.get("stream", []):
            if "contentBlockDelta" in chunk:
                delta_text = chunk["contentBlockDelta"]["delta"].get("text", "")
                if delta_text:
                    partial_msg += delta_text
                    yield partial_msg

    except Exception as e:
        error_msg = f"Error in gen_with_think: {str(e)}"
        logger.error(error_msg)
        yield error_msg
