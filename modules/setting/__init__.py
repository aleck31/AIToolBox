# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
import json
from decimal import Decimal
from common.logger import logger
from common.llm_config import (
    get_llm_models, add_llm_model, delete_llm_model,
    get_module_config, update_module_config
)


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
    if 'system_prompt' in config:
        display_config['system_prompt'] = config['system_prompt']
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


def add_model(name, model_id, provider, model_type, description):
    """Add a new LLM model"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
        
        # Add new model with type
        add_llm_model(name, model_id, provider, model_type, description)
        gr.Info(
            f"Added new model: {name}",
            duration=3
        )
        
        # Return empty values for inputs and updated models list for display
        models = get_llm_models()
        models_data = [[m['name'], m['model_id'], m.get('provider', ''), 
                       m.get('model_type', 'text'), m.get('description', '')] 
                      for m in models]
        return "", "", "", "", "", models_data
    except Exception as e:
        gr.Error(str(e))
        return name, model_id, provider, model_type, description, None


def delete_model(name):
    """Delete an LLM model"""
    try:
        if not name:
            raise ValueError("Model name is required")
        delete_llm_model(name)
        gr.Info(
            f"Deleted model: {name}",
            duration=3
        )
        
        # Return empty value for input and updated models list for display
        models = get_llm_models()
        models_data = [[m['name'], m['model_id'], m.get('provider', ''), 
                       m.get('model_type', 'text'), m.get('description', '')] 
                      for m in models]
        return "", models_data
    except Exception as e:
        gr.Error(str(e))
        return name, None


def update_module_configs(module_name, config_json):
    """Update module settings from JSON config text"""
    try:
        # Parse JSON config text
        config = json.loads(config_json)
        
        # Get current config to preserve internal fields
        current_config = get_module_config(module_name)
        if not current_config:
            raise ValueError(f"Failed to get current config for module: {module_name}")
            
        # Update with new values while preserving internal fields
        current_config.update(config)
        
        # Update module config
        update_module_config(module_name, current_config)
        gr.Info(
            f"Updated {module_name} module settings",
            duration=3
        )
        
        # Return updated configuration text
        return format_config_json(get_module_config(module_name))
        
    except json.JSONDecodeError as e:
        gr.Error(f"Invalid JSON format: {str(e)}")
        raise
    except Exception as e:
        gr.Error(f"Failed to update module settings: {str(e)}")
        raise
