# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationChain
from langchain.memory import ConversationBufferMemory
from langchain.llms.bedrock import Bedrock
from . import bedrock_runtime



model_id = "anthropic.claude-v2"
# modelId = 'anthropic.claude-instant-v1'

inference_modifier = {
    'max_tokens_to_sample':4096, 
    "temperature":1,
    "top_k":10,
    "top_p":1,
    "stop_sequences": ["\n\nHuman"]
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

def text_chat(message:str, history:list, style:str):
    if message == '':
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
        Human: The following is a friendly conversation between a human and an AI.
        The AI is talkative and provides lots of specific details from its context.         
        If the AI does not know the answer to a question, it truthfully says it does not know.

        Current conversation:
        <conversation_history>
        {history}
        </conversation_history>

        Here is the human's next reply:
        <human_reply>
        {input}
        </human_reply>

        Assistant:
        """
    )

    conversation.prompt = chat_prompt
    # 获取llm回复，注意 Claude回复内容带一个空格，例如 " Hello! I'm Claude“
    bot_reply = conversation.predict(input=message)
    # 将当前对话添加到聊天记录
    history.append((message, bot_reply))
    
    # 返回<空>和<历史记录>给输入框和Chatbot
    return '', history


def clear_memory():
    buffer_memory.clear()
    return [('/reset', 'Conversation history forgotten.')]
