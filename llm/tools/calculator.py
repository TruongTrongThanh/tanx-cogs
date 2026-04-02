"""
Calculator tool for mathematical operations.
"""
from typing import Dict, Any
from .base import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing mathematical calculations."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Perform mathematical calculations. Supports basic arithmetic, exponents, and common math functions."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '2 + 2', '15 * 8', 'sqrt(16)', '2**3')"
                }
            },
            "required": ["expression"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Execute a mathematical calculation.
        
        Args:
            arguments: Dict with 'expression' key
            
        Returns:
            Result of the calculation as a string
        """
        expression = arguments.get("expression", "")
        
        if not expression:
            return "Error: No expression provided"
        
        try:
            # Safe eval with limited scope
            import math
            safe_dict = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
            }
            
            # Evaluate the expression safely
            result = eval(expression, {"__builtins__": {}}, safe_dict)
            return f"The result of {expression} is {result}"
            
        except Exception as e:
            return f"Error calculating '{expression}': {str(e)}"
