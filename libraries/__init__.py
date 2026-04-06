"""
Shared libraries cog for tanx-cogs.
Provides common utilities like WindmillClient for other cogs.
"""
from redbot.core import commands
from .windmill_client import WindmillClient, get_windmill_client

__all__ = ["WindmillClient", "get_windmill_client", "Libraries"]


class Libraries(commands.Cog):
    """
    Utility cog providing shared libraries for other cogs.
    No user-facing commands - provides WindmillClient and other utilities.
    """
    
    def __init__(self, bot):
        self.bot = bot
        self.windmill_client = WindmillClient()


async def setup(bot):
    """Setup function for the libraries cog."""
    await bot.add_cog(Libraries(bot))
