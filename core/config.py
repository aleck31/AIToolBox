"""
Configuration management using python-dotenv for environment variables
"""
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ENVConfig:
    """Environment-specific configuration for deployment settings"""
    
    @property
    def default_region(self) -> str:
        """Get default AWS region"""
        return os.getenv('DEFAULT_REGION', 'ap-southeast-1')

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
            'setting_table': os.getenv('SETTING_TABLE', 'aibox_setting'),
            'session_table': os.getenv('SESSION_TABLE', 'aibox_session'),
            'retention_days': int(os.getenv('RETENTION_DAYS', '30')) # 用于计算dynamodb ttl
        }

    @property
    def bedrock_config(self) -> Dict[str, str]:
        """Get AWS Bedrock configuration"""
        return {
            'default_region': os.getenv('BEDROCK_REGION', 'us-west-2'),  # Changed from region_id to default_region
            'assume_role': os.getenv('BEDROCK_ASSUME_ROLE', None)
        }

    @property
    def gemini_config(self) -> Dict[str, str]:
        """Get Gemini API configuration"""
        return {
            'secret_id': os.getenv('GEMINI_SECRET_ID'),
        }

class AppConfig:
    """Application-level configuration settings"""

    @property
    def log_level(self) -> str:     #跟 server_config 'debug' 重复了，可否去掉
        """Get logging level"""
        return os.getenv('LOG_LEVEL', 'INFO')

    @property
    def server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        return {
            'host': os.getenv('SERVER_HOST', 'localhost'),
            'port': int(os.getenv('SERVER_PORT', '8080')),
            'debug': os.getenv('DEBUG', 'False').lower() == 'true'
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
            'token_expiration': int(os.getenv('TOKEN_EXPIRATION', '3600')),
            'ssl_enabled': os.getenv('SSL_ENABLED', 'False').lower() == 'true'
        }


# Create singleton instances
env_config = ENVConfig()
app_config = AppConfig()