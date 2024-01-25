# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from langchain.llms.bedrock import Bedrock
from . import bedrock_runtime



inference_modifier = {
    'max_tokens_to_sample':4096, 
    "temperature":1,
    "top_k":10,
    "top_p":1,
    "stop_sequences": ["\n\nHuman"]
    }

textgen_llm = Bedrock(
    model_id = "anthropic.claude-v2:1",
    client = bedrock_runtime, 
    model_kwargs = inference_modifier 
    )



def gen_code(requirement, language):
    if requirement == '':
        return "Please tell me your requirement first."

    # Create a prompt template that has multiple input variables
    architect_prompt = PromptTemplate(
        input_variables=["requirement", "programmingLanguage"], 
        template="""
        You are an experienced solution architect at a software company. 
        Your task is to help users design excellent code framework architectures as references for developers according to the human's requirements.

        Human: Provide {programmingLanguage} code framework architecture according to the following requirements:
        <requirement>
        {requirement}
        </requirement>

        Assistant:"""
    )
    arch_prompt = architect_prompt.format(requirement=requirement, programmingLanguage=language)
    response = textgen_llm(arch_prompt)
    instruction = response[response.index('\n')+1:]

    # Create a prompt template that has multiple input variables
    coder_prompt = PromptTemplate(
        input_variables=["instruction", "programmingLanguage"], 
        template="""
        You are a senior software developer in {programmingLanguage}.
        Your task is to generate runnable code according to the human's instructions. 
        You should import any needed libraries first, and add code comments if necessary, and explain the code at the end.

        Human:
        <instruction>
        {instruction}
        </instruction>

        Assistant:"""
    )

    prompt = coder_prompt.format(instruction=instruction, programmingLanguage=language)

    response = textgen_llm(prompt)
    code_explanation = response[response.index('\n')+1:]

    return code_explanation
