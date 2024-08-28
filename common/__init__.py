# Copyright iX.
# SPDX-License-Identifier: MIT-0
import ast
import hashlib
from .logs import log_info, log_error
from boto3 import Session
from botocore.exceptions import ClientError


DEFAULT_REGION = "ap-southeast-1"
CONFIG_TAB = 'aibox-db'

session = Session(region_name=DEFAULT_REGION)
ddb = session.resource('dynamodb')
app_table = ddb.Table(CONFIG_TAB)


def verify_user(username: str, password: str):
    '''Verify username and password for login'''
    ddb = session.resource('dynamodb')
    app_table = ddb.Table(CONFIG_TAB)

    # Query DynamoDB table for user
    try:
        # resp = user_table.get_item(Key={'userId' : '1001'})
        resp = app_table.get_item(Key={'user': username})
    except ClientError as ex:
        log_error(ex)
        return False

    # Check if user exists
    if 'Item' in resp:
        # Get stored user item
        user = resp['Item']

        # Verify  password
        encrypted_password = hashlib.sha256(
            password.encode("utf-8")).hexdigest()
        if encrypted_password == user.get('password'):
            log_info(f"[{username}] logged in successfully.")
            return True
        else:
            log_error(f"[{username}] failed to log in.")
            return False
    else:
        return False


# secret_name = "aitoolkit-login"
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
    Supported languages: 
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
        log_error(ex)

    return {
        'translated_text': translated_text,
        'source_lang_code': source_lang_code
    }


class AppConf:
    """
    A class to store and manage app configuration.
    """

    # Constants
    STYLES = ["正常", "幽默", "极简", "理性", "可爱"]
    LANGS = ["en_US", "zh_CN", "zh_TW", "ja_JP", "de_DE", "fr_FR"]
    CODELANGS = ["Python", "GoLang", "Rust", "Java", "C++",
                 "Swift", "Javascript", "Typescript", "HTML", "SQL", "Shell"]
    PICSTYLES = [
        "增强(enhance)", "照片(photographic)", "老照片(analog-film)",
        "电影(cinematic)", "模拟电影(analog-film)", "美式漫画(comic-book)",  "动漫(anime)", "线稿(line-art)",
        "3D模型(3d-model)", "低多边形(low-poly)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",
        "数字艺术(digital-art)", "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)"
    ]
    # initialize model list with default values.
    # https://docs.aws.amazon.com/bedrock/latest/userguide/model-ids.html#model-ids-arns
    MODEL_LIST = [
        {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "name": "claude3"
        },
        {
            "model_id": "gemini-1.5-flash",
            "name": "gemini-chat"
        },
        {
            "model_id": "gemini-1.5-pro",
            "name": "gemini-vision"
        },
        {
            "model_id": "anthropic.claude-3-haiku-20240307-v1:0",
            "name": "translate"
        },
        {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "name": "rewrite"
        },
        {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "name": "summary"
        },
        {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "name": "vision"
        },
        {
            "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
            "name": "code"
        },
        {
            "model_id": "stability.stable-diffusion-xl-v1",
            "name": "image"
        }
    ]

    def update(self, key, value):
        # Update the value of a variable.
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError(f"Invalid configuration variable: {key}")


def get_model_list(username: str):
    '''Get the user's model list from database.'''
    try:
        resp = app_table.get_item(Key={'user': username})

        # If data is found, return the 'models' field data
        if 'Item' in resp:
            model_list = resp['Item'].get('models')
        else:
            model_list = None

        return model_list

    except Exception as ex:
        log_error(f"Error getting model list for user {username}: {ex}")
        return None


def get_model_id(username: str, model_name: str):
    '''Get the model ID specified by the user from database'''
    try:
        resp = app_table.get_item(Key={'user': username})

        # If data is found, return the 'models' field data
        if 'Item' in resp:
            model_list = resp['Item'].get('models', [])
            for model in model_list:
                # If matching model name is found
                if model['name'] == model_name:
                    # Return model ID
                    return model['model_id']

    except Exception as ex:
        log_error(str(ex))
        return None


class UserConf(object):
    """
    A class to store and manage user configuration.
    """

    def __init__(self, username):
        self.username = username
        if not get_model_list(self.username):
            self.model_list = AppConf.MODEL_LIST
            self.set_model_list(self.model_list)
        else:
            self.model_list = get_model_list(self.username)

    def set_user(self, new_username):
        self.username = new_username
        self.model_list = get_model_list(self.username)

    def get_model_id(self, model_name):
        return get_model_id(self.username, model_name)

    def set_model_list(self, model_list: list):
        try:
            app_table.update_item(
                Key={
                    'user': self.username
                },
                UpdateExpression='SET models = :model_list',
                ExpressionAttributeValues={
                    ':model_list': model_list
                },
                ReturnValues='UPDATED_NEW'
            )
            # update self.model_list
            self.model_list = get_model_list(self.username)
        except Exception as ex:
            log_error(str(ex))
            return False


# Default user configuration without login
USER_CONF = UserConf('demo')
