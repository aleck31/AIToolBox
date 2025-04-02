"""
LLM model management and configuration
"""
from typing import Dict, List, Optional
from decimal import Decimal
from botocore.exceptions import ClientError
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_resource
from . import LLMModel, LLM_CAPABILITIES


# Default model configurations
DEFAULT_MODELS = [
    LLMModel(
        name='claude3.6-sonnet',
        model_id='anthropic.claude-3-5-sonnet-20241022-v2:0',
        api_provider='Bedrock',
        category='vision',
        description='Claude 3.5 Sonnet v2 model for general use',
        vendor='Anthropic',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=200*1024
        )
    ),
    LLMModel(
        name='gemini 1.5 pro',
        model_id='gemini-1.5-pro',
        api_provider='Gemini',
        category='vision',
        description='Gemini Pro model for text and vision',
        vendor='Google',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=200*1024
        )
    ),
    LLMModel(
        name='gemini 2.0 flash',
        model_id='gemini-2.0-flash',
        api_provider='Gemini',
        category='vision',
        description='Gemini Flash model for text and vision',
        vendor='Google',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=1024*1024
        )
    ),
    LLMModel(
        name= "Nova Pro",
        category='vision',
        api_provider= "Bedrock",
        description= "Nova Pro is a vision understanding foundation model. It is multilingual and can reason over text, images and videos.",
        model_id= "amazon.nova-pro-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image', 'document', 'video'],
            output_modality=['text'],
            streaming=True,
            tool_use=True
        )
    ),
    LLMModel(
        name= "Nova Canvas",
        category='image',
        api_provider= "BedrockInvoke",
        description= "Nova image generation model. It generates images from text and allows users to upload and edit an existing image. ",
        model_id= "amazon.nova-canvas-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['image']
        )
    ),
    LLMModel(
        name='stable-diffusion',
        model_id='stability.stable-image-ultra-v1:0',
        api_provider='BedrockInvoke',
        category='image',
        description='Stable Diffusion Ultra for image generation',
        vendor='Stability AI',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['image']
        )
    ),
    LLMModel(
        name= "Nova Reel",
        category='video',
        api_provider= "BedrockInvoke",
        description= "Nova video generation model. It generates short high-definition videos, up to 9 seconds long from input images or a natural language prompt.",
        model_id= "amazon.nova-reel-v1:0",
        vendor= "Amazon",
        capabilities=LLM_CAPABILITIES(
            input_modality=['text', 'image'],
            output_modality=['video']
        )
    ),
    LLMModel(
        name='DeepSeek-R1',
        model_id='us.deepseek.r1-v1:0',
        api_provider='Bedrock',
        category='text',
        description='DeepSeek R1 model for text generation',
        vendor='DeepSeek',
        capabilities=LLM_CAPABILITIES(
            input_modality=['text'],
            output_modality=['text'],
            streaming=True,
            tool_use=True,
            context_window=32*1024
        )
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
            # Cache for models
            self._models_cache = None
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

    def _float_to_decimal(self, obj):
        """Helper function to convert float values to Decimal in nested dictionaries and lists"""
        if isinstance(obj, dict):
            return {key: self._float_to_decimal(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._float_to_decimal(item) for item in obj]
        elif isinstance(obj, float):
            return Decimal(str(obj))
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

    def _load_models_from_db(self) -> List[LLMModel]:
        """Load models from database and update cache"""
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

            # Update cache
            self._models_cache = sorted(models, key=lambda m: m.name)
            return self._models_cache
        except Exception as e:
            logger.error(f"Error loading models from database: {str(e)}")
            return []

    def flush_cache(self):
        """Force flush models cache"""
        logger.debug("Flushing models cache")
        self._models_cache = None

    def get_models(self, filter: Optional[Dict] = None) -> List[LLMModel]:
        """Get configured models from cache/database with optional filtering

        Args:
            filter: Optional dictionary of model properties to filter by.
                    Supported properties and capabilities: name, model_id, api_provider, vendor, input_modality, streaming etc.
                    Example: {'input_modality': ['vision']} returns only vision models

        Returns:
            List of LLMModel instances matching the filter criteria          
        """
        try:
            # Get models from cache or load from database
            if self._models_cache is None:
                models = self._load_models_from_db()
            else:
                models = self._models_cache
            
            # Apply filters if provided
            if filter:
                filtered_models = []
                for model in models:
                    matches = True
                    for key, value in filter.items():
                        # Handle capabilities filtering
                        if key in ['input_modality', 'output_modality', 'streaming', 'tool_use', 'context_window']:
                            if not model.capabilities:
                                matches = False
                                break
                            cap_value = getattr(model.capabilities, key)
                            # For modality lists, check if all required modalities are supported
                            if key in ['input_modality', 'output_modality']:
                                if not all(m in cap_value for m in value):
                                    matches = False
                                    break
                            # For other capabilities, direct comparison
                            elif cap_value != value:
                                matches = False
                                break
                        # Handle regular model attributes filtering
                        elif not hasattr(model, key) or getattr(model, key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_models.append(model)
                models = filtered_models

            # Return sort models by name for consistent display
            return sorted(models, key=lambda m: m.name) 
            
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
            
            # Convert models to dict format and ensure all numbers are Decimal
            models_data = [self._float_to_decimal(m.to_dict()) for m in models]
            models_data.append(self._float_to_decimal(model.to_dict()))
            
            # Update table and invalidate cache
            self.table.put_item(
                Item={
                    'setting_name': 'model_manager',
                    'type': 'global',
                    'models': models_data
                }
            )
            self.flush_cache()
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
            
            # Convert models to dict format and ensure all numbers are Decimal
            models_data = [self._float_to_decimal(m.to_dict()) for m in updated_models]
            
            # Update table and invalidate cache
            self.table.put_item(
                Item={
                    'setting_name': 'model_manager',
                    'type': 'global',
                    'models': models_data
                }
            )
            self.flush_cache()
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
            
            # Convert models to dict format and ensure all numbers are Decimal
            models_data = [self._float_to_decimal(m.to_dict()) for m in filtered_models]
            
            # Update table and invalidate cache
            self.table.put_item(
                Item={
                    'setting_name': 'model_manager',
                    'type': 'global',
                    'models': models_data
                }
            )
            self.flush_cache()
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
                models_data = [self._float_to_decimal(model.to_dict()) for model in DEFAULT_MODELS]
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
