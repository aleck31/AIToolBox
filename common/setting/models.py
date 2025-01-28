"""LLM Models tab implementation"""
import gradio as gr
from llm.model_manager import model_manager, LLMModel

def get_model_choices():
    """Get list of available models for dropdown"""
    models = model_manager.get_models()
    return [(f"{m.name}, {m.api_provider}", m.model_id) for m in models]

def refresh_models():
    """Refresh models list"""
    models = model_manager.get_models()
    models_data = [[m.name, m.model_id, m.api_provider, m.vendor, m.modality, m.description] 
                  for m in models]
    return models_data

def add_model(name, model_id, api_provider, vendor, modality, description):
    """Add a new LLM model"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
        
        model = LLMModel(
            name=name,
            model_id=model_id,
            api_provider=api_provider,
            vendor=vendor,
            modality=modality,
            description=description
        )
        
        model_manager.add_model(model)
        gr.Info(f"Added new model: {name}", duration=3)
        
        return refresh_models()
    except Exception as e:
        gr.Error(str(e))
        return None

def update_model(name, model_id, api_provider, vendor, modality, description):
    """Update an existing LLM model"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
            
        updated_model = LLMModel(
            name=name,
            model_id=model_id,
            api_provider=api_provider,
            vendor=vendor,
            modality=modality,
            description=description
        )
        
        model_manager.update_model(updated_model)
        gr.Info(f"Updated model: {name}", duration=3)
        
        return refresh_models()
    except Exception as e:
        gr.Error(str(e))
        return None

def delete_model(model_id):
    """Delete an LLM model"""
    try:
        if not model_id:
            raise ValueError("Model ID is required")
        
        model_manager.delete_model_by_id(model_id)
        gr.Info(f"Deleted model: {model_id}", duration=3)
        
        return refresh_models()
    except Exception as e:
        gr.Error(str(e))
        return None
