# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
import json
from decimal import Decimal
from core.logger import logger
from core.module_config import module_config
from llm.model_manager import model_manager, LLMModel


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(x) for x in obj]
    return obj


def format_config_json(config):
    """Format module config as JSON text"""
    if not config:
        return ""
    
    # Create a clean config dict without internal fields
    display_config = {}
    
    # Add core fields
    if 'default_model' in config:
        display_config['default_model'] = config['default_model']
    if 'parameters' in config:
        display_config['parameters'] = config['parameters']
    if 'sub_modules' in config:
        display_config['sub_modules'] = config['sub_modules']
    if 'description' in config:
        display_config['description'] = config['description']
        
    # Convert Decimal to float before JSON serialization
    display_config = decimal_to_float(display_config)

    if 'parameters' in display_config:
        params = display_config['parameters'].copy()
        if 'max_tokens' in params:
            display_config['parameters']['max_tokens'] = int(params.pop('max_tokens'))
        
    # Convert to formatted JSON string
    return json.dumps(display_config, indent=2)


def add_model(name, model_id, api_provider, type, description):
    """Add a new LLM model"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
        
        # Create new LLMModel instance
        model = LLMModel(
            name=name,
            model_id=model_id,
            api_provider=api_provider,
            type=type,
            description=description
        )
        
        # Add model using ModelManager
        model_manager.add_model(model)
        gr.Info(
            f"Added new model: {name}",
            duration=3
        )
        
        # Return empty values for inputs and updated models list for display
        models = model_manager.get_models()
        models_data = [[m.name, m.model_id, m.api_provider, m.type, m.description] 
                      for m in models]
        return "", "", "", "", "", models_data
    except Exception as e:
        gr.Error(str(e))
        return name, model_id, api_provider, type, description, None


def delete_model(model_id):
    """Delete an LLM model"""
    try:
        if not model_id:
            raise ValueError("Model ID is required")
        
        # Delete model using ModelManager
        model_manager.delete_model(model_id)
        gr.Info(
            f"Deleted model: {model_id}",
            duration=3
        )
        
        # Return empty value for input and updated models list for display
        models = model_manager.get_models()
        models_data = [[m.name, m.model_id, m.api_provider, m.type, m.description] 
                      for m in models]
        return "", models_data
    except Exception as e:
        gr.Error(str(e))
        return model_id, None


def update_module_configs(module_name, config_json):
    """Update module settings from JSON config text"""
    try:
        # Parse JSON config text
        config = json.loads(config_json)
        
        # Get current config to preserve internal fields
        current_config = module_config.get_module_config(module_name)
        if not current_config:
            raise ValueError(f"Failed to get current config for module: {module_name}")
            
        # Update with new values while preserving internal fields
        current_config.update(config)
        
        # Update module config
        module_config.update_module_config(module_name, current_config)
        gr.Info(
            f"Updated {module_name} module settings",
            duration=3
        )
        
        # Return updated configuration text
        return format_config_json(module_config.get_module_config(module_name))
        
    except json.JSONDecodeError as e:
        gr.Error(f"Invalid JSON format: {str(e)}")
        raise
    except Exception as e:
        gr.Error(f"Failed to update module settings: {str(e)}")
        raise