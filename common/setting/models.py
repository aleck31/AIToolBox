"""Handler implementation for Model Management tab"""
import gradio as gr
from typing import List, Tuple, Optional
from llm.model_manager import model_manager, LLMModel, LLM_CAPABILITIES
from core.logger import logger


class ModelHandlers:
    """Handlers for LLM model management"""

    # Shared model manager instance
    _model_manager = model_manager

    @classmethod
    def get_model_choices(cls) -> List[Tuple[str, str]]:
        """Get list of available models for dropdown"""
        try:
            models = cls._model_manager.get_models()
            return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]
        except Exception as e:
            logger.error(f"[ModelHandlers] Error getting model choices: {str(e)}")
            return []

    @classmethod
    def refresh_models(cls) -> List[List]:
        """Refresh models list"""
        try:
            models = cls._model_manager.get_models()
            return [[
                m.name, m.model_id, m.api_provider, m.vendor, m.category,
                ", ".join(m.capabilities.input_modality),
                ", ".join(m.capabilities.output_modality),
                m.capabilities.streaming,
                m.capabilities.tool_use,
                m.capabilities.context_window, 
                m.description
            ] for m in models]
        except Exception as e:
            logger.error(f"[ModelHandlers] Error refreshing models: {str(e)}")
            gr.Error(f"Failed to refresh models: {str(e)}")
            return []

    @classmethod
    def _create_model(cls, name: str, model_id: str, api_provider: str,
                     vendor: str, category: str, description: str,
                     input_modality: List[str], output_modality: List[str],
                     streaming: bool, tool_use: bool, context_window: int) -> LLMModel:
        """Create a new LLM model instance with validation"""
        if not name or not model_id:
            raise ValueError("Model name and ID are required")

        capabilities = LLM_CAPABILITIES(
            input_modality=input_modality,
            output_modality=output_modality,
            streaming=streaming,
            tool_use=tool_use,
            context_window=context_window
        )

        return LLMModel(
            name=name,
            model_id=model_id,
            api_provider=api_provider,
            vendor=vendor,
            category=category,
            description=description,
            capabilities=capabilities
        )

    @classmethod
    def add_model(cls, name: str, model_id: str, api_provider: str,
                  vendor: str, category: str, description: str,
                  input_modality: List[str], output_modality: List[str],
                  streaming: bool, tool_use: bool, context_window: int) -> Optional[List[List]]:
        """Add a new LLM model"""
        try:
            model = cls._create_model(name, model_id, api_provider, vendor, category, description,
                                    input_modality, output_modality, streaming, tool_use, context_window)
            cls._model_manager.add_model(model)
            gr.Info(f"Added new model: {name}", duration=3)
            return cls.refresh_models()
        except Exception as e:
            logger.error(f"[ModelHandlers] Error adding model: {str(e)}")
            gr.Error(str(e))
            return None

    @classmethod
    def update_model(cls, name: str, model_id: str, api_provider: str,
                    vendor: str, category: str, description: str,
                    input_modality: List[str], output_modality: List[str],
                    streaming: bool, tool_use: bool, context_window: int) -> Optional[List[List]]:
        """Update an existing LLM model"""
        try:
            model = cls._create_model(name, model_id, api_provider, vendor, category, description,
                                    input_modality, output_modality, streaming, tool_use, context_window)
            cls._model_manager.update_model(model)
            gr.Info(f"Updated model: {name}", duration=3)
            return cls.refresh_models()
        except Exception as e:
            logger.error(f"[ModelHandlers] Error updating model: {str(e)}")
            gr.Error(str(e))
            return None

    @classmethod
    def delete_model(cls, model_id: str) -> Optional[List[List]]:
        """Delete an LLM model"""
        try:
            if not model_id:
                raise ValueError("Model ID is required")
            
            cls._model_manager.delete_model_by_id(model_id)
            gr.Info(f"Deleted model: {model_id}", duration=3)
            return cls.refresh_models()
        except Exception as e:
            logger.error(f"[ModelHandlers] Error deleting model: {str(e)}")
            gr.Error(str(e))
            return None
