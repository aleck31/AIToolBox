# Copyright iX.
# SPDX-License-Identifier: MIT-0
import json
from common import USER_CONF
from utils import ChatHistory, file
from . import generate_content, generate_stream



model_id = USER_CONF.get_model_id('claude3')

inference_params = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 4096,
    # Use a lower value to decrease randomness in the response. Claude 0-1, default 0.5
    "temperature": 0.9,
    # Specify the number of token choices the model uses to generate the next token. Claude 0-1, default 1
    "top_p": 0.99,
    # Use a lower value to ignore less probable options.  Claude 0-500, default 250
    "top_k": 200,
    "stop_sequences": ["end_turn"]
}

chat_memory = ChatHistory()


def clear_memory():
    chat_memory.clear()
    return [('/reset', 'Conversation history forgotten.')]


def text_chat(input_msg: str, chat_history: list, style: str):
    if input_msg == '':
        return "Please tell me something first :)"

    chat_memory.add_user_text(input_msg)

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
        You are an AI chatbot. You are talkative and provides lots of specific details from its context.
        {prompt_style}
        If you do not know the answer to a question, it truthfully says you don't know.
        """

    # Get the llm reply
    resp = generate_content(chat_memory.messages,
                            system_prompt, inference_params, model_id)
    bot_reply = resp.get('content')[0].get('text')
    # add current conversation to chat memory and history
    chat_memory.add_bot_text(bot_reply)
    # chat_history.append((input_msg, bot_reply))
    chat_history[-1][1] = bot_reply

    # send <chat history> back to Chatbot
    return chat_history


def media_chat(media_path, chat_history: list):
    # Define system prompt base on style
    system_prompt = "Reply in the corresponding language based on the context of the conversation."

    user_msg = {
        'text': 'Explain the image in detail.',
        'file': media_path
    }

    # message_format = [format_message(content_img, "user", 'image')]
    chat_memory.add_user_msg(user_msg)

    # Get the llm reply
    resp = generate_content(chat_memory.messages,
                            system_prompt, inference_params, model_id)
    bot_reply = resp.get('content')[0].get('text')

    # add current conversation to chat memory and history
    chat_memory.add_bot_text(bot_reply)
    chat_history[-1][1] = bot_reply

    # send <chat history> back to Chatbot
    return chat_history


def multimodal_chat(message: dict, history: list, style: str):
    '''
    :input: message dict
    {
        "text": "user input", 
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
        You are an AI chatbot. You are talkative and provides lots of specific details from its context.
        {prompt_style}
        If you are unsure or don't have enough information to provide a confident answer, simply say "I don't know" or "I'm not sure."
        """

    if history:
        last_bot_msg = {"text": history[-1][1]}
        chat_memory.add_bot_msg(last_bot_msg)
    else:
        chat_memory.clear()

    # print(f"USER_Message: {message}")
    chat_memory.add_user_msg(message)

    # Get the llm reply
    resp = generate_stream(
        chat_memory.messages,
        system_prompt,
        inference_params, model_id
    )

    partial_message = ""
    for event in resp.get("body"):
        chunk = json.loads(event["chunk"]["bytes"])
        if chunk['type'] == 'content_block_delta':
            if chunk['delta']['type'] == 'text_delta':
                print(chunk['delta']['text'], end="")
                partial_message = partial_message + chunk['delta']['text']
                yield partial_message


def vision_analyze(file_path: str, require_desc):
    '''
    :input: image or pdf file path
    '''
    # Define system prompt base on style
    system_prompt = '''
    Analyze or describe the content of the image(s) according to the user's requirement.
    Respond using the language onsistent with the user or the language specified in the requirement.
    '''

    text_prompt = require_desc or "Explain the image in detail."
    msg_content = [
        {"type": "text", "text": f"<requirement>{text_prompt}</requirement>" }
    ]

    if file_path.endswith('.pdf'):
        img_list = file.pdf_to_imgs(file_path)    
        for img in img_list:
            img_msg = {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": file.pil_to_base64(img)
                }
            }  
            msg_content.append(img_msg)

    else:
        msg_content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": file.path_to_base64(file_path)
                }
            }
        )

    formated_msg = {'role': 'user', 'content': msg_content}

    # Get the llm reply
    resp = generate_content(
        [formated_msg], system_prompt, inference_params, model_id)
    bot_reply = resp.get('content')[0].get('text')

    return bot_reply
