import discord
from discord.ext import commands

class Panel(commands.Cog):
    """Panel command cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @commands.command(name="panel")
    async def panel_command(self, ctx: commands.Context):
        """Displays the panel"""
        await ctx.send("Panel command works!")
        
    @commands.Cog.listener()
    async def on_ready(self):
        print("Panel cog is ready!")

async def setup(bot: commands.Bot):
    await bot.add_cog(Panel(bot))
