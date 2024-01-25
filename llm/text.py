# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from langchain.llms.bedrock import Bedrock
from . import bedrock_runtime
from utils import format_resp
from utils.common import translate_text



inference_modifier = {
    # maximum number of tokens to generate. Responses are not guaranteed to fill up to the maximum desired length.
    'max_tokens_to_sample':4096, 
    # tunes the degree of randomness in generation. Lower temperatures mean less random generations.
    "temperature":0.5,
    # less than one keeps only the smallest set of most probable tokens with probabilities that add up to top_p or higher for generation.
    "top_p":0.5,
    # top_k - can be used to reduce repetitiveness of generated tokens. 
    # The higher the value, the stronger a penalty is applied to previously present tokens, 
    "top_k":200,
    # stop_sequences - are sequences where the API will stop generating further tokens. The returned text will not contain the stop sequence.
    "stop_sequences": []
    }

textgen_llm = Bedrock(
    model_id = "anthropic.claude-v2:1",
    client = bedrock_runtime, 
    model_kwargs = inference_modifier 
    )



def text_translate(text, Source_lang, target_lang):
    if text == '':
        return "Tell me something first."
    
    translate_prompt = PromptTemplate(
        input_variables=["text", "target_lang"], 
        template="""
        You are an experienced multilingual translation expert. 
        Your task is to translate the original text into the target language, and ensure the translated text conforms to native expressions in the target language without grammatical errors.
        Important: The output only contain the translated text, do not include any other content.
        
        Human: Please translate the original paragraph in to {target_lang} language:
        <original_text>
        {text}
        </original_text>

        Assistant:
        """
    )
    prompt = translate_prompt.format(text=text, target_lang=target_lang)

    response = textgen_llm(prompt)

    return format_resp(response)


def text_rewrite(text, style):
    if text == '':
        return "Tell me something first."
    
    Source_lang_code = translate_text(text, 'en').get('source_lang_code')

    match style:
        case "极简":
            style = "concise and clear"
        case "理性":
            style = "rational and rigorous"
        case "幽默":
            style = "great humor"   
        case "可爱":
            style = "cute and lovely"
        case _:
            style = "general"

    # Create a prompt template that has multiple input variables
    rewrite_prompt = PromptTemplate(
        input_variables=["text", "style", "source_lang_code"], 
        template="""
        You are an experienced editor, your task is to refine the text provided by the user, making the expression more natural and fluent in the {source_lang_code} language.
        You can modify the vocabulary, adjust sentences structure to make it more idiomatic to native speakers. But do not overextend or change the meaning.
        Important: The output only contain the polished text, do not include any other content.

        Human: Polish following original paragraph in a {style} manner:
        <original_paragraph>
        {text}
        </original_paragraph>

        Assistant:
        """
    )
    prompt = rewrite_prompt.format(text=text, style=style, source_lang_code=Source_lang_code)

    response = textgen_llm(prompt)

    return format_resp(response)


def text_summary(text):
    if text == '':
        return "Tell me something first."
    
    translate_prompt = PromptTemplate(
        input_variables=["text"], 
        template="""
        You are a senior editor. Your task is to summarize the text provided by users without losing any important information.
        Important: The output only contain the summary text, do not include any other content.

        Human: Please provide a summary of the following text:
        <text>
        {text}
        </text>

        Assistant:
        <summarized_text>
        </summarized_text>
        """
    )
    prompt = translate_prompt.format(text=text)

    response = textgen_llm(prompt)

    return format_resp(response)
