# Copyright iX.
# SPDX-License-Identifier: MIT-0
import io
import re
import json
import base64
import random
from PIL import Image
from . import bedrock_runtime


model_id = "stability.stable-diffusion-xl-v0"
# model_id = "stability.stable-diffusion-xl-v1"

negative_prompts = [
    "lower",
    "blurry",
    "low resolution",
    "poorly rendered",
    "poor background details"
]
clip_guidance_preset = "FAST_GREEN" # (e.g. FAST_BLUE FAST_GREEN NONE SIMPLE SLOW SLOWER SLOWEST)
sampler = "K_DPMPP_2S_ANCESTRAL" # (e.g. DDIM, DDPM, K_DPMPP_SDE, K_DPMPP_2M, K_DPMPP_2S_ANCESTRAL, K_DPM_2, K_DPM_2_ANCESTRAL, K_EULER, K_EULER_ANCESTRAL, K_HEUN, K_LMS)
'''
Recommended image sizes for different ratios:
21:9 - 1536 x 640
16:9 - 1344 x 768
3:2 - 1216 x 832
5:4 - 1152 x 896
1:1 - 1024 x 1024
'''
width = 768


def text_image(prompt:str, negative:str, style, step:int, seed:int):
    # chang seed from Double to Int
    seed = random.randrange(10000000, 99999999) if seed == -1 else int(seed)
    # extracts the style string contained within ()
    if style:
        pattern = r'\((.*?)\)'
        style = re.findall(pattern, style)[0]
    else:
        style = 'base'
    
    negative_prompts.append(negative)

    request_body = json.dumps({
        "text_prompts": (
            [{"text": prompt, "weight": 1.0}]
            + [{"text": negprompt, "weight": -1.0} for negprompt in negative_prompts]
        ),
        "steps": step,
        "seed": seed,
        "style_preset": style,
        "clip_guidance_preset": clip_guidance_preset,
        "sampler": sampler,
        "width": width,
        "cfg_scale": 5
    })

    response = bedrock_runtime.invoke_model(
        body=request_body, 
        modelId=model_id,
        accept = "application/json",
        contentType = "application/json"
    )
    response_body = json.loads(response.get("body").read())
    # print(response_body["result"])
    base_64_img_str = response_body["artifacts"][0].get("base64")
    decoded_img = Image.open(io.BytesIO(base64.b64decode(base_64_img_str)))
    # decoded_img = Image.open(io.BytesIO(base64.decodebytes(bytes(base_64_img_str, "utf-8"))))

    return decoded_img
