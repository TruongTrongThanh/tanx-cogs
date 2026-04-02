"""
Base class for LLM tools.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseTool(ABC):
    """Base class for all tools that can be called by the LLM."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The name of the tool (used for function calling)."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the tool does."""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """JSON Schema for the tool's parameters."""
        pass
    
    @abstractmethod
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Execute the tool with given arguments.
        
        Args:
            arguments: Dictionary of arguments matching the parameter schema
            
        Returns:
            String result to send back to the LLM
        """
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """Get OpenAI-compatible function schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
