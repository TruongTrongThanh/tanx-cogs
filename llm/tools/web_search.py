"""
Web search tool using Brave Search API.
"""
from typing import Dict, Any
import os
import aiohttp
import asyncio
from .base import BaseTool


class WebSearchTool(BaseTool):
    """Tool for searching the web using Brave Search API."""
    
    def __init__(self):
        self.api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        self.api_url = "https://api.search.brave.com/res/v1/web/search"
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "Search the web for current information using Brave Search. Use this when you need up-to-date information, facts, news, or answers that you don't have in your knowledge base."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                },
                "count": {
                    "type": "integer",
                    "description": "Number of results to return (default: 3, max: 10)",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Perform a web search using Brave Search API.
        
        Args:
            arguments: Dict with 'query' and optional 'count'
            
        Returns:
            Search results or error message
        """
        if not self.api_key:
            return (
                "Brave Search API is not configured. To enable web search:\n"
                "1. Get an API key from https://brave.com/search/api/\n"
                "2. Set the BRAVE_SEARCH_API_KEY environment variable\n"
                "3. Restart the bot"
            )
        
        query = arguments.get("query", "")
        count = min(arguments.get("count", 3), 10)  # Cap at 10 results
        
        if not query:
            return "Error: No search query provided"
        
        # Run async search in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self._search_async(query, count))
    
    async def _search_async(self, query: str, count: int) -> str:
        """
        Perform async web search.
        
        Args:
            query: Search query
            count: Number of results
            
        Returns:
            Formatted search results
        """
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": count,
            "text_decorations": False,
            "search_lang": "en"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.api_url,
                    headers=headers,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return f"Brave Search API error (status {response.status}): {error_text}"
                    
                    data = await response.json()
                    
                    # Format results
                    return self._format_results(data, query)
                    
        except aiohttp.ClientError as e:
            return f"Network error during web search: {str(e)}"
        except Exception as e:
            return f"Error performing web search: {str(e)}"
    
    def _format_results(self, data: Dict[str, Any], query: str) -> str:
        """
        Format search results for LLM consumption.
        
        Args:
            data: API response data
            query: Original search query
            
        Returns:
            Formatted string with search results
        """
        web_results = data.get("web", {}).get("results", [])
        
        if not web_results:
            return f"No search results found for '{query}'"
        
        formatted = f"Web search results for '{query}':\n\n"
        
        for i, result in enumerate(web_results[:10], 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            description = result.get("description", "No description available")
            
            formatted += f"{i}. {title}\n"
            formatted += f"   URL: {url}\n"
            formatted += f"   {description}\n\n"
        
        return formatted.strip()
