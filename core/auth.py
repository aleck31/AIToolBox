"""
Amazon Cognito authentication provider
"""
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Optional
from core.config import env_config
from core.logger import logger


class CognitoAuth:
    """Amazon Cognito authentication provider"""
    
    def __init__(self):
        """Initialize Cognito client with configuration"""
        self.client = boto3.client('cognito-idp', region_name=env_config.default_region)
        self.user_pool_id = env_config.cognito_config['user_pool_id']
        self.client_id = env_config.cognito_config['client_id']
        self.refresh_tokens = {}  # {username: refresh_token}
        self.access_tokens = {}   # {username: access_token}
        self.user_info = {}       # {username: {user_attributes}}

    def authenticate(self, username: str, password: str) -> Dict:
        """
        Authenticate a user using Amazon Cognito
        
        Args:
            username: The username
            password: The password
            
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
            
            # Store tokens and user info
            if 'AuthenticationResult' in response:
                self.refresh_tokens[username] = response['AuthenticationResult'].get('RefreshToken')
                self.access_tokens[username] = response['AuthenticationResult'].get('AccessToken')
                
                # Get and store user info
                user_info = self.client.get_user(
                    AccessToken=response['AuthenticationResult']['AccessToken']
                )
                self.user_info[username] = {
                    'username': user_info['Username'],
                    'attributes': {attr['Name']: attr['Value'] for attr in user_info['UserAttributes']}
                }
                
                logger.info(f"User [{username}] authenticated successfully")
                return {
                    'success': True,
                    'tokens': response['AuthenticationResult'],
                    'error': None
                }
            else:
                logger.warning(f"User [{username}] authentication failed: No AuthenticationResult")
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
        """Verify an access token with Cognito"""
        # Check if token exists in our stored access tokens
        if token in self.access_tokens.values():
            try:
                # Let Cognito verify if token is still valid
                self.client.get_user(AccessToken=token)
                return True
            except self.client.exceptions.NotAuthorizedException:
                # Token expired - remove from storage
                self._remove_token(token)
                return False
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                return False
                
        # If token not in memory, verify with Cognito
        try:
            response = self.client.get_user(AccessToken=token)
            username = response['Username']
            
            # Store verified token and user info
            self.access_tokens[username] = token
            self.user_info[username] = {
                'username': username,
                'attributes': {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            }
            return True
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return False

    def _remove_token(self, token: str) -> None:
        """Remove token and associated data from storage"""
        for username, stored_token in self.access_tokens.items():
            if stored_token == token:
                del self.access_tokens[username]
                if username in self.refresh_tokens:
                    del self.refresh_tokens[username]
                if username in self.user_info:
                    del self.user_info[username]
                break

    def get_user_info(self, token: str) -> Optional[Dict]:
        """Get user information using token"""
        # First check if we have user info for this token
        for username, stored_token in self.access_tokens.items():
            if stored_token == token and username in self.user_info:
                try:
                    # Verify token is still valid with Cognito
                    self.client.get_user(AccessToken=token)
                    return self.user_info[username]
                except self.client.exceptions.NotAuthorizedException:
                    # Token expired - clean up storage
                    self._remove_token(token)
                    return None
                except Exception:
                    return None
        
        # If not found in memory, get from Cognito
        try:
            response = self.client.get_user(AccessToken=token)
            username = response['Username']
            user_info = {
                'username': username,
                'attributes': {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            }
            
            # Store for future use
            self.access_tokens[username] = token
            self.user_info[username] = user_info
            return user_info
        except Exception as e:
            logger.error(f"Error getting user info: {str(e)}")
            return None

    def get_token_for_user(self, username: str) -> str:
        """Get stored access token for user"""
        return self.access_tokens.get(username, '')

    def logout(self, token: str) -> bool:
        """
        Logout a user by invalidating their access token
        
        Args:
            token: The access token to invalidate
            
        Returns:
            bool: True if logout successful, False otherwise
        """
        try:
            # Get user info before invalidating token
            self.client.global_sign_out(
                AccessToken=token
            )
            
            # Clean up stored data
            self._remove_token(token)
            logger.info("User logged out successfully")
            return True
            
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return False

# Create a singleton instance
cognito_auth = CognitoAuth()


# FastAPI dependency
'''
security = HTTPBearer()

def verify_api_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict:
    """
    FastAPI dependency for verifying API token and getting the current authenticated user
    
    Args:
        credentials: The HTTP Authorization credentials
        
    Returns:
        Dict: User information if token is valid
        
    Raises:
        HTTPException: If authentication is invalid
    """
    token = credentials.credentials
    user_info = cognito_auth.get_user_info(token)
    
    if not user_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user_info
'''
