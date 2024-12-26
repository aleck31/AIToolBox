from typing import Optional, Dict
from llm import LLMConfig
from llm.model_manager import model_manager
from ..session import SessionStore
from .chat_service import ChatService
from .gen_service import GenService
from core.logger import logger
from core.module_config import module_config


class ServiceFactory:
    """Factory for creating and configuring services"""
    
    _session_store = None
    
    @classmethod
    def get_session_store(cls) -> SessionStore:
        """Get or create session store instance"""
        if cls._session_store is None:
            try:
                cls._session_store = SessionStore()
            except Exception as e:
                logger.error(f"Failed to create session store: {str(e)}")
                raise
        return cls._session_store

    @staticmethod
    def create_default_llm_config(
        model_id: Optional[str] = None,
        inference_params: Optional[Dict] = None
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

            # Set default provider-specific parameters
            provider_defaults = {
                'BEDROCK': {
                    'max_tokens': 2048,
                    'temperature': 0.9,
                    'top_p': 0.9,
                    'top_k': 200
                },
                'GEMINI': {
                    'max_tokens': 1024,
                    'temperature': 0.7,
                    'top_p': 0.99,
                    'top_k': 200
                }
            }

            provider = model.api_provider.upper()
            if provider not in provider_defaults:
                raise ValueError(f"Unsupported API provider: {provider}")

            # Merge configurations with priority: inference_params > provider_defaults
            config = {
                "api_provider": model.api_provider,
                "model_id": model_id,
                **provider_defaults[provider],  # Provider defaults
                **(inference_params or {})      # Override with inference params if provided
            }

            return LLMConfig(**config)

        except Exception as e:
            logger.error(f"Failed to create default LLM config: {str(e)}")
            raise

    @classmethod
    def _get_llm_config_by_module(cls, module_name: str) -> LLMConfig:
        """Create LLM configuration for a module"""
        # Get model configuration from module config
        model_id = module_config.get_default_model(module_name)               
        llm_model = model_manager.get_model_by_id(model_id)
        if not llm_model:
            raise ValueError(f"Model not found: {model_id}")

        params = module_config.get_inference_params(module_name) or {}
        if params:                        
            # Create LLM config with module parameters
            return LLMConfig(
                api_provider=llm_model.api_provider,
                model_id=model_id,
                temperature=params.get('temperature', 0.7),
                max_tokens=int(params.get('max_tokens', 2048)),
                top_p=params.get('top_p', 0.99),
                top_k=params.get('top_k', 200)
            )
        else:
            return cls.create_default_llm_config(model_id=model_id)

    @classmethod
    def create_gen_service(cls, module_name: str) -> GenService:
        """Create and configure general service for modules"""
        try:
            llm_config = cls._get_llm_config_by_module(module_name)
            return GenService(llm_config)
        except Exception as e:
            logger.error(f"Failed to create service for {module_name}: {str(e)}")
            raise

    @classmethod
    def create_chat_service(cls, module_name: str) -> ChatService:
        """Create and configure chat service"""
        try:
            llm_config = cls._get_llm_config_by_module(module_name)
            return ChatService(llm_config)
        except Exception as e:
            logger.error(f"Failed to create service for {module_name}: {str(e)}")
            raise
