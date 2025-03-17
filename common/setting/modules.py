"""Handler implementation for Module configurations tab"""
import json
from typing import Dict, List, Optional, Any
import gradio as gr
from core.logger import logger
from core.module_config import module_config


# List of available modules
MODULE_LIST = ['assistant', 'chatbot', 'text', 'summary', 'vision', 'asking', 'coding', 'draw']


class ModuleHandlers:
    """Handlers for module configuration management"""

    # Parameters that should be integers
    INT_PARAMS = ['max_tokens', 'top_k', 'width', 'height', 'steps']

    # Shared module config instance
    _module_config = module_config

    @classmethod
    def _format_parameters_json(cls, parameters: Optional[Dict]) -> str:
        """Format module parameters as JSON text for UI display"""
        if not parameters:
            return "{}"

        display_params = cls._module_config._decimal_to_float(parameters)

        # Convert specified parameters to integers
        for param in cls.INT_PARAMS:
            if param in display_params and isinstance(display_params[param], (int, float)):
                display_params[param] = int(display_params[param])

        return json.dumps(display_params, indent=2)

    @classmethod
    def _validate_and_parse_json(cls, json_str: str) -> Dict:
        """Validate and parse JSON string"""
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"[ModuleHandlers] Invalid JSON format: {str(e)}")
            raise ValueError(f"Invalid JSON format: {str(e)}")

    @classmethod
    def update_module_configs(cls, module_name: str, params_json: str, 
                            tools: List[str], model: str) -> None:
        """Update all configs/settings of a specific module at once"""
        try:
            # Parse and validate parameters JSON
            params = cls._validate_and_parse_json(params_json)

            # Get and validate current config
            current_config = cls._module_config.get_module_config(module_name)
            if not current_config:
                raise ValueError(f"Failed to get config for module: {module_name}")

            # Update with new values
            current_config.update({
                'default_model': model,
                'parameters': params,
                'enabled_tools': tools
            })

            # Update module config
            cls._module_config.update_module_config(module_name, current_config)
            gr.Info(f"Updated {module_name} module settings", duration=3)

        except Exception as e:
            logger.error(f"[ModuleHandlers] Failed to update module settings: {str(e)}")
            gr.Error(f"Failed to update module settings: {str(e)}")
            raise

    @classmethod
    def refresh_module_configs(cls) -> List[Any]:
        """Refresh module configurations"""
        try:
            result: Dict[str, Dict] = {}

            # Gather configurations for all modules
            for module_name in MODULE_LIST:
                if config := cls._module_config.get_module_config(module_name):
                    result[module_name] = {
                        'default_model': config.get('default_model', ''),
                        'parameters': cls._format_parameters_json(config.get('parameters', {})),
                        'enabled_tools': config.get('enabled_tools', [])
                    }

            # Return lists of values for each field type
            models = [result[m]['default_model'] for m in MODULE_LIST]
            params = [result[m]['parameters'] for m in MODULE_LIST]
            tools = [result[m]['enabled_tools'] for m in MODULE_LIST]

            return models + params + tools

        except Exception as e:
            logger.error(f"[ModuleHandlers] Error refreshing module configs: {str(e)}")
            gr.Error(f"Failed to refresh module configurations: {str(e)}")
            return ['' for _ in range(len(MODULE_LIST) * 3)]  # Return empty values
