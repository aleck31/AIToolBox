from typing import Optional
from llm import LLMConfig
from llm.model_manager import model_manager
from ..session import SessionManager
from .chat_service import ChatService
from core.config import env_config
from core.logger import logger
from utils.aws import get_secret

'''
class ServiceFactory:
    """Factory for creating and configuring services"""
    
    @staticmethod
    def create_session_manager() -> SessionManager:
        """Create and configure session manager"""
        try:
            # Create SessionManager which internally creates DynamoDBStorage
            return SessionManager()
            
        except Exception as e:
            logger.error(f"Failed to create session manager: {str(e)}")
            raise

    @staticmethod
    def create_default_llm_config(
        model_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> LLMConfig:
        """Create default LLM configuration"""
        try:
            # Initialize default models if none exist
            models = model_manager.get_models()
            if not models:
                model_manager.init_default_models()
                models = model_manager.get_models()

            # Get model configuration
            if model_id:
                # Find specific model
                model = next((m for m in models if m.model_id == model_id), None)
                if not model:
                    raise ValueError(f"Model not found: {model_id}")
            else:
                # Use first available model as default
                model = models[0]
                model_id = model.model_id

            # Create provider-specific configuration
            if model.api_provider.upper() == 'BEDROCK':
                region = region or env_config.bedrock_config['default_region']
                return LLMConfig(
                    api_provider=model.api_provider,
                    model_id=model_id,
                    max_tokens=4096,
                    temperature=0.9,
                    top_p=0.99
                )
            elif model.api_provider.upper() == 'GEMINI':

                return LLMConfig(
                    api_provider=model.api_provider,
                    model_id=model_id,
                    max_tokens=8192,
                    temperature=0.9,
                    top_p=0.99
                )
            else:
                raise ValueError(f"Unsupported API provider: {model.api_provider}")

        except Exception as e:
            logger.error(f"Failed to create default LLM config: {str(e)}")
            raise

    @staticmethod
    def create_chat_service(
        session_manager: Optional[SessionManager] = None,
        llm_config: Optional[LLMConfig] = None
    ) -> ChatService:
        """Create and configure chat service"""
        try:
            # Create session manager if not provided
            if session_manager is None:
                session_manager = ServiceFactory.create_session_manager()
                
            # Create default LLM config if not provided
            if llm_config is None:
                llm_config = ServiceFactory.create_default_llm_config()
                
            return ChatService(
                session_manager=session_manager,
                default_model_config=llm_config
            )
            
        except Exception as e:
            logger.error(f"Failed to create chat service: {str(e)}")
            raise

    @classmethod
    def create_default_services(cls) -> ChatService:
        """Create services with default configuration"""
        try:
            # Create session manager
            session_manager = cls.create_session_manager()
            
            # Create default LLM config
            llm_config = cls.create_default_llm_config()
            
            # Create chat service
            return cls.create_chat_service(
                session_manager=session_manager,
                llm_config=llm_config
            )
            
        except Exception as e:
            logger.error(f"Failed to create default services: {str(e)}")
            raise
'''
