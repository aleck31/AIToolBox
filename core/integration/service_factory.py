from typing import Optional, Dict
from llm import LLMConfig
from llm.model_manager import model_manager
from .chat_service import ChatService
from .gen_service import GenService
from .draw_service import DrawService
from core.logger import logger
from core.module_config import module_config


class ServiceFactory:
    """Factory for creating and configuring services"""

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
                models = model_manager.init_default_models()

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
    def _get_llm_config_by_module(cls, module_name: str, model_id: str = None) -> LLMConfig:
        """Create LLM configuration for a module"""
        # Get model_id from module configuration if there are no model_id
        model_id = model_id or module_config.get_default_model(module_name)
        llm_model = model_manager.get_model_by_id(model_id)
        if not llm_model:
            raise ValueError(f"Model not found: {model_id}")
        
        # Get model configuration from module config
        if params := module_config.get_inference_params(module_name):                        
            # Create LLM config with module parameters
            logger.debug(f"[ServiceFactory] Creating LLM config for {module_name} with params: {params}")
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
    def _create_service(cls, service_class, module_name: str, model_id=None, updated_tools=None):
        """Generic service creation method
        
        Args:
            service_class: The service class to instantiate
            module_name: Name of the module requesting service
            model_id: Optional model ID to use as default
            updated_tools: Optional list of tool names to enable
            
        Returns:
            Configured service instance
        """
        try:
            logger.debug(f"[ServiceFactory] Creating {service_class.__name__} for {module_name} with model_id={model_id}")
            
            # Get LLM configuration if model_id provided
            llm_config = cls._get_llm_config_by_module(module_name, model_id) if model_id else None
            kwargs = {'llm_config': llm_config}
            logger.debug(f"[ServiceFactory] Created LLM config: {llm_config}")

            # Get tools from module configuration if no updated tools provided
            if enabled_tools := updated_tools or module_config.get_enabled_tools(module_name):
                kwargs['enabled_tools'] = enabled_tools
            
            return service_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to create {service_class.__name__} for {module_name}: {str(e)}")
            raise

    @classmethod
    def create_gen_service(cls, module_name: str, model_id=None, updated_tools=None) -> GenService:
        """Create and configure general service"""
        return cls._create_service(GenService, module_name, model_id, updated_tools)

    @classmethod
    def create_chat_service(cls, module_name: str, model_id=None, updated_tools=None) -> ChatService:
        """Create and configure chat service"""
        return cls._create_service(ChatService, module_name, model_id, updated_tools)

    @classmethod
    def create_draw_service(cls, module_name: str = 'draw', model_id=None, updated_tools=None) -> DrawService:
        """Create and configure draw service"""
        return cls._create_service(DrawService, module_name, model_id, updated_tools)
