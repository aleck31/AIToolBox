"""
Test script to verify Cognito User Pool authentication
"""
import os
import sys
import boto3
import json
from dotenv import load_dotenv

# Add parent directory to path to import from project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
load_dotenv()

def test_cognito_auth(username, password):
    """
    Test authentication against Cognito User Pool
    
    Parameters:
    -----------
    username : str
        Username to test
    password : str
        Password for the user
    
    Returns:
    --------
    dict
        Authentication result with tokens if successful
    """
    try:
        # Get Cognito User Pool details from environment
        user_pool_id = os.environ.get('USER_POOL_ID')
        client_id = os.environ.get('CLIENT_ID')
        region = os.environ.get('AWS_REGION')
        
        if not user_pool_id or not client_id or not region:
            print("ERROR: Missing required environment variables.")
            print(f"USER_POOL_ID: {'✓' if user_pool_id else '✗'}")
            print(f"CLIENT_ID: {'✓' if client_id else '✗'}")
            print(f"AWS_REGION: {'✓' if region else '✗'}")
            return None
        
        print(f"Testing authentication for user: {username}")
        print(f"User Pool ID: {user_pool_id}")
        print(f"Client ID: {client_id}")
        print(f"Region: {region}")
        
        # Create Cognito Identity Provider client
        client = boto3.client('cognito-idp', region_name=region)
        
        # Attempt authentication
        # Try ADMIN_USER_PASSWORD_AUTH first (requires admin privileges)
        try:
            print("Attempting ADMIN_USER_PASSWORD_AUTH flow...")
            response = client.admin_initiate_auth(
                UserPoolId=user_pool_id,
                ClientId=client_id,
                AuthFlow='ADMIN_USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
        except Exception as e:
            print(f"Admin auth failed: {str(e)}")
            print("Falling back to USER_PASSWORD_AUTH flow...")
            # Fall back to USER_PASSWORD_AUTH
            response = client.initiate_auth(
                ClientId=client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
        
        print("\n✅ Authentication successful!")
        print(f"Access Token expires in: {response.get('AuthenticationResult', {}).get('ExpiresIn', 'N/A')} seconds")
        
        # Return only necessary information (not the full tokens for security)
        result = {
            'success': True,
            'token_type': response.get('AuthenticationResult', {}).get('TokenType'),
            'expires_in': response.get('AuthenticationResult', {}).get('ExpiresIn'),
            'id_token_exists': bool(response.get('AuthenticationResult', {}).get('IdToken')),
            'access_token_exists': bool(response.get('AuthenticationResult', {}).get('AccessToken')),
            'refresh_token_exists': bool(response.get('AuthenticationResult', {}).get('RefreshToken'))
        }
        
        return result
        
    except client.exceptions.NotAuthorizedException:
        print("\n❌ Authentication failed: Incorrect username or password")
        return {'success': False, 'error': 'NotAuthorizedException'}
        
    except client.exceptions.UserNotFoundException:
        print("\n❌ Authentication failed: User does not exist")
        return {'success': False, 'error': 'UserNotFoundException'}
        
    except client.exceptions.UserNotConfirmedException:
        print("\n❌ Authentication failed: User is not confirmed")
        return {'success': False, 'error': 'UserNotConfirmedException'}
        
    except Exception as e:
        print(f"\n❌ Authentication failed: {str(e)}")
        return {'success': False, 'error': str(e)}

if __name__ == "__main__":
    # Check if username and password are provided as command line arguments
    if len(sys.argv) == 3:
        username = sys.argv[1]
        password = sys.argv[2]
    else:
        # Default test credentials
        username = "demo"
        password = "Demo@1357!"
    
    result = test_cognito_auth(username, password)
    
    if result and result.get('success'):
        print("\nToken information:")
        for key, value in result.items():
            if key != 'success':
                print(f"- {key}: {value}")
        sys.exit(0)
    else:
        sys.exit(1)
