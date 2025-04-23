"""
Configuration management using python-dotenv for environment variables
"""
import os
from typing import Any, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Debug: Print loaded environment variables
print(f"Loaded SERVER_HOST: {os.getenv('SERVER_HOST')}")


class ENVConfig:
    """Environment-specific configuration for deployment settings"""
    
    @property
    def aws_region(self) -> str:
        """Get default AWS region"""
        return os.getenv('AWS_REGION', 'ap-southeast-1')

    @property
    def cognito_config(self) -> dict:
        """Get Cognito configuration"""
        return {
            'user_pool_id': os.getenv('USER_POOL_ID'),
            'client_id': os.getenv('CLIENT_ID')
        }

    @property
    def database_config(self) -> dict:
        """Get database configuration"""
        return {
            'setting_table': os.getenv('SETTING_TABLE', 'aitoolbox-setting'),
            'session_table': os.getenv('SESSION_TABLE', 'aitoolbox-session'),
            'retention_days': int(os.getenv('RETENTION_DAYS', '30')) # 用于计算dynamodb ttl
        }

    @property
    def bedrock_config(self) -> Dict[str, str]:
        """Get AWS Bedrock configuration"""
        return {
            'bedrock_region': os.getenv('BEDROCK_REGION', 'us-west-2'),
            'assume_role': os.getenv('BEDROCK_ASSUME_ROLE', None)
        }

class AppConfig:
    """Application-level configuration settings"""

    @property
    def server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        # Prioritize using the PORT environment variable provided by App Runner
        port = os.getenv('PORT') or os.getenv('SERVER_PORT', '8080')
        return {
            'host': os.getenv('SERVER_HOST', '0.0.0.0'),  # 默认使用0.0.0.0以便在容器中工作
            'port': int(port),
            'debug': os.getenv('DEBUG', 'False').lower() == 'true',
            'log_level': 'debug' if os.getenv('DEBUG') else 'info'
        }

    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        return {
            'allow_origins': os.getenv('CORS_ORIGINS', '*').split(','),
            'allow_methods': os.getenv('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(','),
            'allow_headers': os.getenv('CORS_HEADERS', '*').split(',')
        }

    @property
    def security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        return {
            'secret_key': os.getenv('SECRET_KEY', 'default-secret-key'),
            'token_expiration': int(os.getenv('TOKEN_EXPIRATION', '7200')),
            'ssl_enabled': os.getenv('SSL_ENABLED', 'False').lower() == 'true'
        }


# Create singleton instances
env_config = ENVConfig()
app_config = AppConfig()
