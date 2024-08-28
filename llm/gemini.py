# Copyright iX.
# SPDX-License-Identifier: MIT-0
from PIL import Image
import google.generativeai as gm
from common import USER_CONF, get_secret
from common.logs import log_error
from utils import file


# gemini/getting-started guide:
# https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_python.ipynb
gemini_api_key = get_secret('dev_gemini_api').get('api_key')
gm.configure(api_key=gemini_api_key)


default_config = gm.GenerationConfig(
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
    'SEXUAL' : 'BLOCK_NONE',
    'DANGEROUS' : 'BLOCK_NONE'
}

llm_chat = gm.GenerativeModel(
    # model_name="gemini-1.5-pro-001",
    model_name=USER_CONF.get_model_id('gemini-chat'),
    generation_config=default_config,
    system_instruction=[
        "You are a friendly chatbot.",
        "You are talkative and provides lots of specific details from its context.",
        "If you are unsure or don't have enough information to provide a confident answer, just say 'I do not know' or 'I am not sure.'"
    ]
    # safety_settings = safety_settings
)

conversation = llm_chat.start_chat(history=[])


def clear_memory():
    # conversation.rewind()
    global conversation 
    conversation = llm_chat.start_chat(history=[])
    return [('/reset', 'Conversation history forgotten.')]


def multimodal_chat(message: dict, history: list):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''

    contents = [message.get('text')]

    if message.get('files'):
        for file_path in message.get('files'):
            file_ref = gm.upload_file(path=file_path)
            contents.append(file_ref)
    # print(llm.count_tokens(contents))

    if not history:
        clear_memory()

    try:
        resp = conversation.send_message(contents, stream=True)
    except:
        return "Oops, looks like I had a brain fart! Pls allow me a brief moment to investigate the issue."
    
    partial_msg = ""
    for chunk in resp:
        partial_msg = partial_msg + chunk.text
        yield(partial_msg)


vision_config = gm.GenerationConfig(
    max_output_tokens=4096,
    temperature=0.9,
    top_p=0.999,
    top_k=200,
    candidate_count=1
)

llm_vision = gm.GenerativeModel(
    model_name=USER_CONF.get_model_id('gemini-vision'),
    generation_config=vision_config,
    # safety_settings = safety_settings
)


def vision_analyze(file_path: str, req_description=None):

    # Define prompt templete
    req_description = req_description or "Describe the media or document in detail."
    text_prompt = f"Analyze or describe the multimodal content according to the requirement:{req_description}"

    file_ref = gm.upload_file(path=file_path)    
    # print(llm.count_tokens([file_ref, msg_content]))
    
    try:
        resp = llm_vision.generate_content(
            contents = [file_ref, text_prompt],
            generation_config=vision_config
        )
    except Exception as ex:
        log_error(ex)
        return "Unfortunately, an issue occurred, no content was generated by the model."

    return resp.text
