"""
Amazon Cognito authentication provider
"""
import boto3
import time
from botocore.exceptions import ClientError
from typing import Dict, Optional
from core.config import env_config
from core.logger import logger


class CognitoAuth:
    """Amazon Cognito authentication provider"""
    
    def __init__(self):
        """Initialize Cognito client with configuration"""
        # Validate configuration
        self._validate_config()

        self.client = boto3.client('cognito-idp', region_name=env_config.default_region)
        self.user_pool_id = env_config.cognito_config['user_pool_id']
        self.client_id = env_config.cognito_config['client_id']

        # cache for tokens and user info
        self.refresh_tokens = {}  # {username: refresh_token}
        self.access_tokens = {}   # {username: {access_token, expiry_time}}
        self.user_info = {}       # {username: {user_attributes}}
        
        # Token validity period in seconds (default: 55 minutes to be safe with 1h tokens)
        self.token_validity_period = 55 * 60
        
        logger.info(f"CognitoAuth initialized with user pool: {self.user_pool_id}")
        
    def _validate_config(self) -> None:
        """Validate authentication configuration"""
        if not env_config.cognito_config['user_pool_id']:
            error_msg = "Missing required configuration: USER_POOL_ID"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        if not env_config.cognito_config['client_id']:
            error_msg = "Missing required configuration: CLIENT_ID"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("Authentication configuration validated successfully")

    def authenticate(self, username: str, password: str) -> Dict:
        """
        Authenticate a user using Amazon Cognito

        Returns:
            dict: Authentication result containing tokens and user attributes
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
                self.access_tokens[username] = {
                    'access_token': response['AuthenticationResult'].get('AccessToken'),
                    'expiry_time': time.time() + self.token_validity_period
                }

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

    def verify_token(self, token: str) -> Optional[str]:
        """
        Verify an access token with Cognito and refresh if expired

        Args:
            token: The access token to verify
            
        Returns:
            str: The valid token (original or refreshed) if verification succeeds, None otherwise
        """
        # Check if token exists in our stored access tokens
        username = None
        for user, token_data in self.access_tokens.items():
            if token_data['access_token'] == token:
                username = user
                break

        if username:
            # Check if token is still valid based on our local expiry time
            current_time = time.time()
            token_expiry = self.access_tokens[username]['expiry_time']
            
            # If token is not expired locally, return it without API call
            if current_time < token_expiry - 300:  # 5 minutes buffer
                return token

            # If token is close to expiry, try to refresh it
            if username in self.refresh_tokens:
                try:
                    if auth_result := self.refresh_access_token(username):
                        # Return the new token
                        return auth_result['AccessToken']
                except Exception as e:
                    logger.error(f"Token refresh failed for user [{username}]: {str(e)}")
                    self._remove_token(token)
                    return None

            # Try to verify with Cognito as a last resort if we can't refresh
            try:
                # Let Cognito verify if token is still valid
                self.client.get_user(AccessToken=token)
                # Update expiry time since token is still valid
                self.access_tokens[username]['expiry_time'] = time.time() + self.token_validity_period
                return token
            except self.client.exceptions.NotAuthorizedException:
                # Token is definitely expired
                self._remove_token(token)
                return None
            except Exception as e:
                logger.error(f"Token verification failed: {str(e)}")
                return None

        # Verify with Cognito when no token cached
        try:
            response = self.client.get_user(AccessToken=token)
            username = response['Username']
            
            # Store verified token and user info
            self.access_tokens[username] = {
                'access_token': token,
                'expiry_time': time.time() + self.token_validity_period
            }
            self.user_info[username] = {
                'username': username,
                'attributes': {attr['Name']: attr['Value'] for attr in response['UserAttributes']}
            }
            return token

        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None

    def refresh_access_token(self, username: str) -> Optional[Dict]:
        """
        Refresh access token using stored refresh token

        Returns:
            dict: New token if refresh successful, None otherwise
        """
        refresh_token = self.refresh_tokens.get(username)
        if not refresh_token:
            return None
            
        try:
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters={
                    'REFRESH_TOKEN': refresh_token
                }
            )
            
            if 'AuthenticationResult' in response:
                # Update stored tokens
                self.access_tokens[username] = {
                    'access_token': response['AuthenticationResult']['AccessToken'],
                    'expiry_time': time.time() + self.token_validity_period
                }
                # Note: Refresh token remains the same
                
                logger.info(f"Successfully refreshed token for user [{username}]")
                return response['AuthenticationResult']
            else:
                logger.warning(f"Token refresh failed for user [{username}]: No AuthenticationResult")
                return None
                
        except Exception as e:
            logger.error(f"Token refresh failed for user [{username}]: {str(e)}")
            return None

    def _remove_token(self, token: str) -> None:
        """Remove token and associated data from storage"""
        for username, token_data in self.access_tokens.items():
            if token_data['access_token'] == token:
                # Try to refresh token before removing
                if username in self.refresh_tokens:
                    if self.refresh_access_token(username):
                        return  # Token refreshed successfully, don't remove
                
                # If refresh failed or no refresh token, remove all tokens
                del self.access_tokens[username]
                if username in self.refresh_tokens:
                    del self.refresh_tokens[username]
                if username in self.user_info:
                    del self.user_info[username]
                break

    def get_token_for_user(self, username: str) -> str:
        """Get stored access token for user"""
        token_data = self.access_tokens.get(username)
        return token_data['access_token'] if token_data else ''

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
