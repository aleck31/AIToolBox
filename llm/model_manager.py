"""
LLM model management and configuration
"""
from typing import Dict, List, Optional
from decimal import Decimal
from dataclasses import dataclass
from botocore.exceptions import ClientError
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_resource
from . import LLMModel


# Default model configurations
DEFAULT_MODELS = [
    LLMModel(
        name='claude3.5-sonnet-v2',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        api_provider='Bedrock',
        type='multimodal',
        description='Claude 3.5 Sonnet model for general use',
        vendor='Anthropic'
    ),
    LLMModel(
        name='gemini-pro',
        model_id='gemini-1.5-pro',
        api_provider='Gemini',
        type='multimodal',
        description='Gemini Pro model for text and vision',
        vendor='Google'
    ),
    LLMModel(
        name='stable-diffusion',
        model_id='stability.stable-image-ultra-v1:0',
        api_provider='Bedrock',
        type='image',
        description='Stable Diffusion Ultra for image generation',
        vendor='Stability AI'
    )    
]


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

    def get_model_by_id(self, model_id: str) -> Optional[LLMModel]:
        """Get a specific LLM model by its ID
        
        Args:
            model_id: The ID of the model to retrieve
            
        Returns:
            LLMModel if found, None otherwise
        """
        try:
            models = self.get_models()
            return next((model for model in models if model.model_id == model_id), None)
        except Exception as e:
            logger.error(f"Error getting model by ID {model_id}: {str(e)}")
            return None

    def get_models(self, filter=None) -> List[LLMModel]:
        """Get all configured LLM models

        Args:
            filter: [Optional] Dict containing filtering conditions based on LLMModel properties        
        """
        try:
            response = self.table.get_item(
                Key={
                    'setting_name': 'llm_models',
                    'type': 'global'
                }
            )
            if 'Item' in response:
                models_data = self._convert_decimal_to_float(response['Item'].get('models', []))
                return [LLMModel.from_dict(model_data) for model_data in models_data]
            return []
        except ClientError as e:
            logger.error(f"Error getting LLM models: {str(e)}")
            return []

    def add_model(self, model: LLMModel) -> bool:
        """Add a new LLM model to the configuration"""
        try:
            # Get current models
            models = self.get_models()
            
            # Check if model with same name or model_id exists
            for existing in models:
                if existing.name == model.name:
                    raise ValueError(f"Model with name '{model.name}' already exists")
                if existing.model_id == model.model_id:
                    raise ValueError(f"Model with ID '{model.model_id}' already exists")
            
            # Convert models to dict format for storage
            models_data = [m.to_dict() for m in models]
            models_data.append(model.to_dict())
            
            # Update table
            self.table.put_item(
                Item={
                    'setting_name': 'llm_models',
                    'type': 'global',
                    'models': models_data
                }
            )
            logger.info(f"Added new LLM model: {model.name} ({model.model_id})")
            return True
        except Exception as e:
            logger.error(f"Error adding LLM model: {str(e)}")
            raise

    def delete_model(self, model_id: str) -> bool:
        """Delete an LLM model by model_id"""
        try:
            if not model_id:
                raise ValueError("Model ID is required")
            
            # Get current models
            models = self.get_models()
            
            # Find and remove model with matching model_id
            original_length = len(models)
            filtered_models = [m for m in models if m.model_id != model_id]
            
            if len(filtered_models) == original_length:
                raise ValueError(f"Model with ID '{model_id}' not found")
            
            # Convert models to dict format for storage
            models_data = [m.to_dict() for m in filtered_models]
            
            # Update table
            self.table.put_item(
                Item={
                    'setting_name': 'llm_models',
                    'type': 'global',
                    'models': models_data
                }
            )
            logger.info(f"Deleted LLM model with ID: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting LLM model: {str(e)}")
            raise

    def init_default_models(self) -> Optional[List[LLMModel]]:
        """Initialize default LLM models if none exist"""
        try:
            models = self.get_models()
            if not models:
                models_data = [model.to_dict() for model in DEFAULT_MODELS]
                self.table.put_item(
                    Item={
                        'setting_name': 'llm_models',
                        'type': 'global',
                        'models': models_data
                    }
                )
                logger.info("Initialized default LLM models")
                return DEFAULT_MODELS
            return models
        except Exception as e:
            logger.error(f"Error initializing default LLM models: {str(e)}")
            return None


# Create a singleton instance
model_manager = ModelManager()
