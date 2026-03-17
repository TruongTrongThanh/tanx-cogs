from .reccog import RecCog


async def setup(bot):
    await bot.add_cog(RecCog(bot))