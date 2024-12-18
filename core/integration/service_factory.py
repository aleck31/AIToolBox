import ast
from typing import Optional
from llm import LLMConfig, ModelProvider
from ..session.dynamodb_manager import DynamoDBSessionManager
from ..session.session_manager import AuthSessionManager
from .chat_service import ChatService
from core.config import env_config
from core.logger import logger
from utils.aws import get_aws_client


def get_secret(secret_name):
    '''Get user dict from Secrets Manager'''
    try:
        # Get Secrets Manager client using centralized AWS configuration
        client = get_aws_client('secretsmanager')
        
        response = client.get_secret_value(
            SecretId=secret_name
        )
        
        # Decrypts secret using the associated KMS key.
        secret = ast.literal_eval(response['SecretString'])
        return secret
        
    except Exception as ex:
        logger.error(f"Error getting secret {secret_name}: {str(ex)}")
        raise


class ServiceFactory:
    """Factory for creating and configuring services"""
    
    @staticmethod
    def create_session_manager(
        table_name: str = "aibox-sessions",
        session_ttl: int = 7200,
        region: str = env_config.default_region,
        with_auth: bool = True
    ) -> AuthSessionManager:
        """Create and configure session manager"""
        try:
            # Create base DynamoDB manager
            base_manager = DynamoDBSessionManager(
                table_name=table_name,
                session_ttl=session_ttl,
                region_name=region
            )
            
            # Wrap with auth manager if requested
            if with_auth:
                return AuthSessionManager(base_manager=base_manager)
            return base_manager
            
        except Exception as e:
            logger.error(f"Failed to create session manager: {str(e)}")
            raise

    @staticmethod
    def create_default_llm_config(
        provider: ModelProvider = ModelProvider.BEDROCK,
        model_id: Optional[str] = None,
        region: Optional[str] = None
    ) -> LLMConfig:
        """Create default LLM configuration"""
        if provider == ModelProvider.BEDROCK:
            # Default to Claude if no model specified
            model_id = model_id or "anthropic.claude-v2"
            region = region or env_config.bedrock_config['default_region']
            
            return LLMConfig(
                provider=provider,
                model_id=model_id,
                region=region,
                max_tokens=4096,
                temperature=0.9,
                top_p=0.99
            )
            
        elif provider == ModelProvider.GEMINI:
            # Default to Gemini Pro if no model specified
            model_id = model_id or "gemini-pro"
            gemini_secret_key=env_config.gemini_config['secret_id']
            api_key = get_secret(gemini_secret_key).get('api_key')
            
            return LLMConfig(
                provider=provider,
                model_id=model_id,
                api_key=api_key,
                max_tokens=8192,
                temperature=0.9,
                top_p=0.99
            )
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def create_chat_service(
        session_manager: Optional[AuthSessionManager] = None,
        llm_config: Optional[LLMConfig] = None,
        with_auth: bool = True
    ) -> ChatService:
        """Create and configure chat service"""
        try:
            # Create session manager if not provided
            if session_manager is None:
                session_manager = ServiceFactory.create_session_manager(with_auth=with_auth)
                
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
    def create_default_services(cls, with_auth: bool = True) -> ChatService:
        """Create services with default configuration"""
        try:
            # Create session manager
            session_manager = cls.create_session_manager(with_auth=with_auth)
            
            # Create default LLM config
            llm_config = cls.create_default_llm_config()
            
            # Create chat service
            return cls.create_chat_service(
                session_manager=session_manager,
                llm_config=llm_config,
                with_auth=with_auth
            )
            
        except Exception as e:
            logger.error(f"Failed to create default services: {str(e)}")
            raise
