# Copyright iX.
# SPDX-License-Identifier: MIT-0
from utils import format_resp, format_msg
from utils.aws import translate_text
from core.integration.module_config import module_config
from llm.claude_deprecated import bedrock_generate


LANGS = ["en_US", "zh_CN", "zh_TW", "ja_JP", "de_DE", "fr_FR"]
STYLES = {
    "正常": {
        'description': '清晰自然的表达',
        'prompt': 'Write in a clear, straightforward manner using standard language and natural flow',
        "options": {}
    },
    "学术": {
        'description': '学术风格，使用规范的学术用语, 严谨的论证结构, 客观中立的语气',
        'prompt': 'Write in a formal academic style with precise terminology and logical structure. Use objective, analytical language and maintain a scholarly tone. Include clear argumentation and evidence-based statements. Avoid colloquialisms and maintain professional distance.',
    },
    "新闻": {
        'description': '新闻报道风格, 简洁明了, 重点突出, 遵循 5W1H 原则',
        'prompt': 'Write in a journalistic style following the 5W1H principle (Who, What, When, Where, Why, How). Present information objectively and concisely, with clear attribution and factual presentation. Use inverted pyramid structure, starting with the most important information.',
    },
    "文学": {
        'description': '文学创作风格, 富有感情色彩, 善用修辞手法, 具有艺术性',
        'prompt': 'Write with literary flair, employing rich imagery, metaphors, and elegant prose. Use varied sentence structures, descriptive language, and poetic devices. Create a sophisticated narrative flow with attention to rhythm and emotional resonance.',
    },
    "口语": {
        'description': '口语化风格, 通俗易懂, 生动活泼, 接近日常表达',
        'prompt': 'Write in a conversational tone that mirrors natural speech patterns. Use everyday expressions, contractions, and informal language while maintaining clarity. Include conversational fillers and casual transitions that people use in daily conversations.',
    },    
    "幽默": {
        'description': '幽默风格, 俏皮的比喻',
        'prompt': 'Write with wit and humor, using clever wordplay, amusing metaphors, and light-hearted tone. Include appropriate jokes or humorous observations where suitable. Keep the tone playful but not overly silly.',
    },
    "可爱": {
        'description': '可爱风格, 语气活泼, 使用带有萌感的词汇或emoji',
        'prompt': 'Write in an adorable and endearing style, using cheerful expressions, gentle language, and occasional emoticons. Add warmth and sweetness to the tone, making it feel friendly and approachable. Use diminutives and positive expressions where appropriate.',
    } 
}


inference_params = {
    # maximum number of tokens to generate. Responses are not guaranteed to fill up to the maximum desired length.
    'maxTokens': 4096,
    # tunes the degree of randomness in generation. Lower temperatures mean less random generations.
    "temperature": 0.5,
    # less than one keeps only the smallest set of most probable tokens with probabilities that add up to top_p or higher for generation.
    "topP": 0.5,
    # stop_sequences - are sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    "stopSequences": ["end_turn"]
}

additional_model_fields = {
    # The higher the value, the stronger a penalty is applied to previously present tokens,
    # Use a lower value to ignore less probable options.  Claude 0-500, default 250
    "top_k": 200
}


