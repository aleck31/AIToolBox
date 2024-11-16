# Copyright iX.
# SPDX-License-Identifier: MIT-0
from common import USER_CONF
from common.llm_config import get_module_config
from common.logger import logger
from utils import format_msg
from llm.gemini import get_generation_config
from llm import bedrock_stream
import google.generativeai as gm


# Get vision configuration for Gemini
vision_config = get_module_config('vision-gemini')
vision_model = vision_config.get('default_model') if vision_config else None
if not vision_model:
    vision_model = USER_CONF.get_model_id('gemini-vision')

try:
    llm_vision = gm.GenerativeModel(
        model_name=vision_model,
        generation_config=get_generation_config('vision-gemini')
    )
except Exception as e:
    logger.warning(f"Failed to initialize vision model: {e}")
    llm_vision = None


def vision_analyze_gemini(file_path: str, req_description=None):
    """Vision analysis using Gemini model"""
    # Get system prompt from configuration
    system_prompt = ""
    if vision_config:
        system_prompt = vision_config.get('system_prompt', '')

    # Define prompt template
    req_description = req_description or "Describe the media or document in detail."
    text_prompt = f"{system_prompt}\nAnalyze or describe the multimodal content according to the requirement: {req_description}"

    file_ref = gm.upload_file(path=file_path)
    
    try:
        resp = llm_vision.generate_content(
            contents=[file_ref, text_prompt],
            generation_config=get_generation_config('vision-gemini'),
            stream=True
        )

        partial_response = ""
        for chunk in resp:
            if chunk.text:
                partial_response += chunk.text
                yield partial_response

    except Exception as ex:
        logger.error(ex)
        yield "Unfortunately, an issue occurred, no content was generated by the model."


def vision_analyze_claude(file_path: str, req_description=None):
    """Vision analysis using Claude model"""
    # Get module configuration
    inference_params = get_inference_params('vision')
    system_prompt = get_system_prompt('vision') or '''
        Analyze or describe the multimodal content according to the user's requirement.
        Respond using the language consistent with the user or the language specified in the <requirement> </requirement> tags.
        '''

    req_description = req_description or "Describe the picture or document in detail."

    formated_msg = format_msg(
        {
            "text": f"<requirement>{req_description}</requirement>",
            "files": [file_path]
        },
        "user"
    )

    # Get module config for model selection
    config = get_module_config('vision')
    model_id = config.get('default_model') if config else None
    if not model_id:
        model_id = USER_CONF.get_model_id('vision')

    # Additional model parameters
    additional_model_fields = {
        "top_k": 200  # Claude 0-500, default 250
    }

    # Get the llm reply using streaming
    # Restriction：document file name 不支持中文字符
    stream_resp = bedrock_stream(
        messages=[formated_msg],
        system=[{'text': system_prompt}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    partial_msg = ""
    for chunk in stream_resp["stream"]:
        if "contentBlockDelta" in chunk:
            partial_msg = partial_msg + chunk["contentBlockDelta"]["delta"]["text"]
            yield partial_msg


def get_inference_params(module_name: str):
    """Get inference parameters from module configuration"""
    config = get_module_config(module_name)
    if config and 'parameters' in config:
        params = config['parameters'].copy()
        # Convert parameters to bedrock format
        if 'temperature' in params:
            params['temperature'] = float(params['temperature'])
        if 'max_tokens' in params:
            params['maxTokens'] = int(params.pop('max_tokens'))
        return params
    
    # Default parameters if no configuration found
    return {
        "maxTokens": 4096,
        "temperature": 0.9,
        "topP": 0.99,
        "stopSequences": ["end_turn"]
    }


def get_system_prompt(module_name: str, sub_module: str = None):
    """Get system prompt from module configuration"""
    config = get_module_config(module_name)
    if config:
        if sub_module and 'sub_modules' in config:
            sub_config = config['sub_modules'].get(sub_module, {})
            return sub_config.get('system_prompt')
        return config.get('system_prompt')
    return None
