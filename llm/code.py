# Copyright iX.
# SPDX-License-Identifier: MIT-0
from langchain.prompts import PromptTemplate
from utils import format_message, generate_content
from . import bedrock_runtime


model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

inference_params = {
    "anthropic_version": "bedrock-2023-05-31",
    "max_tokens": 4096,
    "temperature": 1, # Use a lower value to decrease randomness in the response. Claude 0-1, default 0.5
    "top_p": 1,         # Specify the number of token choices the model uses to generate the next token. Claude 0-1, default 1
    "top_k": 10,       # Use a lower value to ignore less probable options.  Claude 0-500, default 250
    "stop_sequences": ["end_turn"]
    }


def gen_code(requirement, program_language):
    if requirement == '':
        return "Please tell me your requirement first."

    # Define system prompt for software architect
    system_arch = """
        You are an experienced solution architect at a software company. 
        Your task is to help users design excellent code framework architectures as references for developers according to the human's requirements.
        """
    prompt_arch = f"""
        Provide {program_language} code framework architecture according to the following requirements:
        <requirement>
        {requirement}
        </requirement>
    """
    message_arch = [format_message(prompt_arch, 'user', 'text')]

    # Get the llm reply
    resp_arch = generate_content(bedrock_runtime, message_arch, system_arch, inference_params, model_id)
    instruction = resp_arch.get('content')[0].get('text')

    # Define system prompt for coder
    system_coder = f"""
        You are an experienced developer in {program_language}.
        Your task is to generate high-quality code according to given instructions, and provide a concise explanation at the end.
        Make sure to include any imports required, and add comments for things that are non-obvious.
        NEVER write anything before the code.
        After you are done generating the code, check your work carefully to make sure there are no mistakes, errors, or inconsistencies. 
        If there are errors, list those errors in <error> tags, then generate a new version with those errors fixed. 
        If there are no errors, write "CHECKED: NO ERRORS" in <error> tags.
        """
    
    prompt_coder = f"""
        Write code according to the following instructions:
        <instruction>
        {instruction}
        </instruction>
    """

    message_coder = [format_message(prompt_coder, 'user', 'text')]

    # Get the llm reply
    resp_coder = generate_content(bedrock_runtime, message_coder, system_coder, inference_params, model_id)
    code_explanation = resp_coder.get('content')[0].get('text')

    return code_explanation
