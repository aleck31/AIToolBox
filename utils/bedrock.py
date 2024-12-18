# Copyright iX.
# SPDX-License-Identifier: MIT-0
"""Helper utilities for working with Amazon Bedrock from Python notebooks"""
from typing import Optional
from core.logger import logger
from utils.aws import get_aws_client

_BEDROCK_RUNTIME = None

def get_bedrock_client(
    region_name: Optional[str],
    assume_role_arn: Optional[str] = None,
    runtime: Optional[bool] = True,
):
    """Create a boto3 client for Amazon Bedrock, with optional configuration overrides

    Parameters
    ----------
    region_name :
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

    try:
        # Create the appropriate Bedrock client using centralized AWS configuration
        service_name = 'bedrock-runtime' if runtime else 'bedrock'
        bedrock_client = get_aws_client(
            service_name=service_name,
            region_name=region_name,
            assume_role_arn=assume_role_arn
        )
        
        if runtime:
            _BEDROCK_RUNTIME = bedrock_client
            
        logger.info(f"boto3 Bedrock {service_name} client successfully created!")
        logger.info(f"Endpoint: {bedrock_client._endpoint}")
        return bedrock_client
        
    except Exception as e:
        logger.error(f"Failed to create Bedrock client: {str(e)}")
        raise
