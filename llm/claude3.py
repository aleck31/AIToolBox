# Copyright iX.
# SPDX-License-Identifier: MIT-0
from common import USER_CONF
from common.chat_memory import chat_memory
from common.llm_config import get_module_config
from utils import format_msg, format_resp
from . import bedrock_generate, bedrock_stream


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

def clear_memory():
    chat_memory.clear()
    return {"role": "assistant", "content": "Conversation history forgotten."}

def multimodal_chat(message: dict, history: list, style: str):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''
    # Get module configuration
    inference_params = get_inference_params('chatbot')
    base_system_prompt = get_system_prompt('chatbot')

    # AI的回复采用 {style} 的对话风格.
    match style:
        case "极简":
            prompt_style = "You're acting like a rigorous person, your goal is to answer questions concisely and efficiently."
        case "理性":
            prompt_style = "You're playing the role of a wise professor, your goal is to provide user with sensible answers and advice"
        case "幽默":
            prompt_style = "You're playing the role of a humorous person, your goal is to answer users' questions in humorous language."
        case "可爱":
            prompt_style = "You're playing the role of a cute girl whose goal is to interact with users in a cute way."
        case _:
            prompt_style = None

    # Define system prompt base on style and configuration
    system_prompt = f"""
        {base_system_prompt or 'You are a friendly chatbot. You are talkative and provides lots of specific details from its context.'}
        {prompt_style}
        If you are unsure or don't have enough information to provide a confident answer, simply say "I don't know" or "I'm not sure."
        """

    if history:
        last_bot_msg = {"text": history[-1]["content"]}
        chat_memory.add_bot_msg(last_bot_msg)
    else:
        chat_memory.clear()

    chat_memory.add_user_msg(message)

    # Get module config for model selection
    config = get_module_config('chatbot')
    model_id = config.get('default_model') if config else None
    if not model_id:
        model_id = USER_CONF.get_model_id('claude3')

    # Additional model parameters
    additional_model_fields = {
        # The higher the value, the stronger a penalty is applied to previously present tokens,
        # Use a lower value to ignore less probable options.  Claude 0-500, default 250
        "top_k": 200  # Claude 0-500, default 250
    }

    # Get the llm reply
    stream_resp = bedrock_stream(
        messages=chat_memory.conversation,
        system=[{'text': system_prompt}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    partial_msg = ""
    for chunk in stream_resp["stream"]:
        if "contentBlockDelta" in chunk:
            partial_msg = partial_msg + \
                chunk["contentBlockDelta"]["delta"]["text"]
            yield {"role": "assistant", "content": partial_msg}
