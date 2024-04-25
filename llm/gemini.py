# Copyright iX.
# SPDX-License-Identifier: MIT-0
from PIL import Image
import google.generativeai as gm
from common import USER_CONF, get_secret
from utils import image



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

llm = gm.GenerativeModel(USER_CONF.get_model_id('gemini'))
multimodal_model = gm.GenerativeModel(USER_CONF.get_model_id('gemini-vision'))
conversation = llm.start_chat(history=[])


def clear_memory():
    # conversation.rewind()
    global conversation 
    conversation = llm.start_chat(history=[])
    return [('/reset', 'Conversation history forgotten.')]


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
    try:
        response = multimodal_model.generate_content(
            [media, prompt],
            generation_config=generation_config
        )
    except:
        raise

    # add current conversation to chat history
    chat_history[-1][1] = response.text
    
    # send <chat history> back to Chatbot
    return chat_history


def vision_analyze(file_path: str, require_desc):

    # Define prompt templete
    text_prompt = require_desc or "Explain the image in detail."
    msg_content = [f"Analyze or describe the content of the image(s) according to the requirement:{text_prompt}"]

    if file_path.endswith('.pdf'):
        img_list = image.pdf_to_imgs(file_path)
        msg_content.extend(img_list)
    else:
        img_file = Image.open(file_path)
        msg_content.append(img_file)
    try:
        resp = multimodal_model.generate_content(
            contents=msg_content,
            generation_config=generation_config
        )
    except:
        raise

    return resp.text
