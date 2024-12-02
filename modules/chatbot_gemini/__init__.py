# Copyright iX.
# SPDX-License-Identifier: MIT-0
import google.generativeai as gm
from common.logger import logger
from common.llm_config import get_default_model, get_system_prompt
from llm.gemini import get_generation_config


# Initialize conversation
conversation = None

def convert_history_to_gemini_format(history):
    """Convert gradio chat history to Gemini format"""
    if not history:
        return []
    
    gemini_history = []
    for msg in history:
        if msg["role"] == "user":
            gemini_history.append({"role": "user", "parts": [{"text": msg["content"]}]})
        elif msg["role"] == "assistant":
            gemini_history.append({"role": "model", "parts": [{"text": msg["content"]}]})
    return gemini_history

def initialize_model(history):
    """Initialize or reinitialize the chat model with latest configuration"""
    try:
        model_id = get_default_model('chatbot-gemini')
        chat_model = gm.GenerativeModel(
            model_name=model_id,
            generation_config=get_generation_config('chatbot-gemini'),
            system_instruction=get_system_prompt('chatbot-gemini') or [
                    "You are a friendly chatbot.",
                    "You are talkative and provides lots of specific details from its context.",
                    "If you are unsure or don't have enough information to provide a confident answer, just say 'I do not know' or 'I am not sure."
                ]
        )
        gemini_history = convert_history_to_gemini_format(history)
        return chat_model.start_chat(history=gemini_history)
        
    except Exception as e:
        logger.warning(f"Failed to initialize chat model: {e}")
        return None


def multimodal_chat(message: dict, history: list):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''
    global conversation
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

        # Initialize chat conversation with history
        conversation = initialize_model(history)

        resp = conversation.send_message(contents, stream=True)

        partial_msg = ""
        for chunk in resp:
            partial_msg = partial_msg + chunk.text
            yield {"role": "assistant", "content": partial_msg}

    except Exception as ex:
        logger.error(f"multimodal_chat: {str(ex)}")
        return {"role": "assistant", "content": f"An error occurred: {str(ex)}"}
