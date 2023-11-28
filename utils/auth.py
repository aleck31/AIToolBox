# Copyright iX.
# SPDX-License-Identifier: MIT-0
import ast
import hashlib
import boto3
from botocore.exceptions import ClientError



region_name = "ap-southeast-1"
table_name = 'aibox_users'
dynamodb = boto3.resource('dynamodb', region_name=region_name)
user_table = dynamodb.Table('aibox_users')
secret_name = "aitoolkit-login"


def verify_user(username, password):
    '''Verify username and password for login'''
    # Query DynamoDB table for user
    try:
        # resp = user_table.get_item(Key={'userId' : '1001'})
        resp = user_table.get_item(Key={'username': username}) 
    except ClientError as ex:
        # raise ex
        return False

    # Check if user exists
    if 'Item' in resp:
        # Get stored user item
        user = resp['Item']

        # Verify  password
        encrypted_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if encrypted_password == user.get('password'):
            return True
        else:
            return False
    else:
        return False
    

def get_userdict():
    '''Get user dict from Secrets Mnaager'''
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
