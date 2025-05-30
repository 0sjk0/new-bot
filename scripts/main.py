import os
import sys
import logging
from pathlib import Path
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Configure logging with separate handlers for file and console
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

# File handler - logs everything to file
file_handler = logging.FileHandler('bot.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Console handler - logs to terminal
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(console_handler)

# Disable discord's debug logging
logging.getLogger('discord').setLevel(logging.WARNING)

class WhiteoutBot(commands.Bot):
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        # Initialize the bot
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Load environment variables
        self._load_env()
        
    def _load_env(self):
        """Load environment variables from config/.env"""
        env_path = Path("config/.env")
        if not env_path.exists():
            logger.error("No .env file found in config/.env")
            sys.exit(1)
            
        load_dotenv(env_path)
        self.token = os.getenv('BOT_TOKEN')
        
        if not self.token:
            logger.error("BOT_TOKEN not found in config/.env")
            sys.exit(1)

    async def load_all_cogs(self):
        """Load all cogs from the cogs directory"""
        try:
            # Get the current file's directory
            current_dir = Path(__file__).parent
            cogs_dir = current_dir / "cogs"
            
            logger.info("====== Loading Cogs ======")
            logger.info(f"Looking for cogs in: {cogs_dir}")
            
            if not cogs_dir.exists():
                logger.error(f"Cogs directory not found at {cogs_dir}")
                return
                
            # Load all cogs from the cogs directory
            cogs_loaded = 0
            for cog_file in cogs_dir.glob("*.py"):
                if cog_file.stem == "__init__":
                    continue
                    
                try:
                    # Use the correct import path relative to scripts directory
                    cog_path = f"cogs.{cog_file.stem}"
                    logger.info(f"Loading cog: {cog_path}...")
                    await self.load_extension(cog_path)
                    logger.info(f"✓ Successfully loaded: {cog_path}")
                    cogs_loaded += 1
                except Exception as e:
                    logger.error(f"✗ Failed to load {cog_path}: {str(e)}")
                    logger.debug("Error details:", exc_info=True)
            
            logger.info(f"====== Loaded {cogs_loaded} cogs ======\n")
        except Exception as e:
            logger.error(f"Failed to load cogs: {str(e)}")
            logger.debug("Error details:", exc_info=True)

    async def setup_hook(self):
        """Called before the bot starts to set up the bot"""
        await self.load_all_cogs()

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info("====== Bot Ready ======")
        logger.info(f"Logged in as: {self.user}")
        logger.info(f"Bot is ready!")

# Create global bot instance
bot = WhiteoutBot()

def run():
    """Function to start the bot - called by starter.py"""
    try:
        logger.info("====== Starting Bot ======")
        bot.run(bot.token)
    except Exception as e:
        logger.error(f"Error running bot: {str(e)}")
        logger.debug("Error details:", exc_info=True)
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    run()
