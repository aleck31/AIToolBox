# Copyright iX.
# SPDX-License-Identifier: MIT-0
import io
import re
import json
import base64
import random
from PIL import Image
from . import bedrock_runtime
from common import USER_CONF, translate_text
from common.logger import logger
from botocore.exceptions import ClientError


negative_prompts = [
    "lower",
    "blurry",
    "low resolution",
    "poorly rendered",
    "poor background details"
]

# Stability.ai Diffusion 1.0 text to image inference parameters:
# https://docs.aws.amazon.com/bedrock/latest/userguide/model-parameters-diffusion-1-0-text-image.html
optional_parms_xl = {
    # (e.g. FAST_BLUE FAST_GREEN NONE SIMPLE SLOW SLOWER SLOWEST)
    'clip_guidance_preset': 'FAST_GREEN',
    # (e.g. DDIM, DDPM, K_DPMPP_SDE, K_DPMPP_2M, K_DPMPP_2S_ANCESTRAL, K_DPM_2, K_DPM_2_ANCESTRAL, K_EULER, K_EULER_ANCESTRAL, K_HEUN, K_LMS)
    'sampler': 'K_DPMPP_2S_ANCESTRAL' ,
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

def random_seed():
    # Maximum 4294967295
    return random.randrange(1, 4294967295)


def text_image(prompt:str, negative:str, style, step:int, seed, is_random):
    """
    Invokes Bedrock LLM to run inference using the prompt and inference parameters:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model.html

    :return: image and random seed
    """
    model_id = USER_CONF.get_model_id('image')

    # change seed from Double to Int
    seed = random_seed() if is_random else int(seed)
    # extracts the style string contained within ()
    if style:
        pattern = r'\((.*?)\)'
        style = re.findall(pattern, style)[0]
    else:
        style = 'enhance'
    
    prompt = translate_text(prompt, 'en').get('translated_text')

    negative_prompts.append(negative)

    if model_id == 'stability.stable-diffusion-xl-v1':
        request_body = {
            'text_prompts': (
                [{'text': prompt, 'weight': 1.0}]
                + [{'text': negprompt, 'weight': -1.0} for negprompt in negative_prompts]
            ),
            'steps': step,
            'seed': seed,
            'style_preset': style
        }
        request_body.update(optional_parms_xl)
    else:
        request_body = {
            'prompt': f'{prompt}, {style}',
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
            accept = "application/json",
            contentType = "application/json"
        )
        resp_body = json.loads(resp.get("body").read())
        # print(resp_body["result"])

        # Log token usage and metrics
        logger.info(f"Seeds: {resp_body.get('seeds')} | Finish reason: {resp_body.get('finish_reasons')}")
        
        if model_id == 'stability.stable-diffusion-xl-v1':
            base_64_img_str = resp_body.get("artifacts")[0].get("base64")
        else:
            base_64_img_str = resp_body.get("images")[0]
        decoded_img = Image.open(io.BytesIO(base64.b64decode(base_64_img_str)))

        return decoded_img, seed
    
    except ClientError as ex:
        logger.error(f"Invoke model faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")