def text_proofread(text, options=None):
    if text == '':
        return "Tell me something first."

    options = options or {}
    target_lang = options.get('target_lang', 'en_US')

    # Define prompts for proofreading
    system_proofread = f"""
        You are a professional proofreader with expertise in grammar, spelling, and language mechanics across multiple languages.
        Your task is to thoroughly check the text for any errors in spelling, grammar, punctuation, and sentence structure.
        Provide the corrected version while maintaining the original meaning and style.
        Ensure the output is in {target_lang} language.
        Output only with the succinct context and nothing else.
        """
    prompt_proofread = f"""
        Proofread and correct the text within <text></text> tags:
        <text>
        {text}
        </text>
        """
    message_proofread = format_msg({"text": prompt_proofread}, 'user')

    # Get model ID from module config
    model_id = module_config.get_default_model('text')

    resp = bedrock_generate(
        messages=[message_proofread],
        system=[{'text':system_proofread}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    proofread_text = resp.get('content')[0].get('text')
    return format_resp(proofread_text)


def text_rewrite(text, options=None):
    if text == '':
        return "Tell me something first."

    options = options or {}
    style_key = options.get('style', '正常')
    target_lang = options.get('target_lang', 'en_US')
    # Source_lang_code = translate_text(text, target_lang).get('source_lang_code')

    # Get style prompt from STYLES dictionary
    style_info = STYLES.get(style_key)
    style_prompt = style_info['prompt']

    # Define prompts for text rewrite
    system_rewrite = f"""
        You are an experienced editor with a keen eye for detail and a deep understanding of language, style, and grammar.
        Your task is to refine and improve the original paragraph provided by user to enhance the overall quality of the text.
        You can alternate the word choice, sentences structure and phrasing to make the expression more natural and fluent, 
        suitable for the native {target_lang} language speakers.
        Output only with the succinct context and nothing else.
        """
    prompt_rewrite = f"""
        Rewrite the text within <original_paragraph> </original_paragraph> tags following this style instruction:
        {style_prompt}
        Ensuring the output is in {target_lang} language:

        <original_paragraph>
        {text}
        </original_paragraph>
        """
    message_rewrite = format_msg({"text": prompt_rewrite}, 'user')

    # Get model ID from module config
    model_id = module_config.get_default_model('text')

    # Get the llm reply
    resp = bedrock_generate(
        messages=[message_rewrite],
        system=[{'text':system_rewrite}],
        model_id=model_id,
        params=inference_params,        
        additional_params=additional_model_fields
    )

    polished_text = resp.get('content')[0].get('text')

    return format_resp(polished_text)


def text_reduce(text, options=None):
    if text == '':
        return "Tell me something first."

    options = options or {}
    target_lang = options.get('target_lang', 'en_US')

    # Define prompts for text reduction
    system_reduce = f"""
        You are an expert in concise writing and text simplification.
        Your task is to simplify the text by removing redundant information and simplifying sentence structure
        while preserving the core message and key points. Focus on clarity and brevity.
        Ensure the output is in {target_lang} language.
        Output only with the succinct context and nothing else.
        """
    prompt_reduce = f"""
        Simplify and reduce the text within <text></text> tags while maintaining the core message:
        <text>
        {text}
        </text>
        """
    message_reduce = format_msg({"text": prompt_reduce}, 'user')

    # Get model ID from module config
    model_id = module_config.get_default_model('text')

    resp = bedrock_generate(
        messages=[message_reduce],
        system=[{'text':system_reduce}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    reduced_text = resp.get('content')[0].get('text')
    return format_resp(reduced_text)


def text_expand(text, options=None):
    if text == '':
        return "Tell me something first."

    options = options or {}
    target_lang = options.get('target_lang', 'en_US')

    # Define prompts for text expansion
    system_expand = f"""
        You are an expert content developer skilled in expanding and enriching text.
        Your task is to enhance the original text by adding relevant details, examples, and background information
        while maintaining coherence and natural flow. Keep the additions relevant and valuable to the context.
        Ensure the output is in {target_lang} language.
        Output only with the succinct context and nothing else.
        """
    prompt_expand = f"""
        Expand the text within <text></text> tags by adding relevant details and background information:
        <text>
        {text}
        </text>
        """
    message_expand = format_msg({"text": prompt_expand}, 'user')

    # Get model ID from module config
    model_id = module_config.get_default_model('text')

    resp = bedrock_generate(
        messages=[message_expand],
        system=[{'text':system_expand}],
        model_id=model_id,
        params=inference_params,
        additional_params=additional_model_fields
    )

    expanded_text = resp.get('content')[0].get('text')
    return format_resp(expanded_text)
