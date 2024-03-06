# Copyright iX.
# SPDX-License-Identifier: MIT-0
from PIL import Image
import time
import google.generativeai as gm
from utils.common import get_secret


# gemini/getting-started guide:
# https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_python.ipynb
gemini_api_key = get_secret('dev_gemini_api').get('api_key')

gm.configure(api_key=gemini_api_key)

generation_config = gm.GenerationConfig(
    max_output_tokens=8192,
    temperature=0.9,
    top_p=0.999,
    top_k=200,
    candidate_count=1    
)

llm = gm.GenerativeModel("gemini-pro")
llmv = gm.GenerativeModel("gemini-pro-vision")
conversation = llm.start_chat(history=[])


def text_chat(input_msg:str, chat_history:list):
    # remove the last user message from history
    # chat_history.pop()
    # conversation = llm.start_chat(history=chat_history)
    response = conversation.send_message(
        input_msg,
        # stream=True,
        generation_config=generation_config
    )
    # add current conversation to chat history
    # chat_history.append((input_msg, response.text))
    chat_history[-1][1] = response.text
    
    # send <chat history> back to Chatbot
    return chat_history


def media_chat(media_path, chat_history):

    media = Image.open(media_path)
    prompt = "Describe the contents of the picture in detail in both English and Chinese."
    response = llmv.generate_content(
        [media, prompt],
        generation_config=generation_config
    )

    # add current conversation to chat history
    chat_history[-1][1] = response.text
    
    # send <chat history> back to Chatbot
    return chat_history


def clear_memory():
    # conversation.rewind()
    global conversation 
    conversation = llm.start_chat(history=[])
    return [('/reset', 'Conversation history forgotten.')]
