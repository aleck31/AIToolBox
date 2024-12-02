# Copyright iX.
# SPDX-License-Identifier: MIT-0
import ast
from .logger import logger
from boto3 import Session
from botocore.exceptions import ClientError
from .config import DATABASE_CONFIG, DEFAULT_REGION


session = Session(region_name=DEFAULT_REGION)
ddb = session.resource('dynamodb')
setting_table = ddb.Table(DATABASE_CONFIG['setting_table'])


def get_secret(secret_name):
    '''Get user dict from Secrets Manager'''
    # Create a Secrets Manager client
    client = session.client(
        service_name='secretsmanager'
    )

    try:
        response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as ex:
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise ex

    # Decrypts secret using the associated KMS key.
    secret = ast.literal_eval(response['SecretString'])

    return secret


def translate_text(text, target_lang_code):
    '''
    Translates input text to the target language. Supported languages: 
    https://docs.aws.amazon.com/translate/latest/dg/what-is-languages.html
    '''
    client = session.client(
        service_name='translate'
    )

    try:
        # Call TranslateText API
        response = client.translate_text(
            Text=text,
            SourceLanguageCode='auto',
            TargetLanguageCode=target_lang_code)

        # Get translated text and detected source language code
        translated_text = response['TranslatedText']
        source_lang_code = response['SourceLanguageCode']

    except ClientError as ex:
        # Log error and set result & source_lang_code to None if fails
        logger.error(ex)

    return {
        'translated_text': translated_text,
        'source_lang_code': source_lang_code
    }


class AppConf:
    """
    A class to store and manage app configuration.
    """

    # Constants
    CODELANGS = ["Python", "GoLang", "Rust", "Java", "C++",
                 "Swift", "Javascript", "Typescript", "HTML", "SQL", "Shell"]
    # The list of style presets for Stable Diffusion
    # https://docs.aws.amazon.com/zh_cn/bedrock/latest/userguide/model-parameters-diffusion-1-0-text-image.html
    PICSTYLES = [
        "增强(enhance)", "照片(photographic)", "模拟胶片(analog-film)", "电影(cinematic)",
        "数字艺术(digital-art)",  "美式漫画(comic-book)",  "动漫(anime)", "3D模型(3d-model)", "低多边形(low-poly)",
        "线稿(line-art)", "等距插画(isometric)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",  
        "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)", "瓷砖纹理(tile-texture)"
    ]

    def update(self, key, value):
        # Update the value of a variable.
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError(f"Invalid configuration variable: {key}")


def get_model_id(model_name: str):
    '''Get model ID from settings table'''
    try:
        resp = setting_table.get_item(Key={'setting': 'models'})
        if 'Item' in resp:
            model_list = resp['Item'].get('value', [])
            for model in model_list:
                if model['name'] == model_name:
                    return model['model_id']
    except Exception as ex:
        logger.error(f"Failed to get model ID for {model_name}: {str(ex)}")
    return None
