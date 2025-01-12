"""Module configurations tab implementation"""
import json
import gradio as gr
from core.logger import logger
from core.module_config import module_config

# List of available modules
MODULE_LIST = ['chatbot', 'chatbot-gemini', 'text', 'summary', 'vision', 'coding', 'oneshot', 'draw']

def format_paras_json(parameters):
    """Format module parameters as JSON text for UI display"""
    if not parameters:
        return "{}"

    display_parms = module_config._decimal_to_float(parameters)

    # List of parameters that should be integers
    int_params = ['max_tokens', 'top_k']
    for p in int_params:
        if p in display_parms and isinstance(display_parms[p], (int, float)):
            display_parms[p] = int(display_parms[p])
        
    return json.dumps(display_parms, indent=2)

def update_module_configs(module_name: str, params_json: str, tools: list, model: str):
    """Update all configs/settings of a specific module at once"""
    try:
        # Parse parameters JSON
        params = json.loads(params_json)
        
        # Get current config to preserve internal fields
        current_config = module_config.get_module_config(module_name)
        if not current_config:
            raise ValueError(f"Failed to get config for module: {module_name}")
        
        # Update with new values
        current_config.update({
            'default_model': model,
            'parameters': params,
            'enabled_tools': tools
        })
        
        # Update module config
        module_config.update_module_config(module_name, current_config)
        gr.Info(f"Updated {module_name} module settings", duration=3)
        
    except json.JSONDecodeError as e:
        gr.Error(f"Invalid JSON format: {str(e)}")
        raise
    except Exception as e:
        gr.Error(f"Failed to update module settings: {str(e)}")
        raise

def refresh_module_configs():
    """Refresh module configurations"""
    result = {}
    for module_name in MODULE_LIST:
        if config := module_config.get_module_config(module_name):
            result[module_name] = {
                'default_model': config.get('default_model', ''),
                'parameters': format_paras_json(config.get('parameters', {})),
                'enabled_tools': config.get('enabled_tools', [])
            }
    
    # Return a list of values for each field type across all modules
    models = [result[m]['default_model'] for m in MODULE_LIST]
    params = [result[m]['parameters'] for m in MODULE_LIST]
    tools = [result[m]['enabled_tools'] for m in MODULE_LIST]
    
    return models + params + tools
