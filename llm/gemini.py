# Copyright iX.
# SPDX-License-Identifier: MIT-0
from PIL import Image
import time
import google.generativeai as gm
from utils.common import get_secret


# api key secret_name = "dev_gemini_api"
gemini_api_key = get_secret('dev_gemini_api').get('api_key')

gm.configure(api_key=gemini_api_key)
llm = gm.GenerativeModel("gemini-pro")
llmv = gm.GenerativeModel("gemini-pro-vision")

# text_message = {
#     "type": "text",
#     "text": "how to make this meat?",
# }

# image_message = {
#     "type": "image_url",
#     "image_url": {"url": "https://ai.google.dev/static/tutorials/python_quickstart_files/output_CjnS0vNTsVis_0.png"},
# }


def bot(input_msg, history):
    response = "**That's cool!**"
    history[-1][1] = ""
    for character in response:
        history[-1][1] += character
        time.sleep(0.1)
        # yield history
    return history, history


def text_chat(input_msg:str, chat_history:list):
    # remove last user message
    # chat_history.pop()
    conversation = llm.start_chat(history=[])
    response = conversation.send_message(input_msg)

    # add current conversation to chat history
    # chat_history.append((input_msg, response.text))
    chat_history[-1][1] = response.text
    
    # send <chat history> back to Chatbot
    return chat_history


def media_chat(media_path, chat_history):

    img = Image.open(media_path)
    response = llmv.generate_content(img)

    # add current conversation to chat history
    chat_history[-1][1] = response.text
    
    # send <chat history> back to Chatbot
    return chat_history