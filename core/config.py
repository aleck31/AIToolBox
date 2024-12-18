"""
Configuration management using python-dotenv for environment variables
"""
import os
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_env_value(key: str, default: Any = None) -> Any:
    """Get environment variable value with optional default"""
    return os.getenv(key, default)

class ENVConfig:
    """Environment-specific configuration for deployment settings"""
    
    @property
    def default_region(self) -> str:
        """Get default AWS region"""
        return get_env_value('DEFAULT_REGION', 'ap-southeast-1')

    @property
    def cognito_config(self) -> dict:
        """Get Cognito configuration"""
        return {
            'user_pool_id': get_env_value('USER_POOL_ID'),
            'client_id': get_env_value('CLIENT_ID')
        }

    @property
    def database_config(self) -> dict:
        """Get database configuration"""
        return {
            'setting_table': get_env_value('SETTING_TABLE', 'aibox_setting'),
            'session_table': get_env_value('SESSION_TABLE', 'aibox_session'),
        }

    @property
    def bedrock_config(self) -> Dict[str, str]:
        """Get AWS Bedrock configuration"""
        return {
            'default_region': get_env_value('BEDROCK_REGION', 'us-west-2'),  # Changed from region_id to default_region
            'assume_role': get_env_value('BEDROCK_ASSUME_ROLE', None)
        }

    @property
    def gemini_config(self) -> Dict[str, str]:
        """Get Gemini API configuration"""
        return {
            'secret_id': get_env_value('GEMINI_SECRET_ID'),
        }

class AppConfig:
    """Application-level configuration settings"""

    @property
    def log_level(self) -> str:     #跟 server_config 'debug' 重复了，可否去掉
        """Get logging level"""
        return get_env_value('LOG_LEVEL', 'INFO')

    @property
    def server_config(self) -> Dict[str, Any]:
        """Get server configuration"""
        # 请在 .env 文件里添加相应的变量定义
        return {
            'host': get_env_value('SERVER_HOST', 'localhost'),
            'port': int(get_env_value('SERVER_PORT', '8080')),
            'debug': get_env_value('DEBUG', 'False').lower() == 'true'
        }

    @property
    def cors_config(self) -> Dict[str, Any]:
        """Get CORS configuration"""
        # 请在 .env 文件里添加相应的变量定义
        return {
            'allow_origins': get_env_value('CORS_ORIGINS', '*').split(','),
            'allow_methods': get_env_value('CORS_METHODS', 'GET,POST,PUT,DELETE,OPTIONS').split(','),
            'allow_headers': get_env_value('CORS_HEADERS', '*').split(',')
        }

    @property
    def security_config(self) -> Dict[str, Any]:
        """Get security configuration"""
        # 请在 .env 文件里添加相应的变量定义
        return {
            'secret_key': get_env_value('SECRET_KEY', 'default-secret-key'),
            'token_expiration': int(get_env_value('TOKEN_EXPIRATION', '3600')),
            'ssl_enabled': get_env_value('SSL_ENABLED', 'False').lower() == 'true'
        }

class AppConf:
    """
    A class to store and manage app configuration.
    """

    # Constants
    CODELANGS = ["Python", "GoLang", "Rust", "Java", "C++",
                 "Swift", "Javascript", "Typescript", "HTML", "SQL", "Shell"]
    # The list of style presets for Stable Diffusion
    # https://docs.aws.amazon.com/zh_cn/bedrock/latest/userguide/model-parameters-diffusion-1-0-text-image.html
    PICSTYLES = [
        "增强(enhance)", "照片(photographic)", "模拟胶片(analog-film)", "电影(cinematic)",
        "数字艺术(digital-art)",  "美式漫画(comic-book)",  "动漫(anime)", "3D模型(3d-model)", "低多边形(low-poly)",
        "线稿(line-art)", "等距插画(isometric)", "霓虹朋克(neon-punk)", "复合建模(modeling-compound)",  
        "奇幻艺术(fantasy-art)", "像素艺术(pixel-art)", "折纸艺术(origami)", "瓷砖纹理(tile-texture)"
    ]

    def update(self, key, value):
        # Update the value of a variable.
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError(f"Invalid configuration variable: {key}")


# Create singleton instances
env_config = ENVConfig()
app_config = AppConfig()
