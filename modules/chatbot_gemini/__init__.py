# Copyright iX.
# SPDX-License-Identifier: MIT-0
import google.generativeai as gm
from common import USER_CONF
from common.logger import logger
from common.llm_config import get_module_config
from llm.gemini import get_generation_config

# Get chatbot configuration
chat_config = get_module_config('chatbot-gemini')
chat_model = chat_config.get('default_model') if chat_config else None
if not chat_model:
    chat_model = USER_CONF.get_model_id('gemini-chat')

# Initialize conversation
conversation = None

try:
    llm_chat = gm.GenerativeModel(
        model_name=chat_model,
        generation_config=get_generation_config('chatbot-gemini'),
        system_instruction=(
            chat_config.get('system_prompt', '').split('\n')
            if chat_config and chat_config.get('system_prompt')
            else [
                "You are a friendly chatbot.",
                "You are talkative and provides lots of specific details from its context.",
                "If you are unsure or don't have enough information to provide a confident answer, just say 'I do not know' or 'I am not sure.'"
            ]
        )
    )
    conversation = llm_chat.start_chat(history=[])
except Exception as e:
    logger.warning(f"Failed to initialize chat model: {e}")

def clear_memory():
    global conversation
    if conversation:
        conversation = llm_chat.start_chat(history=[])
    return {"role": "assistant", "content": "Conversation history forgotten."}

def multimodal_chat(message: dict, history: list):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''
    try:
        # Add debug logging
        logger.debug(f"Received message: {message}")

        # Handle string message from gr.ChatInterface
        if isinstance(message, str):
            contents = [message]
        else:
            contents = [message.get('text')]
            if message.get('files'):
                logger.debug(f"Processing files: {message.get('files')}")
                for file_path in message.get('files'):
                    file_ref = gm.upload_file(path=file_path)
                    contents.append(file_ref)
        
        logger.debug(f"Final contents to send: {contents}")

        if not history:
            clear_memory()

        resp = conversation.send_message(contents, stream=True)

        partial_msg = ""
        for chunk in resp:
            partial_msg = partial_msg + chunk.text
            yield {"role": "assistant", "content": partial_msg}

    except Exception as e:
        error_msg = f"Error in multimodal_chat: {str(e)}"
        logger.error(error_msg)
        return {"role": "assistant", "content": f"An error occurred: {str(e)}"}
