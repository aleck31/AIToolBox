# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.llms.bedrock import Bedrock
from . import bedrock_runtime



model_id = "anthropic.claude-v2:1"
# model_id = 'anthropic.claude-instant-v1'

inference_modifier = {
    'max_tokens_to_sample':2048, 
    "temperature":0.9,
    "top_p":0.999,
    "top_k":200,
    "stop_sequences": ["\n\nHuman:"]
    }

textgen_llm = Bedrock(
    model_id = model_id,
    client = bedrock_runtime, 
    model_kwargs = inference_modifier 
    )

buffer_memory = ConversationBufferMemory(
    return_messages=True,
    human_prefix="Human", 
    ai_prefix="Assistant"
)
conversation = ConversationChain(
    # turn verbose to true to see the full logs and documents
    # verbose=True,
    llm=textgen_llm,
    memory=buffer_memory
)

def text_chat(input_msg:str, chat_history:list, style:str):
    if input_msg == '':
        return "Please tell me something first :)"
    
    # AI的回复采用 {style} 的对话风格.
    match style:
        case "极简":
            buffer_memory.chat_memory.add_user_message("You will be acting as a rigorous person. Your goal is to answer questions concisely and efficiently.")
            buffer_memory.chat_memory.add_ai_message("I am strict and talk to users using the most concise language.")
        case "理性":
            buffer_memory.chat_memory.add_user_message("You will be acting as a sensible professor, your goal is to provide sensible answers and advice to users")
            buffer_memory.chat_memory.add_ai_message("I am a rational and rigorous professor, I talk to users based on rational analysis.")
        case "幽默":
            buffer_memory.chat_memory.add_user_message("You will be acting as a humorous person, your goal is to answer users' questions in humorous language.")
            buffer_memory.chat_memory.add_ai_message("I am a humorous person and talk to users with great humor.")      
        case "可爱":
            buffer_memory.chat_memory.add_user_message("You will be play as a cute young lady. Your goal is to answer users' questions in a cute way.")
            buffer_memory.chat_memory.add_ai_message("I am a very sweet person and talk to users using cute language.")
        case _:
            pass
    
    # Create a prompt template
    chat_prompt = PromptTemplate.from_template(
        """
        You are an AI chatbot. You are talkative and provides lots of specific details from its context.
        If you do not know the answer to a question, it truthfully says you don't know.
        The following is a friendly conversation between a human and an AI.

        Current conversation:
        <conversation_history>
        {history}
        </conversation_history>

        Here is the human's next reply:
        Human:
        <human_message>
        {input}
        </human_message>

        Assistant:
        """
    )

    conversation.prompt = chat_prompt
    # Get the llm reply, pay attention Claude reply content with a space，like: " Hello! I'm Claude“
    bot_reply = conversation.predict(input=input_msg)
    # add current conversation to chat history
    # chat_history.append((input_msg, bot_reply))
    chat_history[-1][1] = bot_reply
    
    # send <chat history> back to Chatbot
    return chat_history


def clear_memory():
    buffer_memory.clear()
    return [('/reset', 'Conversation history forgotten.')]
