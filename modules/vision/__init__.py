# Copyright iX.
# SPDX-License-Identifier: MIT-0
from common.llm_config import get_default_model, get_system_prompt, get_inference_params
from common.logger import logger
from utils import format_msg
from llm.gemini import get_generation_config
from llm.claude import bedrock_stream, format_claude_params
import google.generativeai as gm


def vision_analyze_gemini(file_path: str, user_requirement=None):
    """Vision analysis using Gemini model"""

    # Get vision configuration for Gemini
    gemini_model_id = get_default_model('chatbot-gemini')

    try:
        llm_vision = gm.GenerativeModel(
            model_name=gemini_model_id,
            generation_config=get_generation_config('vision')
        )
    except Exception as e:
        logger.warning(f"Failed to initialize vision model: {e}")
        llm_vision = None

    # Get system prompt from configuration
    system_prompt = get_system_prompt('vision') or "Analyze or describe the multimodal content according to the requirement:"

    # Define prompt template
    user_requirement = user_requirement or "Describe the media or document in detail."
    text_prompt = f"{system_prompt}\n{user_requirement}"

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


def vision_analyze_claude(file_path: str, user_requirement=None):
    """Vision analysis using Claude model"""
    # Get module configuration
    inference_params = format_claude_params(get_inference_params('vision'))
    system_prompt = get_system_prompt('vision') or '''
        Analyze or describe the multimodal content according to the user's requirement.
        Respond using the language consistent with the user or the language specified in the <requirement> </requirement> tags.
        '''

    user_requirement = user_requirement or "Describe the picture or document in detail."

    formated_msg = format_msg(
        {
            "text": f"<requirement>{user_requirement}</requirement>",
            "files": [file_path]
        },
        "user"
    )

    # Get model ID from module config
    model_id = get_default_model('vision')

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
