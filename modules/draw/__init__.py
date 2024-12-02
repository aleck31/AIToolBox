# Copyright iX.
# SPDX-License-Identifier: MIT-0
import io
import re
import json
import base64
import random
from PIL import Image
from botocore.exceptions import ClientError
from common.logger import logger
from common.llm_config import get_default_model
from llm.claude import bedrock_runtime, bedrock_generate


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

# Stability.ai Diffusion 1.0 text to image inference parameters:
# https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-diffusion-1-0-text-image.html
optional_parms_xl = {
    # (e.g. FAST_BLUE FAST_GREEN NONE SIMPLE SLOW SLOWER SLOWEST)
    'clip_guidance_preset': 'FAST_GREEN',
    # (e.g. DDIM, DDPM, K_DPMPP_SDE, K_DPMPP_2M, K_DPMPP_2S_ANCESTRAL, K_DPM_2, K_DPM_2_ANCESTRAL, K_EULER, K_EULER_ANCESTRAL, K_HEUN, K_LMS)
    'sampler': 'K_DPMPP_2S_ANCESTRAL',
    # The image dimension must be one of: 1024x1024, 1152x896, 1216x832, 1344x768, or 1536x640
    'height': 1152,
    'width': 896,
    'cfg_scale': 7
}

# Stability.ai SD3 model text to image inference parameters:
# https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-diffusion-stable-ultra-text-image-request-response.html
optional_parms_sd3 = {
    'mode': 'text-to-image',
    # the aspect ratio of the generated imag, Enum 16:9, 1:1, 21:9, 2:3, 3:2, 4:5, 5:4, 9:16, 9:21
    'aspect_ratio': '2:3',
    # 'height': 1152,    'width': 896,
    # 'output_format': ''
}

negative_prompts = [
    "lower",
    "blurry",
    "low resolution",
    "poorly rendered",
    "poor background details"
]


def random_seed():
    # Maximum 4294967295
    return random.randrange(1, 4294967295)


def prompt_optimizer(prompt):
    '''
    Convert simple Stable Diffusion prompt to a highly optimized prompt
    '''

    # Define prompts for prompt optimizer
    sys_prompt = """
        You are now a Stable Diffusion prompt optimization expert. 
        I will give you a basic prompt, and you need to optimize and expand it to achieve better image generation. 
        During the optimization process, please follow these guidelines:
        1. Add specific details to enrich the description
        2. Use descriptive adjectives to enhance visual effects
        3. Specify art styles or painting techniques
        4. Describe lighting and atmosphere
        5. Mention camera angles and shot types
        6. Reference specific artists or works for inspiration
        7. Mention color palettes
        8. Describe textures and materials
        9. Use bracketed weights to emphasize certain elements, e.g., [important element:1.5]
        10. Combine multiple concepts
        11. Pay attention to word order, putting the most important elements first
        12. Consider adding suggestions from prompt libraries or generators.

        Please respond in English only with the succinct context and nothing else.
        """

    msg_prompt = {
        'role': 'user',
        'content': [{"text": prompt}]
    }

    # Get model ID from module config
    model_id = get_default_model('draw')

    # Get the llm reply
    resp = bedrock_generate(
        messages=[msg_prompt],
        system=[{'text': sys_prompt}],
        model_id=model_id,
        params=inference_params
    )

    opt_prompt = resp.get('content')[0].get('text')

    return opt_prompt


def text_image(prompt: str, negative: str, style, step: int, seed, is_random):
    """
    Invokes Bedrock LLM to run inference using the prompt and inference parameters:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model.html

    :return: image and random seed
    """
    # Get model ID from module config
    model_id = get_default_model('draw')

    # change seed from Double to Int
    seed = random_seed() if is_random else int(seed)
    # extracts the style string contained within ()
    if style:
        pattern = r'\((.*?)\)'
        style = re.findall(pattern, style)[0]
    else:
        style = 'enhance'

    prompt = prompt_optimizer(prompt)

    negative_prompts.append(negative)

    if model_id == 'stability.stable-diffusion-xl-v1':
        request_body = {
            'text_prompts': (
                [{'text': prompt, 'weight': 1.0}]
                + [{'text': negprompt, 'weight': -1.0}
                    for negprompt in negative_prompts]
            ),
            'steps': step,
            'seed': seed,
            'style_preset': style
        }
        request_body.update(optional_parms_xl)
    else:
        request_body = {
            'prompt': f'{prompt}, style preset: {style}',
            'negative_prompt': ''.join(negative_prompts),
            'seed': seed
        }
        request_body.update(optional_parms_sd3)

    try:
        logger.info(f"*text_to_image* invoke the model [{model_id}]")
        logger.info(f"text2image prompt: {prompt}")

        resp = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body),
            accept="application/json",
            contentType="application/json"
        )
        resp_body = json.loads(resp.get("body").read())
        # print(resp_body["result"])

        # Log token usage and metrics
        logger.info(
            f"Seeds: {resp_body.get('seeds')} | Finish reason: {resp_body.get('finish_reasons')}")

        if model_id == 'stability.stable-diffusion-xl-v1':
            base_64_img_str = resp_body.get("artifacts")[0].get("base64")
        else:
            base_64_img_str = resp_body.get("images")[0]
        decoded_img = Image.open(io.BytesIO(base64.b64decode(base_64_img_str)))

        return decoded_img, seed

    except ClientError as ex:
        logger.error(
            f"Invoke model faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")
