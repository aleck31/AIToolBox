# Copyright iX.
# SPDX-License-Identifier: MIT-0
from core.integration.module_config import module_config
from core.integration.service_factory import ServiceFactory
from core.logger import logger
from utils import format_msg


def vision_analyze_gemini(file_path: str, user_requirement=None):
    """Vision analysis using Gemini model"""
    try:
        # Get vision service from factory
        vision_service = ServiceFactory.get_service('vision')
        llm_vision = vision_service.get_model('gemini')
    except Exception as e:
        logger.warning(f"Failed to initialize vision model: {e}")
        yield "Failed to initialize vision model. Please try again later."
        return

    # Get system prompt from configuration
    system_prompt = module_config.get_system_prompt('vision') or "Analyze or describe the multimodal content according to the requirement:"

    # Define prompt template
    user_requirement = user_requirement or "Describe the media or document in detail."
    text_prompt = f"{system_prompt}\n{user_requirement}"

    try:
        # Use the service to analyze the image
        for chunk in vision_service.analyze_image(
            file_path=file_path,
            prompt=text_prompt,
            stream=True
        ):
            yield chunk

    except Exception as ex:
        logger.error(ex)
        yield "Unfortunately, an issue occurred, no content was generated by the model."


def vision_analyze_claude(file_path: str, user_requirement=None):
    """Vision analysis using Claude model"""
    try:
        # Get vision service from factory
        vision_service = ServiceFactory.get_service('vision')
        
        # Get system prompt from configuration
        system_prompt = module_config.get_system_prompt('vision') or '''
            Analyze or describe the multimodal content according to the user's requirement.
            Respond using the language consistent with the user or the language specified in the <requirement> </requirement> tags.
            '''

        user_requirement = user_requirement or "Describe the picture or document in detail."
        formated_msg = format_msg(
            {
                "text": f"<requirement>{user_requirement}</requirement>",
                "files": [file_path]
            },
            "user"
        )

        # Use the service to analyze the image
        for chunk in vision_service.analyze_image(
            file_path=file_path,
            prompt=formated_msg,
            system_prompt=system_prompt,
            model='claude',
            stream=True
        ):
            yield chunk

    except Exception as ex:
        logger.error(f"Error in vision_analyze_claude: {ex}")
        yield "Unfortunately, an issue occurred while analyzing the image."
