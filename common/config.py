"""
AWS service configuration parameters
"""
import os
import json
from pathlib import Path

def load_config():
    """Load configuration from JSON file"""
    config_path = Path(__file__).parent / 'config.json'
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return {}

def get_config_value(env_key, json_path):
    """
    Get configuration value with priority:
    1. Environment variable
    2. JSON config file
    3. None if not found
    """
    # First try environment variable
    env_value = os.environ.get(env_key)
    if env_value is not None:
        return env_value
    
    # Then try JSON config
    config = load_config()
    try:
        value = config
        for key in json_path:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return None

# Load configuration
CONFIG = load_config()

# Default AWS region
DEFAULT_REGION = get_config_value('AWS_DEFAULT_REGION', ['default_region'])

# Cognito configuration
COGNITO_CONFIG = {
    'user_pool_id': get_config_value('COGNITO_USER_POOL_ID', ['cognito', 'user_pool_id']),
    'client_id': get_config_value('COGNITO_CLIENT_ID', ['cognito', 'client_id'])
}

# Database configuration
DATABASE_CONFIG = {
    'setting_table': get_config_value('DATABASE_SETTING_TABLE', ['database', 'setting_table']),
    'user_table': get_config_value('DATABASE_USER_TABLE', ['database', 'user_table'])
}

# Bedrock configuration
BEDROCK_REGION = get_config_value('AWS_BEDROCK_REGION', ['bedrock', 'region'])
