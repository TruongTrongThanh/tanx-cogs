from redbot.core import commands
from discord.ext import tasks
import aiohttp
import json
from datetime import datetime
import os

class RecCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.windmill_token = os.getenv("WINDMILL_TOKEN")
        self.windmill_url = os.getenv("WINDMILL_URL")
        self.rec_channel_id = os.getenv("REC_CHANNEL_ID")
        self.rec_channel = None
        self.rec_task.start()
        if not self.windmill_token:
            print("Warning: WINDMILL_TOKEN environment variable not set.")
        if not self.windmill_url:
            print("Warning: WINDMILL_URL environment variable not set.")
        if not self.rec_channel_id:
            print("Warning: REC_CHANNEL_ID environment variable not set.")

    def cog_unload(self):
        self.rec_task.cancel()

    async def _call_windmill_api(self):
        """Helper method to call Windmill API"""
        if not self.windmill_token:
            print("Error: Windmill API token not set.")
            return None
        
        if not self.windmill_url:
            print("Error: Windmill API URL not set.")
            return None
        
        body = {}
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.windmill_token}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.windmill_url, json=body, headers=headers) as response:
                    result = await response.json()
                    output_text = result.get("text", "No output found.")
                    return output_text
        except aiohttp.ClientError as e:
            print(f"Error: Failed to connect to Windmill API: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse response JSON: {e}")
            return None
        except Exception as e:
            print(f"Error: Unexpected error occurred: {e}")
            return None

    @tasks.loop(hours=1)
    async def rec_task(self):
        """Background task that runs every Saturday at 10:00 AM"""
        now = datetime.now()
        # Saturday is weekday() == 5 (0=Monday, 6=Sunday)
        if now.weekday() == 5 and now.hour == 10:
            print("Running rec job - Saturday 10:00 AM!")
            result = await self._call_windmill_api()
            if result:
                if self.rec_channel:
                    await self.rec_channel.send(result)
                else:
                    print("No channel set. Set REC_CHANNEL_ID environment variable or use `.set_rec_channel` command.")
            else:
                print("Failed to get recommendations.")

    @rec_task.before_loop
    async def before_rec_task(self):
        """Wait until the bot is ready before starting the task"""
        await self.bot.wait_until_ready()
        # Load the channel from the environment variable if set
        if self.rec_channel_id:
            try:
                self.rec_channel = self.bot.get_channel(int(self.rec_channel_id))
                if not self.rec_channel:
                    print(f"Error: Channel with ID {self.rec_channel_id} not found.")
            except ValueError:
                print(f"Error: Invalid REC_CHANNEL_ID format: {self.rec_channel_id}")

    @commands.command()
    async def rec(self, ctx):
        """A command to output recommendations using LLM"""

        print("Starting recommendation process...")
        
        if not self.windmill_token:
            print("Error: WINDMILL_TOKEN environment variable not set.")
            await ctx.send("❌ Windmill token not configured. Please set the WINDMILL_TOKEN environment variable.")
            return
        
        async with ctx.typing():
            result = await self._call_windmill_api()
            if result:
                await ctx.send(result)
            else:
                await ctx.send("❌ Something went wrong. Please try again later.")