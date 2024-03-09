# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
import json
from utils import bedrock
from botocore.exceptions import ClientError


# os.environ["BEDROCK_ASSUME_ROLE"] = "<YOUR_ROLE_ARN>"  # E.g. "arn:aws:..."
# 推荐使用 IAM role 授权方式
# Create new bedrock client
bedrock_runtime = bedrock.get_bedrock_client(
    assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
    region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
)

boto3_bedrock = bedrock.get_bedrock_client(
    assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE", None),
    region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
    runtime=False
)


def test_connection():
    # Validate the connection
    model_list = boto3_bedrock.list_foundation_models()
    return model_list


def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting


# Helper function to pass prompts and inference parameters
def generate_content(messages, system, params, model_id, runtime=bedrock_runtime):
    params['system'] = system
    params['messages'] = messages
    body=json.dumps(params)
    
    try:
        response = runtime.invoke_model(body=body, modelId=model_id)
    except ClientError as ex:
        print(f"Err: {ex}")
        raise

    response_body = json.loads(response.get('body').read())

    return response_body