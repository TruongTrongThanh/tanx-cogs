"""
Current time and date tool.
"""
from typing import Dict, Any
from datetime import datetime
from .base import BaseTool


class CurrentTimeTool(BaseTool):
    """Tool for getting current time and date information."""
    
    @property
    def name(self) -> str:
        return "get_current_time"
    
    @property
    def description(self) -> str:
        return "Get the current date and time. Use this when users ask about the current time, date, day of week, etc."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "description": "Format string for the datetime (optional). If not provided, returns full datetime.",
                    "enum": ["full", "date", "time", "day"]
                }
            },
            "required": []
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Get current time/date.
        
        Args:
            arguments: Dict with optional 'format' key
            
        Returns:
            Current time/date as a string
        """
        now = datetime.now()
        format_type = arguments.get("format", "full")
        
        if format_type == "date":
            return now.strftime("%Y-%m-%d")
        elif format_type == "time":
            return now.strftime("%H:%M:%S")
        elif format_type == "day":
            return now.strftime("%A, %B %d, %Y")
        else:  # full
            return now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
