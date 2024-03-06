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
        You are an experienced developer in {programmingLanguage}.
        Your task is to generate high-quality code according to human's instructions, and explain the code at the end.
        Make sure to include any imports required, and add comments for things that are non-obvious.

        After you are done generating the code, check your work carefully to make sure there are no mistakes, errors, or inconsistencies. 
        If there are errors, list those errors in <error> tags, then generate a new version with those errors fixed. 
        If there are no errors, write "CHECKED: NO ERRORS" in <error> tags.

        Human:
        Here is the instruction:
        <instruction>
        {instruction}
        </instruction>

        Assistant:"""
    )

    prompt = coder_prompt.format(instruction=instruction, programmingLanguage=language)

    response = textgen_llm(prompt)
    code_explanation = response[response.index('\n')+1:]

    return code_explanation
