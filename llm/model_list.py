"""
LLM model configurations
"""
from . import LLMModel, LLM_CAPABILITIES


# Default model list
DEFAULT_MODELS = [
    LLMModel(
        name='claude3.7-sonnet-thinking',
        model_id='us.anthropic.claude-3-7-sonnet-20250219-v1:0',
        api_provider='Bedrock',
        category='vision',
        description='Claude 3.7 Sonnet model offer extended thinking—the ability to solve complex problems with careful, step-by-step reasoning.',
        vendor='Anthropic',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            reasoning=True,
            context_window=200*1024
        )
    ),
    LLMModel(
        name='claude3.6-sonnet',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        api_provider='Bedrock',
        category='vision',
        description='Claude 3.5 Sonnet v2 model for general use',
        vendor='Anthropic',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=200*1024
        )
    ),
    LLMModel(
        name='gemini 1.5 pro',
        model_id='gemini-1.5-pro',
        api_provider='Gemini',
        category='vision',
        description='Gemini Pro model for text and vision',
        vendor='Google',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=200*1024
        )
    ),
    LLMModel(
        name='gemini 2.0 flash',
        model_id='gemini-2.0-flash',
        api_provider='Gemini',
        category='vision',
        description='Gemini Flash model for text and vision',
        vendor='Google',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=1024*1024
        )
    ),
    LLMModel(
        name= "Nova Pro",
        category='vision',
        api_provider= "Bedrock",
        description= "Nova Pro is a vision understanding foundation model. It is multilingual and can reason over text, images and videos.",
        model_id= "amazon.nova-pro-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document', 'video'],
            output_modality=['text'],
            streaming=True,
            tool_use=True
        )
    ),
    LLMModel(
        name= "Nova Canvas",
        category='image',
        api_provider= "BedrockInvoke",
        description= "Nova image generation model. It generates images from text and allows users to upload and edit an existing image. ",
        model_id= "amazon.nova-canvas-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['image']
        )
    ),
    LLMModel(
        name='stable-diffusion',
        model_id='stability.stable-image-ultra-v1:0',
        api_provider='BedrockInvoke',
        category='image',
        description='Stable Diffusion Ultra for image generation',
        vendor='Stability AI',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['image']
        )
    ),
    LLMModel(
        name= "Nova Reel",
        category='video',
        api_provider= "BedrockInvoke",
        description= "Nova video generation model. It generates short high-definition videos, up to 9 seconds long from input images or a natural language prompt.",
        model_id= "amazon.nova-reel-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['video']
        )
    ),
    LLMModel(
        name='DeepSeek-R1',
        model_id='us.deepseek.r1-v1:0',
        api_provider='Bedrock',
        category='text',
        description='DeepSeek R1 model for text generation',
        vendor='DeepSeek',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            reasoning=True,
            context_window=32*1024
        )
    )
]
