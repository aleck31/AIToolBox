# Copyright iX.
# SPDX-License-Identifier: MIT-0
from common import USER_CONF
from common.logger import logger
from utils import ChatHistory, format_msg, format_resp
from . import bedrock_generate, bedrock_stream


model_id = USER_CONF.get_model_id('claude3')

inference_params = {
    "maxTokens": 4096,
    # Use a lower value to decrease randomness in the response. Claude 0-1, default 0.5
    "temperature": 0.9,
    # Specify the number of token choices the model uses to generate the next token. Claude 0-1, default 1
    "topP": 0.99,
    # stop_sequences - are sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    "stopSequences": ["end_turn"]
}

additional_model_fields = {
    # The higher the value, the stronger a penalty is applied to previously present tokens,
    # Use a lower value to ignore less probable options.  Claude 0-500, default 250
    "top_k": 200
}

chat_memory = ChatHistory()


def clear_memory():
    chat_memory.clear()
    return [('/reset', 'Conversation history forgotten.')]


def multimodal_chat(message: dict, history: list, style: str):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''
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

    # Define system prompt base on style
    system_prompt = f"""
        You are a friendly chatbot. You are talkative and provides lots of specific details from its context.
        {prompt_style}
        If you are unsure or don't have enough information to provide a confident answer, simply say "I don't know" or "I'm not sure."
        """

    if history:
        last_bot_msg = {"text": history[-1][1]}
        chat_memory.add_bot_msg(last_bot_msg)
    else:
        chat_memory.clear()

    # logger.info(f"USER_Message: {message}")
    chat_memory.add_user_msg(message)

    # Get the llm reply
    stream_resp = bedrock_stream(
        messages=chat_memory.conversation,
        system=[{'text': system_prompt}],
        model_id=USER_CONF.get_model_id('claude3'),
        params=inference_params,
        additional_params=additional_model_fields
    )

    partial_msg = ""
    for chunk in stream_resp["stream"]:
        if "contentBlockDelta" in chunk:
            partial_msg = partial_msg + \
                chunk["contentBlockDelta"]["delta"]["text"]
            yield partial_msg


def vision_analyze(file_path: str, req_description=None):
    '''
    :input: image or pdf file path
    '''
    # Define system prompt base on style
    system_prompt = '''
        Analyze or describe the multimodal content according to the user's requirement.
        Respond using the language onsistent with the user or the language specified in the <requirement> </requirement> tags.
        '''

    req_description = req_description or "Describe the picture or document in detail."

    formated_msg = format_msg(
        {
            "text": f"<requirement>{req_description}</requirement>",
            "files": [file_path]
        },
        "user"
    )

    # Get the llm reply
    # Restriction：document file name 不支持中文字符
    resp = bedrock_generate(
        messages=[formated_msg],
        system=[{'text': system_prompt}],
        model_id=USER_CONF.get_model_id('vision'),
        params=inference_params,
        additional_params=additional_model_fields
    )

    resp_text = resp.get('content')[0].get('text')

    return format_resp(resp_text)
