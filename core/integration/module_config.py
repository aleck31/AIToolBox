"""
Module configuration management
"""
from typing import Dict, Optional, Any
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from core.config import env_config
from core.logger import logger

class ModuleConfig:
    def __init__(self):
        session = boto3.Session(region_name=env_config.default_region)
        self.dynamodb = session.resource('dynamodb')
        self.table = self.dynamodb.Table(env_config.database_config['setting_table'])

    def _convert_decimal_to_float(self, obj: Any) -> Any:
        """Helper function to convert Decimal values to float in nested dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._convert_decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_float(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    def _convert_float_to_decimal(self, obj: Any) -> Any:
        """Helper function to convert float values to Decimal for DynamoDB"""
        if isinstance(obj, dict):
            return {key: self._convert_float_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_float_to_decimal(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
        return obj

    def get_module_config(self, module_name: str, sub_module: str = None) -> Optional[Dict]:
        """
        Get configuration for a specific module
        
        Args:
            module_name: Name of the module
            sub_module: Optional sub-module name
            
        Returns:
            dict: Module configuration or None if not found
        """
        try:
            response = self.table.get_item(
                Key={
                    'setting_name': module_name,
                    'type': 'module'
                }
            )
            if 'Item' in response:
                config = self._convert_decimal_to_float(response['Item'])
                if sub_module and 'sub_modules' in config:
                    return config['sub_modules'].get(sub_module)
                return config
            return self.init_module_config(module_name)
        except ClientError as e:
            logger.error(f"Error getting module config: {str(e)}")
            return None

    def update_module_config(self, module_name: str, config: Dict) -> bool:
        """
        Update configuration for a specific module
        
        Args:
            module_name: Name of the module
            config: New configuration dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure required fields
            config['setting_name'] = module_name
            config['type'] = 'module'
            
            # Convert float values to Decimal for DynamoDB
            config = self._convert_float_to_decimal(config)
            
            self.table.put_item(Item=config)
            logger.info(f"Updated config for module: {module_name}")
            return True
        except Exception as e:
            logger.error(f"Error updating module config: {str(e)}")
            raise

    def get_default_model(self, module_name: str, sub_module: str = None) -> str:
        """
        Get the default model ID for a specific module
        
        Args:
            module_name: Name of the module
            sub_module: Optional sub-module name
            
        Returns:
            str: Default model ID or fallback model ID
        """
        try:
            config = self.get_module_config(module_name)
            if config and 'default_model' in config:
                return config['default_model']
            else:
                # Fallback to Claude 3.5 Sonnet as the default model
                logger.warning(f"No default model found for module {module_name}, using fallback model")
                return 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        except Exception as e:
            logger.error(f"Error getting default model for module {module_name}: {str(e)}")
            return 'anthropic.claude-3-5-sonnet-20241022-v2:0'

    def get_inference_params(self, module_name: str, sub_module: str = None) -> Optional[Dict]:
        """Get inference parameters from module configuration"""
        config = self.get_module_config(module_name)
        if config and 'parameters' in config:
            if sub_module and 'sub_modules' in config:
                sub_config = config['sub_modules'].get(sub_module, {})
                return sub_config.get('parameters', config['parameters'])
            return config['parameters']
        return None

    def get_system_prompt(self, module_name: str, sub_module: str = None) -> Optional[str]:
        """Get system prompt from module configuration"""
        config = self.get_module_config(module_name)
        if config:
            if sub_module and 'sub_modules' in config:
                sub_config = config['sub_modules'].get(sub_module, {})
                return sub_config.get('system_prompt')
            return config.get('system_prompt')
        return None

    def init_module_config(self, module_name: str) -> Optional[Dict]:
        """Initialize default configuration for a module"""
        default_configs = {
            'chatbot': {
                'setting_name': 'chatbot',
                'type': 'module',
                'description': 'Chatbot Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a helpful AI assistant.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000
                }
            },
            'chatbot-gemini': {
                'setting_name': 'chatbot-gemini',
                'type': 'module',
                'description': 'Chatbot(Genimi) Module Settings',
                'default_model': 'gemini-1.5-pro',
                'system_prompt': 'You are a helpful AI assistant.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000
                }
            },
            'coding': {
                'setting_name': 'coding',
                'type': 'module',
                'description': 'Coding Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a coding assistant.',
                'parameters': {
                    'temperature': Decimal('0.2'),
                    'max_tokens': 2000
                }
            },
            'text': {
                'setting_name': 'text',
                'type': 'module',
                'description': 'Text Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000
                },
                'sub_modules': {
                    'translate': {
                        'system_prompt': 'You are a translation assistant.',
                        'parameters': {
                            'temperature': Decimal('0.3'),
                            'max_tokens': 1000
                        }
                    },
                    'rewrite': {
                        'system_prompt': 'You are a text rewriting assistant.',
                        'parameters': {
                            'temperature': Decimal('0.7'),
                            'max_tokens': 1000
                        }
                    }
                }
            },
            'summary': {
                'setting_name': 'summary',
                'type': 'module',
                'description': 'Summary Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a summarization assistant.',
                'parameters': {
                    'temperature': Decimal('0.2'),
                    'max_tokens': 2000
                }
            },
            'vision': {
                'setting_name': 'vision',
                'type': 'module',
                'description': 'Vision Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a computer vision assistant.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000
                }
            },
            'draw': {
                'setting_name': 'draw',
                'type': 'module',
                'description': 'Draw Module',
                'default_model': 'stability.stable-image-ultra-v1:0',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000
                }
            },
            'oneshot': {
                'setting_name': 'oneshot',
                'type': 'module',
                'description': 'OneShot Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a one-shot response generator.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 4096
                }
            }
        }
        
        if module_name in default_configs:
            config = default_configs[module_name]
            try:
                self.table.put_item(Item=config)
                logger.info(f"Initialized config for module: {module_name}")
                return self._convert_decimal_to_float(config)
            except Exception as e:
                logger.error(f"Error initializing module config: {str(e)}")
                return None
        return None

# Create a singleton instance
module_config = ModuleConfig()
