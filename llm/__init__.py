# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
import json
from utils import bedrock
from botocore.exceptions import ClientError


# os.environ["BEDROCK_ASSUME_ROLE"] = "<YOUR_ROLE_ARN>"  # E.g. "arn:aws:..."
# os.environ["AWS_DEFAULT_REGION"] = "<REGION_CODE>"  # E.g. "us-west-2"
# It is recommended to use IAM role authorization

# Create new bedrock client
bedrock_runtime = bedrock.get_bedrock_client(
    region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
    assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE")
)


def test_connection():
    """
    Validate the connection by list the available foundation models.

    :return: The list of available bedrock foundation models.
    """
    bedrock_client = bedrock.get_bedrock_client(
        region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
        assumed_role=os.environ.get("BEDROCK_ASSUME_ROLE"),
        runtime=False
    )

    try:
        response = bedrock_client.list_foundation_models(
            byProvider="anthropic")
        models = response["modelSummaries"]
        # print("Got %s foundation models.", len(models))
        return models

    except ClientError as err:
        print(f'Err:{err}')
        raise


def moc_chat(name, message, history):
    history = history or []
    message = message.lower()
    salutation = "Good morning" if message else "Good evening"
    greeting = f"{salutation} {name}. {message} degrees today"
    return greeting


# Helper function to pass prompts and inference parameters
def generate_content(messages, system, params, model_id, runtime=bedrock_runtime):
    """
    Invokes Bedrock LLM to run inference using the input provided in the request body.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model.html

    :return: Inference response from the model.
    """

    params['system'] = system
    params['messages'] = messages

    try:
        response = runtime.invoke_model(
            modelId=model_id,
            body=json.dumps(params)
        )

        resp_body = json.loads(response.get('body').read())
        # input_tokens = resp_body["usage"]["input_tokens"]
        # output_tokens = resp_body["usage"]["output_tokens"]
        # output_list = resp_body.get("content", [])
        return resp_body

    except ClientError as err:
        print(
            "Invoke LLM faild. Error code: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise


def generate_stream(messages, system, params, model_id, runtime=bedrock_runtime):
    """
    Invokes Bedrock LLM to run inference using the input provided, return the response in a stream.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/invoke_model_with_response_stream.html

    :return: Inference response from the model.
    """

    params['system'] = system
    params['messages'] = messages

    try:
        # print(f"User_Prompt: {messages}")
        response = runtime.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(params)
        )
        return response

    except ClientError as err:
        print(
            "Invoke LLM faild. Error code: %s: %s",
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        raise
