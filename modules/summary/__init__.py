# Copyright iX.
# SPDX-License-Identifier: MIT-0
from utils import format_resp, format_msg
from common.llm_config import get_default_model
from llm.claude import bedrock_stream
from common.logger import logger


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


def text_summary(text: str, target_lang: str):
    """
    Generate a summary of the input text with streaming response.
    
    Args:
        text (str): The text to summarize
        target_lang (str): Target language for the summary ('original', 'Chinese', or 'English')
    
    Yields:
        str: Chunks of the generated summary
    """
    if text == '':
        yield "Tell me something first."
        return

    # Define system prompt with enhanced summarization guidelines
    system_sum = """
    You are a highly skilled text summarization expert with multilingual capabilities. Your task is to create clear, concise, and well-structured summaries while maintaining the essential meaning and key points of the original text.

    Follow these guidelines for summarization:
    1. Begin with a concise overview sentence that captures the main theme
    2. Structure the summary with clear sections and logical flow
    3. Maintain approximately 20-25% of the original length
    4. Preserve critical terminology, data points, and key quotes
    5. Ensure factual accuracy and maintain the original tone
    6. Use bullet points or numbered lists when appropriate for clarity
    7. Include any significant conclusions or implications
    8. Retain technical precision while improving readability

    Language handling:
    - When 'original' is specified, maintain the same language as the input text
    - When a target language is specified, translate the summary while preserving technical terms
    - Ensure the translation maintains the same level of professionalism and accuracy
    """

    # Enhanced user prompt with language handling
    lang_instruction = "Maintain the original language" if target_lang == "original" else f"Output the summary in {target_lang}"
    
    prompt_sum = f"""
    Please analyze and summarize the following text according to the guidelines. {lang_instruction}.

    <original_text>
    {text}
    </original_text>

    Provide a well-structured summary, ensure the output is in {target_lang} language while keeping technical terms accurate.
    Generate the response in a streaming fashion, ensuring each chunk is a complete and meaningful sentence or bullet point.
    """

    message_sum = format_msg({"text": prompt_sum}, 'user')

    try:
        # Get default model id for Summary module
        model_id = get_default_model('summary')

        # Get streaming response
        stream_resp = bedrock_stream(
            messages=[message_sum],
            system=[{'text': system_sum}],
            model_id=model_id,
            params=inference_params,
            additional_params=additional_model_fields
        )

        if not stream_resp:
            logger.error("No response received from model")
            yield "Error: No response received from the model"
            return

        # Stream the response chunk by chunk
        partial_msg = ""
        for chunk in stream_resp.get("stream", []):
            if "contentBlockDelta" in chunk:
                delta_text = chunk["contentBlockDelta"]["delta"].get("text", "")
                if delta_text:
                    partial_msg += delta_text
                    yield format_resp(partial_msg)

    except Exception as e:
        error_msg = f"Error in text_summary: {str(e)}"
        logger.error(error_msg)
        yield error_msg
