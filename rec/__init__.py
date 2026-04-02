from .rec import Rec


async def setup(bot):
    await bot.add_cog(Rec(bot))