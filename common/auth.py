import boto3
from botocore.exceptions import ClientError
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer
from pydantic import BaseModel
from .logger import logger
from .config import COGNITO_CONFIG, DEFAULT_REGION


security = HTTPBearer()

class CognitoAuth:
    def __init__(self):
        self.client = boto3.client('cognito-idp', region_name=DEFAULT_REGION)
        self.user_pool_id = COGNITO_CONFIG['user_pool_id']
        self.client_id = COGNITO_CONFIG['client_id']
        self.refresh_tokens = {}  # Store refresh tokens per user
        self.access_tokens = {}   # Store access tokens per user

    def authenticate(self, username: str, password: str) -> dict:
        """
        Authenticate a user using Amazon Cognito
        
        Args:
            username (str): The username
            password (str): The password
            
        Returns:
            dict: Authentication result containing tokens and user attributes
            
        Raises:
            Exception: If authentication fails
        """
        try:
            # Initial authentication with password
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': username,
                    'PASSWORD': password
                }
            )
            
            # Store tokens for future use
            if 'AuthenticationResult' in response:
                self.refresh_tokens[username] = response['AuthenticationResult'].get('RefreshToken')
                self.access_tokens[username] = response['AuthenticationResult'].get('AccessToken')
                
                logger.info(f"User [{username}] authenticated successfully")
                return {
                    'success': True,
                    'tokens': response['AuthenticationResult'],
                    'error': None
                }
            else:
                logger.warning(f"User [{username}] authenticated failed: No AuthenticationResult")
                return {
                    'success': False,
                    'tokens': None,
                    'error': 'Authentication failed'
                }
            
        except self.client.exceptions.NotAuthorizedException:
            logger.warning(f"Invalid credentials for user [{username}]")
            return {
                'success': False,
                'tokens': None,
                'error': 'Invalid username or password'
            }
            
        except self.client.exceptions.UserNotFoundException:
            logger.warning(f"User [{username}] not found")
            return {
                'success': False,
                'tokens': None,
                'error': 'User not found'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Authentication error for user [{username}]: {error_code} - {error_message}")
            return {
                'success': False,
                'tokens': None,
                'error': error_message
            }

    def verify_token(self, token: str) -> bool:
        """
        Verify an access token from Cognito
        
        Args:
            token (str): The access token to verify
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            response = self.client.get_user(
                AccessToken=token
            )
            return True
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return False

    def get_token_for_user(self, username: str) -> str:
        """Get stored access token for user"""
        return self.access_tokens.get(username, '')

    def logout(self, token: str) -> bool:
        """
        Logout a user by invalidating their access token
        
        Args:
            token (str): The access token to invalidate
            
        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            # Get user info before invalidating token
            self.client.global_sign_out(
                AccessToken=token
            )
            
            try:
                # Get username from token
                user_info = self.client.get_user(AccessToken=token)
                username = user_info['Username']
                
                # Clear stored tokens
                if username in self.access_tokens:
                    del self.access_tokens[username]
                if username in self.refresh_tokens:
                    del self.refresh_tokens[username]
            except:
                pass  # Token might already be invalid
                
            logger.info("User logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False

# Initialize the auth handler
cognito_auth = CognitoAuth()

# FastAPI dependency
def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    if not cognito_auth.verify_token(token):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token
