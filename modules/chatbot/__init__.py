# Copyright iX.
# SPDX-License-Identifier: MIT-0
from utils import format_msg, format_resp
from common.chat_memory import chat_memory
from common.llm_config import get_inference_params, get_system_prompt, get_default_model
from llm.claude import bedrock_generate, bedrock_stream, format_claude_params


CHAT_STYLES = {
    "正常": {
        "description": "自然友好的对话风格",
        'prompt': "Maintain a balanced, approachable tone while providing informative and engaging responses. Be clear and articulate, but avoid being overly formal or casual.",
        "options": {}
    },
    "简洁": {
        "description": "简明扼要的表达方式",
        'prompt': "Provide concise and precise responses. Focus on essential information and eliminate unnecessary details. Use clear, direct language and short sentences. Get straight to the point while maintaining clarity and accuracy."
    },
    "专业": {
        "description": "专业正式, 用词严谨, 表意清晰",
        'prompt': "Communicate with professional expertise and academic rigor. Use industry-standard terminology, provide well-structured explanations, and maintain a formal tone. Support statements with logical reasoning and accurate information. Focus on precision and clarity in technical discussions."
    },
    "幽默": {
        "description": "诙谐有趣的对话风格",
        'prompt': "Engage with wit and humor while remaining informative. Use clever wordplay, appropriate jokes, and light-hearted analogies to make conversations entertaining. Keep the tone playful but ensure the core message remains clear and helpful."
    },
    "可爱": {
        "description": "活泼可爱的对话方式",
        'prompt': "Adopt a cheerful and endearing personality. Use gentle, friendly language with occasional emoticons. Express enthusiasm and warmth in responses. Make conversations feel light and pleasant while maintaining helpfulness. Add cute expressions where appropriate without compromising the message quality."
    }
}


def clear_memory():
    chat_memory.clear()
    return {"role": "assistant", "content": "Conversation history forgotten."}


def multimodal_chat(message: dict, history: list, style: str):
    '''
    Args:
    - message (dict):
    {
        "text": "user's text message", 
        "files": ["file_path1", "file_path2", ...]
    }
    '''
    # Get module configuration
    inference_params = format_claude_params(get_inference_params('chatbot'))
    base_system_prompt = get_system_prompt('chatbot')

    # Get style prompt from CHAT_STYLES dictionary
    style_info = CHAT_STYLES.get(style)
    style_prompt = style_info['prompt'] if style_info else None

    # Define system prompt based on style and configuration
    system_prompt = f"""
        {base_system_prompt or 'You are a friendly and talkative conversationalist.'}
        {style_prompt}
        If you are unsure or don't have enough information to provide a confident answer, simply say "I don't know" or "I'm not sure."
        """

    if history:
        last_bot_msg = {"text": history[-1]["content"]}
        chat_memory.add_bot_msg(last_bot_msg)
    else:
        chat_memory.clear()

    chat_memory.add_user_msg(message)

    # Get model ID from module config
    model_id = get_default_model('chatbot')

    # Additional model parameters
    additional_model_fields = {
        # The higher the value, the stronger a penalty is applied to previously present tokens,
        # Use a lower value to ignore less probable options.  Claude 0-500, default 250
        "top_k": 200  # Claude 0-500, default 250
    }

    # Get the llm reply
    stream_resp = bedrock_stream(
        messages=chat_memory.conversation,
        system=[{'text': system_prompt}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    partial_msg = ""
    for chunk in stream_resp["stream"]:
        if "contentBlockDelta" in chunk:
            partial_msg = partial_msg + \
                chunk["contentBlockDelta"]["delta"]["text"]
            yield {"role": "assistant", "content": partial_msg}
