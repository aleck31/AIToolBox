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
        name='claude3.6-sonnet',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        api_provider='Bedrock',
        modality='vision',
        description='Claude 3.5 Sonnet v2 model for general use',
        vendor='Anthropic'
    ),
    LLMModel(
        name='gemini pro',
        model_id='gemini-1.5-pro',
        api_provider='Gemini',
        modality='vision',
        description='Gemini Pro model for text and vision',
        vendor='Google'
    ),
    LLMModel(
        name='gemini flash',
        model_id='gemini-2.0-flash',
        api_provider='Gemini',
        modality='vision',
        description='Gemini Flash model for text and vision',
        vendor='Google'
    ),
    LLMModel(
        modality= "vision",
        api_provider= "Bedrock",
        description= "Nova Pro is a vision understanding foundation model. It is multilingual and can reason over text, images and videos.",
        model_id= "amazon.nova-pro-v1:0",
        name= "Nova Pro",
        vendor= "Amazon"
    ),
    LLMModel(
        modality= "image",
        api_provider= "BedrockInvoke",
        description= "Nova image generation model. It generates images from text and allows users to upload and edit an existing image. ",
        model_id= "amazon.nova-canvas-v1:0",
        name= "Nova Canvas",
        vendor= "Amazon"
    ),
    LLMModel(
        name='stable-diffusion',
        model_id='stability.stable-image-ultra-v1:0',
        api_provider='BedrockInvoke',
        modality='image',
        description='Stable Diffusion Ultra for image generation',
        vendor='Stability AI'
    ),
    LLMModel(
        modality= "video",
        api_provider= "BedrockInvoke",
        description= "Nova video generation model. It generates short high-definition videos, up to 9 seconds long from input images or a natural language prompt.",
        model_id= "amazon.nova-reel-v1:0",
        name= "Nova Reel",
        vendor= "Amazon"       
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
            # Initialize default models if none exist
            self.init_default_models()
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

    def _decimal_to_float(self, obj):
        """Helper function to convert Decimal values to float in nested dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._decimal_to_float(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._decimal_to_float(item) for item in obj]
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

    def get_models(self, filter: Optional[Dict] = None) -> List[LLMModel]:
        """Get configured models from Database with optional filtering

        Args:
            filter: Optional dictionary of model properties to filter by.
                   Example: {'modality': 'vision'} returns only vision models
                   Supported properties: name, model_id, api_provider, modality, vendor

        Returns:
            List of LLMModel instances matching the filter criteria
        """
        try:
            # Get all models from DynamoDB
            response = self.table.get_item(
                Key={
                    'setting_name': 'model_manager',
                    'type': 'global'
                }
            )
            
            if 'Item' not in response:
                return []
                
            # Convert stored data to LLMModel instances
            models_data = self._decimal_to_float(response['Item'].get('models', []))
            models = [LLMModel.from_dict(model_data) for model_data in models_data]
            
            # Apply filters if provided
            if filter:
                filtered_models = []
                for model in models:
                    matches = True
                    for key, value in filter.items():
                        if not hasattr(model, key) or getattr(model, key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_models.append(model)
                return filtered_models
                
            return models
            
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
                    'setting_name': 'model_manager',
                    'type': 'global',
                    'models': models_data
                }
            )
            logger.info(f"Added new LLM model: {model.name} ({model.model_id})")
            return True
        except Exception as e:
            logger.error(f"Error adding LLM model: {str(e)}")
            raise

    def update_model(self, model: LLMModel) -> bool:
        """Update an existing LLM model
        
        Args:
            model: LLMModel instance with updated properties
            
        Returns:
            bool: True if update successful
        """
        try:
            if not model.model_id:
                raise ValueError("Model ID is required")
            
            # Get current models
            models = self.get_models()
            
            # Find model to update
            model_exists = False
            updated_models = []
            for existing in models:
                if existing.model_id == model.model_id:
                    model_exists = True
                    # Check if another model has the same name (except self)
                    if model.name != existing.name and any(m.name == model.name for m in models):
                        raise ValueError(f"Model with name '{model.name}' already exists")
                    updated_models.append(model)
                else:
                    updated_models.append(existing)
            
            if not model_exists:
                raise ValueError(f"Model with ID '{model.model_id}' not found")
            
            # Convert models to dict format for storage
            models_data = [m.to_dict() for m in updated_models]
            
            # Update table
            self.table.put_item(
                Item={
                    'setting_name': 'model_manager',
                    'type': 'global',
                    'models': models_data
                }
            )
            logger.info(f"Updated LLM model: {model.name} ({model.model_id})")
            return True
        except Exception as e:
            logger.error(f"Error updating LLM model: {str(e)}")
            raise

    def delete_model_by_id(self, model_id: str) -> bool:
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
                    'setting_name': 'model_manager',
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
                        'setting_name': 'model_manager',
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
