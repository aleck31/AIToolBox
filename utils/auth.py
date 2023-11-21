# Copyright iX.
# SPDX-License-Identifier: MIT-0
import ast
import boto3
from botocore.exceptions import ClientError



secret_name = "aitoolkit-login"
region_name = "ap-southeast-1"

def get_userdict():
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
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
    user_dict = ast.literal_eval(response['SecretString'])

    return user_dict
