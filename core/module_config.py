"""
Module configuration management
"""
from typing import Dict, Optional, Any, List
from decimal import Decimal
import boto3
from botocore.exceptions import ClientError
from core.config import env_config
from core.logger import logger


class AppConf:
    """
    A class to store and manage configuration. [Legacy]

    """
    
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


class ModuleConfig:
    def __init__(self):
        session = boto3.Session(region_name=env_config.default_region)
        self.dynamodb = session.resource('dynamodb')
        self.table = self.dynamodb.Table(env_config.database_config['setting_table'])
        self._config_cache = {}  # Cache for module configurations

    def _decimal_to_float(self, obj: Any) -> Any:
        """Helper function to convert Decimal values to float in nested dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_float(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    def _float_to_decimal(self, obj: Any) -> Any:
        """Helper function to convert float values to Decimal for DynamoDB"""
        if isinstance(obj, dict):
            return {key: self._float_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._float_to_decimal(item) for item in obj]
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
        # Check cache first
        cache_key = f"{module_name}:{sub_module}" if sub_module else module_name
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        try:
            logger.debug(f"[ModuleConfig] Getting config for module: {module_name}")
            response = self.table.get_item(
                Key={
                    'setting_name': module_name,
                    'type': 'module'
                }
            )
            logger.debug(f"[ModuleConfig] Raw response from DB: {response}")
            if 'Item' in response:
                config = self._decimal_to_float(response['Item'])
                # Simplify module configuration by removing submodule configurations
                # if sub_module and 'sub_modules' in config:
                #     sub_config = config['sub_modules'].get(sub_module)
                #     if sub_config:
                #         self._config_cache[cache_key] = sub_config
                #         return sub_config
                self._config_cache[cache_key] = config
                return config
            logger.debug(f"[ModuleConfig] No config found for {module_name}, initializing default")
            if config := self.init_module_config(module_name):
                self._config_cache[cache_key] = config
            return config
        except ClientError as e:
            logger.error(f"[ModuleConfig] Error getting module config: {str(e)}")
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
            config = self._float_to_decimal(config)
            
            self.table.put_item(Item=config)
            
            # Clear cache entries for this module
            cache_keys_to_remove = [k for k in self._config_cache if k.startswith(f"{module_name}:") or k == module_name]
            for key in cache_keys_to_remove:
                self._config_cache.pop(key, None)
                
            logger.info(f"[ModuleConfig] Updated config for module: {module_name}")
            return True
        except Exception as e:
            logger.error(f"[ModuleConfig] Error updating module config: {str(e)}")
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
                logger.warning(f"[ModuleConfig] No default model found for module {module_name}, using fallback model")
                return 'anthropic.claude-3-5-sonnet-20241022-v2:0'
        except Exception as e:
            logger.error(f"[ModuleConfig] Error getting default model for module {module_name}: {str(e)}")
            return 'anthropic.claude-3-5-sonnet-20241022-v2:0'

    def get_inference_params(self, module_name: str, sub_module: str = None) -> Optional[Dict]:
        """Get inference parameters from module configuration"""
        config = self.get_module_config(module_name)
        if config and 'parameters' in config:
            # if sub_module and 'sub_modules' in config:
            #     sub_config = config['sub_modules'].get(sub_module, {})
            #     return sub_config.get('parameters', config['parameters'])
            return config['parameters']
        return None

    def get_enabled_tools(self, module_name: str, sub_module: str = None) -> List[str]:
        """
        Get the list of enabled tools for a specific module
        
        Args:
            module_name: Name of the module
            sub_module: Optional sub-module name
            
        Returns:
            List[str]: List of enabled tool module names
        """
        try:
            config = self.get_module_config(module_name)
            if config:
                # if sub_module and 'sub_modules' in config:
                #     sub_config = config['sub_modules'].get(sub_module, {})
                #     return sub_config.get('enabled_tools', [])
                return config.get('enabled_tools', [])
            return []
        except Exception as e:
            logger.error(f"[ModuleConfig] Error getting enabled tools for module {module_name}: {str(e)}")
            return []


    def init_module_config(self, module_name: str) -> Optional[Dict]:
        """Initialize default configuration for a module"""
        default_configs = {
            'assistant': {
                'setting_name': 'assistant',
                'type': 'module',
                'description': 'Assistant Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are a helpful AI assistant.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 2049,
                },
                'enabled_tools': [
                    'get_weather',         # Weather information
                    'get_text_from_url',   # Get text content from webpage URL
                    'generate_image'       # AI image generation
                ]
            },
            'chatbot': {
                'setting_name': 'chatbot',
                'type': 'module',
                'description': 'Chatbot Module Settings',
                'default_model': 'gemini-1.5-pro',
                'system_prompt': 'You are a friendly chatbot.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 1000,
                    'top_p': Decimal('0.99'),
                    'top_k': 200  # Integer for Gemini compatibility                    
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
                    'max_tokens': 2000,
                    "top_k": 200
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
                },
                'enabled_tools': [
                    'get_text_from_url'     # Get text content from webpage URL
                ]
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
            'asking': {
                'setting_name': 'asking',
                'type': 'module',
                'description': 'Asking Module',
                'default_model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'system_prompt': 'You are able to think before and during responding.',
                'parameters': {
                    'temperature': Decimal('0.7'),
                    'max_tokens': 4096
                },
                'enabled_tools': [
                    'get_text_from_url'     # Get text content from webpage URL
                ]
            },
            'draw': {
                'setting_name': 'draw',
                'type': 'module',
                'description': 'Draw Module',
                'default_model': 'stability.stable-image-ultra-v1:0',
                # basic parameters for generative models
                'parameters': {
                    'height': 1152,
                    'width': 896,
                    'aspect_ratio': '9:16'
                }
            },
            'creative': {
                'setting_name': 'creative',
                'type': 'module',
                'description': 'Creative Module',
                'default_model': 'amazon.nova-canvas-v1:0',
                # basic parameters for generative models
                'parameters': {
                    'height': 1152,
                    'width': 896,
                    'cfg_scale': 7,
                    'steps': 50
                }
            }
        }
        
        if module_name in default_configs:
            config = default_configs[module_name]
            try:
                self.table.put_item(Item=config)
                logger.info(f"[ModuleConfig] Initialized config for module: {module_name}")
                return self._decimal_to_float(config)
            except Exception as e:
                logger.error(f"[ModuleConfig] Error initializing module config: {str(e)}")
                return None
        return None

# Create a singleton instance
module_config = ModuleConfig()
