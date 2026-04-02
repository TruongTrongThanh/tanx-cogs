from redbot.core import commands
from discord.ext import tasks
import logging
from datetime import datetime
import os
import sys

# Add parent directory to path to import libraries
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from libraries.windmill_client import get_windmill_client

log = logging.getLogger("red.tanx.rec")

class Rec(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.windmill_client = get_windmill_client()
        self.rec_channel_id = os.getenv("REC_CHANNEL_ID")
        self.rec_channel = None
        self.rec_task.start()
        
        if not self.rec_channel_id:
            log.warning("REC_CHANNEL_ID environment variable not set.")

    def cog_unload(self):
        self.rec_task.cancel()

    async def _call_windmill_api(self):
        """Call Windmill API to get recommendations"""
        if not self.windmill_client.is_configured():
            log.error("Windmill API not configured.")
            return None
        
        body = {}
        result = await self.windmill_client.call_api(body, path="recommend")
        
        if result:
            return result.get("text", "No output found.")
        return None

    @tasks.loop(hours=1)
    async def rec_task(self):
        """Background task that runs every Saturday at 10:00 AM"""
        now = datetime.now()
        # Saturday is weekday() == 5 (0=Monday, 6=Sunday)
        if now.weekday() == 5 and now.hour == 10:
            log.info("Running rec job - Saturday 10:00 AM!")
            result = await self._call_windmill_api()
            if result:
                if self.rec_channel:
                    await self.rec_channel.send(result)
                else:
                    log.warning("No channel set. Set REC_CHANNEL_ID environment variable or use `.set_rec_channel` command.")
            else:
                log.error("Failed to get recommendations.")

    @rec_task.before_loop
    async def before_rec_task(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        # Load the channel from the environment variable if set
        if self.rec_channel_id:
            try:
                self.rec_channel = self.bot.get_channel(int(self.rec_channel_id))
                if not self.rec_channel:
                    log.error(f"Channel with ID {self.rec_channel_id} not found.")
            except ValueError:
                log.error(f"Invalid REC_CHANNEL_ID format: {self.rec_channel_id}")

    @commands.command()
    async def rec(self, ctx):
        """A command to output recommendations using LLM"""
        log.info("Starting recommendation process...")
        
        if not self.windmill_client.is_configured():
            log.error("Windmill client not configured.")
            await ctx.send("❌ Windmill not configured. Please set WINDMILL_TOKEN and WINDMILL_URL environment variables.")
            return
        
        async with ctx.typing():
            result = await self._call_windmill_api()
            if result:
                await ctx.send(result)
            else:
                await ctx.send("❌ Something went wrong. Please try again later.")