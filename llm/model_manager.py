"""
LLM model management and configuration
"""
from typing import Dict, List, Optional
from decimal import Decimal
from botocore.exceptions import ClientError
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_resource


VALID_MODEL_TYPES = ['text', 'multimodal', 'image', 'embedding']


class ModelManager:
    
    def __init__(self):
        try:
            self.dynamodb = get_aws_resource('dynamodb')
            self.table_name = env_config.database_config['setting_table']
            self.ensure_table_exists()
            self.table = self.dynamodb.Table(self.table_name)
            logger.debug(f"Initialized ModelManager with table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize ModelManager: {str(e)}")
            raise

    def ensure_table_exists(self):
        """Ensure the DynamoDB table exists, create if it doesn't"""
        try:
            existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
            if self.table_name not in existing_tables:
                logger.info(f"Creating DynamoDB table: {self.table_name}")
                self.dynamodb.create_table(
                    TableName=self.table_name,
                    KeySchema=[
                        {'AttributeName': 'setting_name', 'KeyType': 'HASH'},
                        {'AttributeName': 'type', 'KeyType': 'RANGE'}
                    ],
                    AttributeDefinitions=[
                        {'AttributeName': 'setting_name', 'AttributeType': 'S'},
                        {'AttributeName': 'type', 'AttributeType': 'S'}
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                # Wait for table to be created
                waiter = self.dynamodb.meta.client.get_waiter('table_exists')
                waiter.wait(TableName=self.table_name)
        except Exception as e:
            logger.error(f"Error ensuring table exists: {str(e)}")
            raise

    def _convert_decimal_to_float(self, obj):
        """Helper function to convert Decimal values to float in nested dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._convert_decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimal_to_float(item) for item in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    def get_models(self) -> List[Dict]:
        """Get all configured LLM models"""
        try:
            response = self.table.get_item(
                Key={
                    'setting_name': 'llm_models',
                    'type': 'global'
                }
            )
            if 'Item' in response:
                return self._convert_decimal_to_float(response['Item'].get('models', []))
            return []
        except ClientError as e:
            logger.error(f"Error getting LLM models: {str(e)}")
            return []

    def add_model(self, name: str, model_id: str, provider: str = None, 
                 model_type: str = 'text', description: str = None) -> bool:
        """
        Add a new LLM model to the configuration
        
        Args:
            name: Display name for the model
            model_id: Unique identifier for the model
            provider: Model provider (e.g., 'Anthropic', 'Google')
            model_type: Type of model ('text', 'multimodal', 'image')
            description: Optional description of the model
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        try:
            if not name or not model_id:
                raise ValueError("Model name and ID are required")
            
            if model_type not in VALID_MODEL_TYPES:  # Fixed: Using module-level constant
                raise ValueError(f"Invalid model type. Must be one of: {', '.join(VALID_MODEL_TYPES)}")
            
            # Get current models
            models = self.get_models()
            
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
            self.table.put_item(
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

    def delete_model(self, model_id: str) -> bool:
        """
        Delete an LLM model by model_id
        
        Args:
            model_id: The unique identifier of the model to delete
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            ValueError: If model_id is not found
        """
        try:
            if not model_id:
                raise ValueError("Model ID is required")
            
            # Get current models
            models = self.get_models()
            
            # Find and remove model with matching model_id
            original_length = len(models)
            models = [m for m in models if m['model_id'] != model_id]
            
            if len(models) == original_length:
                raise ValueError(f"Model with ID '{model_id}' not found")
            
            # Update table
            self.table.put_item(
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

    def init_default_models(self) -> Optional[List[Dict]]:
        """Initialize default LLM models if none exist"""
        try:
            models = self.get_models()
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
                self.table.put_item(
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

# Create a singleton instance
model_manager = ModelManager()
