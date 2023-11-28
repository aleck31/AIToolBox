# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from langchain.llms.bedrock import Bedrock
from . import bedrock_runtime
from utils import format_resp



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
    model_id = "anthropic.claude-v2",
    client = bedrock_runtime, 
    model_kwargs = inference_modifier 
    )



def text_translate(text, target_lang):
    if text == '':
        return "Tell me something first."
    
    translate_prompt = PromptTemplate(
        input_variables=["text", "target_lang"], 
        template="""
        Human: Please translate the original paragraph in to {target_lang} language, 
        match the expressions of the native language, and make suer there are no grammatical errors in the translated contents.
        Provide only the translated contents, do not include any other content.
        <original_paragraph>
        {text}
        </original_paragraph>

        Assistant:
        """
    )

    prompt = translate_prompt.format(text=text, target_lang=target_lang)

    response = textgen_llm(prompt)

    return format_resp(response)


def text_rewrite(text, style):
    if text == '':
        return "Tell me something first."

    match style:
        case "极简":
            style = "concise and clean"
        case "理性":
            style = "rational and rigorous"
        case "幽默":
            style = "great humor"   
        case "可爱":
            style = "lovely"
        case _:
            pass

    # Create a prompt template that has multiple input variables
    rewrite_prompt = PromptTemplate(
        input_variables=["text", "style"], 
        template="""
        Human: Polis the original paragraph in a {style} way to make the content more idiomatic and natural in the native language expression.
        You can modify the vocabulary, adjust sentences structure to make it more natural. But do not overextend or change the meaning.
        Please provide only the polished contents, do not translate.
        <original_paragraph>
        {text}
        </original_paragraph>

        Assistant:
        """
    )

    prompt = rewrite_prompt.format(text=text, style=style)

    response = textgen_llm(prompt)

    return format_resp(response)


def text_summary(text):
    if text == '':
        return "Tell me something first."
    
    translate_prompt = PromptTemplate(
        input_variables=["text"], 
        template="""
        Human: Please provide a summary of the following text:
        <text>
        {text}
        </text>

        Assistant:
        """
    )

    prompt = translate_prompt.format(text=text)

    response = textgen_llm(prompt)

    return format_resp(response)
