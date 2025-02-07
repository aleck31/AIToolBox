import inspect
import importlib
from typing import Dict, Any, List
from core.logger import logger


class BedrockToolRegistry:
    """Registry for managing available tools"""
    
    def __init__(self):
        self.tools = {}
        self.tool_specs = {}
        
    def load_tool(self, package_name: str, tool_name: str) -> None:
        """Load a specific tool from a package"""
        try:
            # Import the module
            tool_module = importlib.import_module(f"llm.tools.{package_name}")
            
            # Verify tool function exists and is callable
            if not hasattr(tool_module, tool_name):
                logger.warning(f"Tool function {tool_name} not found in module {package_name}")
                return
                
            func = getattr(tool_module, tool_name)
            if not inspect.isfunction(func):
                logger.warning(f"{tool_name} in {package_name} is not a function")
                return
                
            # Register the tool function
            self.tools[tool_name] = func
            logger.info(f"Registered tool function: {tool_name}")
            
            # Get and register tool specification
            if hasattr(tool_module, 'list_of_tools_specs'):
                for spec in tool_module.list_of_tools_specs:
                    if spec.get('toolSpec', {}).get('name') == tool_name:
                        self.tool_specs[tool_name] = spec
                        logger.info(f"Registered tool specification: {tool_name}")
                        break
                else:
                    logger.warning(f"No tool specification found for {tool_name} in {package_name}")
                
        except ImportError as e:
            logger.error(f"Failed to import tool_module {package_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Error loading tool {tool_name} from {package_name}: {str(e)}")

    def get_tool_specs(self) -> List[Dict]:
        """Get list of all loaded tool specifications"""
        return list(self.tool_specs.values())
        
    def get_tool_spec(self, tool_name: str) -> Dict:
        """Get specification for a specific tool"""
        if tool_name not in self.tool_specs:
            # Try to load the tool if it's in the package map
            if tool_name in Tool_Packages:
                self.load_tool(Tool_Packages[tool_name], tool_name)
                
        return self.tool_specs.get(tool_name)
        
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """Execute a loaded tool"""
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")
            
        try:
            tool_func = self.tools[tool_name]
            # Check if the tool function is async
            if inspect.iscoroutinefunction(tool_func):
                return await tool_func(**kwargs)
            else:
                return tool_func(**kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            return {"error": str(e)}

# Map of tool names to their package names
Tool_Packages = {
    'get_weather': 'weather_tools',
    # 'get_location_coords': 'weather_tools',
    'get_text_from_url': 'web_tools',
    'generate_image': 'draw_tools'
}

# Create global registry instance
tool_registry = BedrockToolRegistry()

# Initialize default tools
for tool_name, package in Tool_Packages.items():
    tool_registry.load_tool(package, tool_name)
