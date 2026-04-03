"""
Discord message search tool for retrieving message history.
"""
from typing import Dict, Any
import logging
from datetime import datetime, timedelta

from .base import BaseTool

log = logging.getLogger("red.tanx.llm.tools.discord_search")


class DiscordSearchTool(BaseTool):
    """Tool for searching Discord message history in the current channel."""
    
    def __init__(self):
        self.current_channel = None
        self.current_message = None
    
    def set_context(self, channel, message):
        """Set the current Discord context for this tool."""
        self.current_channel = channel
        self.current_message = message
    
    @property
    def name(self) -> str:
        return "search_discord_messages"
    
    @property
    def description(self) -> str:
        return (
            "Search recent message history in the current Discord channel. "
            "Use this to get more context about the conversation, find previous messages, "
            "or understand what users were discussing. You can search by keywords, "
            "get recent messages, or retrieve messages from a specific user."
        )
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Search query to find relevant messages. If empty, returns recent messages. "
                        "Can be keywords, phrases, or topics to search for."
                    )
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to return (default: 10, max: 50)",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "from_user": {
                    "type": "string",
                    "description": "Optional: Filter messages from a specific username (without @)",
                }
            },
            "required": ["query"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        """
        Search Discord message history.
        
        Args:
            arguments: Dict with 'query', 'limit', and optional 'from_user'
            
        Returns:
            Formatted string with search results
        """
        if not self.current_channel:
            return "Error: Discord channel context not available. This tool can only be used during active Discord conversations."
        
        query = arguments.get("query", "").lower()
        limit = min(arguments.get("limit", 10), 50)
        from_user = arguments.get("from_user", "").lower() if arguments.get("from_user") else None
        
        try:
            # This needs to be run synchronously, but discord.py methods are async
            # We'll use a helper to run the async code
            import asyncio
            
            # Get the current event loop or create one
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Create and run the async search
            if loop.is_running():
                # We're already in an async context, need to use a different approach
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        asyncio.run,
                        self._search_messages_async(query, limit, from_user)
                    )
                    return future.result(timeout=30)
            else:
                return loop.run_until_complete(
                    self._search_messages_async(query, limit, from_user)
                )
                
        except Exception as e:
            log.error(f"Error searching Discord messages: {e}", exc_info=True)
            return f"Error searching messages: {str(e)}"
    
    async def _search_messages_async(self, query: str, limit: int, from_user: str = None) -> str:
        """
        Async helper to search messages.
        
        Args:
            query: Search query
            limit: Max messages to return
            from_user: Optional username filter
            
        Returns:
            Formatted search results
        """
        messages = []
        count = 0
        
        # Fetch message history (fetch more than limit to account for filtering)
        fetch_limit = min(limit * 3, 100)
        
        try:
            async for message in self.current_channel.history(limit=fetch_limit):
                # Skip the current message being processed
                if self.current_message and message.id == self.current_message.id:
                    continue
                
                # Skip bot messages
                if message.author.bot:
                    continue
                
                # Filter by user if specified
                if from_user and message.author.name.lower() != from_user:
                    continue
                
                # Search by query if provided
                if query and query not in message.content.lower():
                    continue
                
                # Format the message
                timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
                author = message.author.name
                content = message.content[:200]  # Truncate long messages
                
                # Add attachment info if any
                attachment_info = ""
                if message.attachments:
                    att_types = []
                    for att in message.attachments:
                        if att.content_type:
                            if att.content_type.startswith('image/'):
                                att_types.append('image')
                            elif att.content_type.startswith('video/'):
                                att_types.append('video')
                            else:
                                att_types.append('file')
                    if att_types:
                        attachment_info = f" [Attachments: {', '.join(att_types)}]"
                
                messages.append(f"[{timestamp}] @{author}: {content}{attachment_info}")
                count += 1
                
                if count >= limit:
                    break
            
            if not messages:
                if query:
                    return f"No messages found matching '{query}'"
                else:
                    return "No recent messages found in this channel"
            
            result = f"Found {len(messages)} message(s)"
            if query:
                result += f" matching '{query}'"
            if from_user:
                result += f" from @{from_user}"
            result += ":\n\n"
            result += "\n".join(messages)
            
            return result
            
        except Exception as e:
            log.error(f"Error fetching message history: {e}", exc_info=True)
            return f"Error fetching message history: {str(e)}"
