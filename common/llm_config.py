from boto3 import Session
from botocore.exceptions import ClientError
from decimal import Decimal
from .logger import logger
from . import DEFAULT_REGION, DATABASE_CONFIG


session = Session(region_name=DEFAULT_REGION)
ddb = session.resource('dynamodb')
table_name = DATABASE_CONFIG.get('setting_table')
setting_table = ddb.Table(table_name)

VALID_MODEL_TYPES = ['text', 'multimodal', 'image']
VALID_SETTING_TYPES = ['global', 'module']


def convert_decimal_to_float(obj):
    """Helper function to convert Decimal values to float in nested dictionaries and lists"""
    if isinstance(obj, dict):
        return {key: convert_decimal_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal_to_float(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    return obj


def get_llm_models():
    """Get all configured LLM models"""
    try:
        response = setting_table.get_item(
            Key={
                'setting_name': 'llm_models',
                'type': 'global'
            }
        )
        if 'Item' in response:
            return response['Item'].get('models', [])
        return []
    except ClientError as e:
        logger.error(f"Error getting LLM models: {str(e)}")
        return []


def add_llm_model(name: str, model_id: str, provider: str = None, model_type: str = 'text', description: str = None):
    """Add a new LLM model to the configuration"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
        
        if model_type not in VALID_MODEL_TYPES:
            raise ValueError(f"Invalid model type. Must be one of: {', '.join(VALID_MODEL_TYPES)}")
        
        # Get current models
        models = get_llm_models()
        
        # Check if model with same name or model_id exists
        for model in models:
            if model['name'] == name:
                raise ValueError(f"Model with name '{name}' already exists")
            if model['model_id'] == model_id:
                raise ValueError(f"Model with ID '{model_id}' already exists")
        
        # Add new model
        new_model = {
            'name': name,
            'model_id': model_id,
            'model_type': model_type,
            'provider': provider,
            'description': description
        }
        models.append(new_model)
        
        # Update table
        setting_table.put_item(
            Item={
                'setting_name': 'llm_models',
                'type': 'global',
                'models': models
            }
        )
        logger.info(f"Added new LLM model: {name} ({model_id})")
        return True
    except Exception as e:
        logger.error(f"Error adding LLM model: {str(e)}")
        raise


def delete_llm_model(model_id: str):
    """Delete an LLM model by model_id"""
    try:
        if not model_id:
            raise ValueError("Model ID is required")
        
        # Get current models
        models = get_llm_models()
        
        # Find and remove model with matching model_id
        original_length = len(models)
        models = [m for m in models if m['model_id'] != model_id]
        
        if len(models) == original_length:
            raise ValueError(f"Model with ID '{model_id}' not found")
        
        # Update table
        setting_table.put_item(
            Item={
                'setting_name': 'llm_models',
                'type': 'global',
                'models': models
            }
        )
        logger.info(f"Deleted LLM model with ID: {model_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting LLM model: {str(e)}")
        raise


def init_module_config(module_name: str):
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
            'system_prompt': 'You are a coding assistant.',
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
            setting_table.put_item(Item=config)
            logger.info(f"Initialized config for module: {module_name}")
            return config
        except Exception as e:
            logger.error(f"Error initializing module config: {str(e)}")
            return None
    return None


def init_default_models():
    """Initialize default LLM models if none exist"""
    try:
        models = get_llm_models()
        if not models:
            default_models = [
                {
                    'name': 'claude3.5-sonnet-v2',
                    'model_id': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                    'provider': 'Anthropic',
                    'model_type': 'multimodal',
                    'description': 'Claude 3.5 Sonnet model for general use'
                },
                {
                    'name': 'gemini-pro',
                    'model_id': 'gemini-1.5-pro',
                    'provider': 'Google',
                    'model_type': 'multimodal',
                    'description': 'Gemini Pro model for text and vision'
                },
                {
                    'name': 'stable-diffusion',
                    'model_id': 'stability.stable-image-ultra-v1:0',
                    'provider': 'Stability',
                    'model_type': 'image',
                    'description': 'Stable Diffusion Ultra for image generation'
                }
            ]
            setting_table.put_item(
                Item={
                    'setting_name': 'llm_models',
                    'type': 'global',
                    'models': default_models
                }
            )
            logger.info("Initialized default LLM models")
            return default_models
        return models
    except Exception as e:
        logger.error(f"Error initializing default LLM models: {str(e)}")
        return None


def update_module_config(module_name: str, config: dict):
    """Update configuration for a specific module"""
    try:
        # Ensure required fields
        config['setting_name'] = module_name
        config['type'] = 'module'
        
        # Convert float values to Decimal for DynamoDB
        if 'parameters' in config:
            for key, value in config['parameters'].items():
                if isinstance(value, float):
                    config['parameters'][key] = Decimal(str(value))
        
        # Convert float values in sub_modules parameters
        if 'sub_modules' in config:
            for sub_module in config['sub_modules'].values():
                if 'parameters' in sub_module:
                    for key, value in sub_module['parameters'].items():
                        if isinstance(value, float):
                            sub_module['parameters'][key] = Decimal(str(value))
        
        setting_table.put_item(Item=config)
        logger.info(f"Updated config for module: {module_name}")
        return True
    except Exception as e:
        logger.error(f"Error updating module config: {str(e)}")
        raise


def get_module_config(module_name: str, sub_module: str = None):
    """Get configuration for a specific module"""
    try:
        response = setting_table.get_item(
            Key={
                'setting_name': module_name,
                'type': 'module'
            }
        )
        if 'Item' in response:
            # Convert any Decimal values to float before returning
            return convert_decimal_to_float(response['Item'])
        return init_module_config(module_name)
    except ClientError as e:
        logger.error(f"Error getting module config: {str(e)}")
        return None


def get_default_model(module_name: str, sub_module: str = None):
    """Get the default model ID for a specific module"""
    try:
        config = get_module_config(module_name)
        if config and 'default_model' in config:
            return config['default_model']
        else:
            # Fallback to Claude 3.5 Sonnet as the default model
            logger.warning(f"No default model found for module {module_name}, using fallback model")
            return 'anthropic.claude-3-5-sonnet-20241022-v2:0'
    except Exception as e:
        logger.error(f"Error getting default model for module {module_name}: {str(e)}")
        return 'anthropic.claude-3-5-sonnet-20241022-v2:0'


def get_inference_params(module_name: str, sub_module: str = None):
    """Get inference parameters from module configuration"""
    config = get_module_config(module_name)
    if config and 'parameters' in config:
        params = config['parameters']
        return params


def get_system_prompt(module_name: str, sub_module: str = None):
    """Get system prompt from module configuration"""
    config = get_module_config(module_name)
    if config:
        if sub_module and 'sub_modules' in config:
            sub_config = config['sub_modules'].get(sub_module, {})
            return sub_config.get('system_prompt')
        return config.get('system_prompt')
    return None
