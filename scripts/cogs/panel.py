import discord
from discord.ext import commands
from discord import app_commands

class Panel(commands.Cog):
    """Panel command and components"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(
        name="panel",
        description="Display the main control panel"
    )
    async def panel(self, interaction: discord.Interaction):
        """Display the main control panel."""
        
        # Create empty embed
        embed = discord.Embed(
            title="Control Panel",
            description="Welcome to the control panel!",
            color=discord.Color.blurple()
        )
        
        # Send the embed
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Panel(bot))
