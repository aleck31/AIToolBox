# Copyright iX.
# SPDX-License-Identifier: MIT-0
import gradio as gr
from common import USER_CONF
from common.llm_config import (
    get_llm_models, add_llm_model, delete_llm_model,
    get_module_config, update_module_config
)

def format_config_text(config):
    """Format module config as display text"""
    if not config:
        return ""
    
    lines = []
    
    # Add default model
    lines.append(f"Default Model: {config.get('default_model', 'Not set')}")
    
    # Add system prompt if present
    if 'system_prompt' in config:
        lines.append(f"System Prompt: {config['system_prompt']}")
    
    # Add parameters section
    if 'parameters' in config:
        lines.append("Parameters:")
        for key, value in config['parameters'].items():
            lines.append(f"  {key}: {value}")
    
    # Add sub modules section
    if 'sub_modules' in config:
        lines.append("Sub Modules:")
        for name, sub_config in config['sub_modules'].items():
            lines.append(f"  {name}:")
            if 'system_prompt' in sub_config:
                lines.append(f"    System Prompt: {sub_config['system_prompt']}")
            if 'parameters' in sub_config:
                lines.append("    Parameters:")
                for key, value in sub_config['parameters'].items():
                    lines.append(f"      {key}: {value}")
    
    # Add description
    lines.append(f"Description: {config.get('description', 'n/a')}")

    return "\n".join(lines)

def add_model(name, model_id, provider, model_type, description):
    """Add a new LLM model"""
    try:
        if not name or not model_id:
            raise ValueError("Model name and ID are required")
        
        # Add new model with type
        add_llm_model(name, model_id, provider, model_type, description)
        gr.Info(f"Added new model: {name}")
        
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
        gr.Info(f"Deleted model: {name}")
        
        # Return empty value for input and updated models list for display
        models = get_llm_models()
        models_data = [[m['name'], m['model_id'], m.get('provider', ''), 
                       m.get('model_type', 'text'), m.get('description', '')] 
                      for m in models]
        return "", models_data
    except Exception as e:
        gr.Error(str(e))
        return name, None

def update_module_settings(module_name, config_text):
    """Update module settings from config text"""
    try:
        # Parse config text into dictionary
        config = {}
        current_section = None
        current_sub_module = None
        
        for line in config_text.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('Name:'):
                config['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('Default Model:'):
                config['default_model'] = line.split(':', 1)[1].strip()
            elif line.startswith('System Prompt:'):
                if current_sub_module:
                    if 'sub_modules' not in config:
                        config['sub_modules'] = {}
                    if current_sub_module not in config['sub_modules']:
                        config['sub_modules'][current_sub_module] = {}
                    config['sub_modules'][current_sub_module]['system_prompt'] = line.split(':', 1)[1].strip()
                else:
                    config['system_prompt'] = line.split(':', 1)[1].strip()
            elif line == 'Parameters:':
                current_section = 'parameters'
                if current_sub_module:
                    if 'sub_modules' not in config:
                        config['sub_modules'] = {}
                    if current_sub_module not in config['sub_modules']:
                        config['sub_modules'][current_sub_module] = {}
                    config['sub_modules'][current_sub_module]['parameters'] = {}
                else:
                    config['parameters'] = {}
            elif line == 'Sub Modules:':
                current_section = 'sub_modules'
                config['sub_modules'] = {}
            elif line.endswith(':'):
                if current_section == 'sub_modules':
                    current_sub_module = line[:-1].strip()
                    if current_sub_module not in config['sub_modules']:
                        config['sub_modules'][current_sub_module] = {}
            elif current_section == 'parameters':
                if ':' in line:
                    key, value = line.strip().split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    try:
                        # Try to convert value to number if possible
                        value = float(value) if '.' in value else int(value)
                    except ValueError:
                        pass
                    
                    if current_sub_module:
                        config['sub_modules'][current_sub_module]['parameters'][key] = value
                    else:
                        config['parameters'][key] = value
        
        # Update module config
        update_module_config(module_name, config)
        gr.Info(f"Updated {module_name} module settings")
        
        # Return updated configuration text
        return format_config_text(get_module_config(module_name))
        
    except Exception as e:
        gr.Error(f"Failed to update module settings: {str(e)}")
        raise
