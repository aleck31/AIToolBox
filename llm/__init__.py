# Copyright iX.
# SPDX-License-Identifier: MIT-0
import os
import json
from utils import bedrock
from common.logs import log_info, log_error
from botocore.exceptions import ClientError


# os.environ["BEDROCK_ASSUME_ROLE"] = "<YOUR_ROLE_ARN>"  # E.g. "arn:aws:..."
# os.environ["AWS_DEFAULT_REGION"] = "<REGION_CODE>"  # E.g. "us-west-2"
# It is recommended to use IAM role authorization

# Create new bedrock client
bedrock_runtime = bedrock.get_bedrock_client(
    region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
    assume_role_arn=os.environ.get("BEDROCK_ASSUME_ROLE")
)


def test_connection():
    """
    Validate the connection by list the available foundation models.

    :return: The list of available bedrock foundation models.
    """
    bedrock_client = bedrock.get_bedrock_client(
        region=os.environ.get("AWS_DEFAULT_REGION", "us-west-2"),
        assume_role_arn=os.environ.get("BEDROCK_ASSUME_ROLE"),
        runtime=False
    )

    try:
        response = bedrock_client.list_foundation_models(
            byProvider="anthropic")
        models = response["modelSummaries"]
        # print("Got %s foundation models.", len(models))
        return models

    except ClientError as ex:
        log_error(ex)


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

    except ClientError as ex:
        log_error(f"Invoke LLM faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")


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

    except ClientError as ex:
        print(params)
        log_error(f"Invoke LLM faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")


def bedrock_generate(messages, system, model_id, params, additional_params=None, runtime=bedrock_runtime):
    """
    Invokes Bedrock LLM to run inference using the input provided and return the response in a stream.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse.html

    :return: Inference response from the model.
    """

    try:
        # print(f"User_Prompt: {messages}")
        resp = runtime.converse(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=params,
            additionalModelRequestFields = additional_params
        )

        # Log token usage and metrics.
        # token_usage = resp['usage']
        # log_info("Input tokens: %s", token_usage['inputTokens'])
        # log_info("Output tokens: %s", token_usage['outputTokens'])
        # log_info("Total tokens: %s", token_usage['totalTokens'])
        # log_info("Stop reason: %s", response['stopReason'])
        # token_metrics = resp['metrics']
        # log_info("Latency: %s", token_metrics['latencyMs'])
        
        resp_message = resp['output']['message']

        return resp_message

    except ClientError as ex:
        print(messages)
        log_error(f"Invoke LLM [{model_id}] faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")


def bedrock_stream(messages, system,  model_id, params, additional_params=None, runtime=bedrock_runtime):
    """
    Invokes Bedrock LLM to run inference using the input provided and return the response in a stream.
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime/client/converse_stream.html

    :return: Inference response from the model.
    """

    try:
        # print(f"User_Prompt: {messages}")
        streaming_resp = runtime.converse_stream(
            modelId=model_id,
            messages=messages,
            system=system,
            inferenceConfig=params,
            additionalModelRequestFields = additional_params
        )
        return streaming_resp

    except ClientError as ex:
        log_error(f"Invoke LLM {model_id} faild. {ex.response['Error']['Code']} - {ex.response['Error']['Message']}")        
