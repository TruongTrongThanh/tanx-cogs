"""
Tool registry and loader for LLM function calling.
"""
import os
import importlib
import inspect
import logging
from typing import Dict, List, Any, Callable
from .base import BaseTool

log = logging.getLogger("red.tanx.llm.tools")


class ToolRegistry:
    """Registry for managing and loading tools."""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._load_tools()
    
    def set_discord_context(self, channel, message):
        """Set Discord context for tools that need it."""
        for tool in self.tools.values():
            if hasattr(tool, 'set_context'):
                tool.set_context(channel, message)
    
    def _load_tools(self):
        """Automatically load all tools from the tools directory."""
        tools_dir = os.path.dirname(__file__)
        
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and filename not in ['__init__.py', 'base.py']:
                module_name = filename[:-3]
                try:
                    module = importlib.import_module(f'.{module_name}', package='llm.tools')
                    
                    # Find all BaseTool subclasses in the module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        if issubclass(obj, BaseTool) and obj is not BaseTool:
                            tool_instance = obj()
                            self.tools[tool_instance.name] = tool_instance
                            log.info(f"Loaded tool: {tool_instance.name}")
                            
                except Exception as e:
                    log.error(f"Error loading tool module {module_name}: {e}")
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool schemas for all registered tools."""
        return [tool.get_schema() for tool in self.tools.values()]
    
    def get_tool(self, name: str) -> BaseTool:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        """Execute a tool with given arguments."""
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        
        try:
            return tool.execute(arguments)
        except Exception as e:
            log.error(f"Error executing tool {name}: {e}")
            return f"Error executing tool: {str(e)}"
    
    def list_tools(self) -> List[str]:
        """List all available tool names."""
        return list(self.tools.keys())
