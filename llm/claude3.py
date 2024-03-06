# Copyright iX.
# SPDX-License-Identifier: MIT-0
import json
import base64
from . import bedrock_runtime


# https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html#model-ids-arns
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
# model_id = "anthropic.claude-v2:1"
# model_id = 'anthropic.claude-instant-v1'

inference_params = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 4096,
    "temperature": 0.9, # Use a lower value to decrease randomness in the response. Claude 0-1, default 0.5
    "top_p": 0.99,         # Specify the number of token choices the model uses to generate the next token. Claude 0-1, default 1
    "top_k": 200,       # Use a lower value to ignore less probable options.  Claude 0-500, default 250
    "stop_sequences": ["end_turn"]
    }


# Helper function to pass prompts and inference parameters
def generate_message(messages, system, params):
    params['system'] = system
    params['messages'] = messages
    body=json.dumps(params)
    
    response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get('body').read())

    return response_body


def format_content(content, role, type):
    if type == 'text':
        content_format = {
            "role": role, 
            "content": [
                {
                    "type": "text",
                    "text": content
                }
            ]
        }
    elif type == 'image':
        content_format = {
            "role": role,
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": content
                    }
                },
                {
                    "type": "text",
                    "text": "Describe what you understand from the content in this picture, as much detail as possible."
                }
            ]
        }                          
    return content_format


def text_chat(input_msg:str, chat_history:list, style:str):
    if input_msg == '':
        return "Please tell me something first :)"

    chat_history.pop()

    history_format = []
    for human, assistant in chat_history:
        history_format.append(format_content(human, "user", 'text'))
        history_format.append(format_content(assistant, "assistant", 'text'))

    history_format.append(
        format_content(input_msg, "user", 'text')
    )

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
    resp = generate_message(history_format, system_prompt, inference_params)
    bot_reply = resp.get('content')[0].get('text')
    # add current conversation to chat history
    chat_history.append((input_msg, bot_reply))
    # chat_history[-1][1] = bot_reply
    
    # send <chat history> back to Chatbot
    return chat_history


def media_chat(media_path, chat_history:list):

    # Define system prompt base on style
    system_prompt = "Describe the picture in both English and Chinese."
    
    # Read reference image from file and encode as base64 strings.
    with open(media_path, "rb") as image_file:
        content_img = base64.b64encode(image_file.read()).decode('utf8') 
    
    message_format = [format_content(content_img, "user", 'image')]

    # Get the llm reply
    resp = generate_message(message_format, system_prompt, inference_params)
    bot_reply = resp.get('content')[0].get('text')

    # add current conversation to chat history
    chat_history[-1][0] = str(media_path)
    chat_history[-1][1] = bot_reply

    # send <chat history> back to Chatbot
    return chat_history

def clear_memory():
    # buffer_memory.clear()
    return [('/reset', 'Conversation history forgotten.')]
