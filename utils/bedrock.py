# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Bedrock from Python notebooks"""
# Python Built-Ins:
import os
from typing import Optional

# External Dependencies:
import boto3
from botocore.config import Config


_BEDROCK_RUNTIME = None


def get_bedrock_client(
    region: Optional[str],
    assumed_role: Optional[str] = None,
    runtime: Optional[bool] = True,
):
    """Create a boto3 client for Amazon Bedrock, with optional configuration overrides

    Parameters
    ----------
    region :
        AWS Region name in which the service should be called (e.g. "us-east-1").
    assumed_role :
        Optional ARN of an AWS IAM role to assume for calling the Bedrock service. If not
        specified, the current active credentials will be used.
    runtime :
        Optional choice of getting different client to perform operations with the Amazon Bedrock service.
        Bedrock.Client: 
            describes the API operations for creating and managing Bedrock models.
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock.html
        BedrockRuntime.Client: 
            describes the API operations for running inference using Bedrock models.
            https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-runtime.html
    """

    global _BEDROCK_RUNTIME
    if runtime and _BEDROCK_RUNTIME:
        return _BEDROCK_RUNTIME

    if assumed_role:
        print(f"  Using role: {assumed_role}", end='')
        sts = session.client("sts")
        response = sts.assume_role(
            RoleArn=str(assumed_role),
            RoleSessionName="bedrock-llm-1"
        )
        print(" ... successful!")
        client_kwargs["aws_access_key_id"] = response["Credentials"]["AccessKeyId"]
        client_kwargs["aws_secret_access_key"] = response["Credentials"]["SecretAccessKey"]
        client_kwargs["aws_session_token"] = response["Credentials"]["SessionToken"]

    session_kwargs = {"region_name": region}
    client_kwargs = {**session_kwargs}

    profile_name = os.environ.get("AWS_PROFILE")
    if profile_name:
        print(f"  Using profile: {profile_name}")
        session_kwargs["profile_name"] = profile_name

    session = boto3.Session(**session_kwargs)

    retry_config = Config(
        region_name=region,
        retries={
            "max_attempts": 10,
            "mode": "standard",
        },
    )
    bedrock_client = session.client(
        service_name=['bedrock', 'bedrock-runtime'][runtime],
        config=retry_config,
        **client_kwargs
    )

    print("boto3 Bedrock client successfully created!")
    print(bedrock_client._endpoint)
    return bedrock_client
