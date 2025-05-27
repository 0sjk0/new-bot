import os
import sys
import logging
from typing import Optional, List
from pathlib import Path
import interactions
from interactions import Client, Intents, listen
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WhiteoutBot(Client):
    def __init__(self) -> None:
        # Initialize with all intents for maximum functionality
        intents = Intents.ALL
        
        # Load environment variables from config/.env
        env_path = os.path.join("config", ".env")
        if not os.path.exists(env_path):
            logger.error(f"No .env file found in {env_path}")
            sys.exit(1)
            
        load_dotenv(env_path)
        
        # Get bot token from environment
        token = self._get_bot_token()
        if not token:
            logger.error("No bot token found! Please add BOT_TOKEN to your config/.env file.")
            sys.exit(1)
            
        super().__init__(
            token=token,
            intents=intents,
            logger=logger,
            sync_interactions=True,
            auto_defer=True
        )
        
        # Store loaded cogs
        self.loaded_cogs: List[str] = []
        
        # Create necessary directories
        self._create_directories()
        
    def _get_bot_token(self) -> Optional[str]:
        """Get bot token from environment."""
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("BOT_TOKEN not found in config/.env file")
            return None
        return token
        
    def _create_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = ['logs', 'data', 'cogs', 'config']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    async def load_cogs(self) -> None:
        """Load all cogs from the cogs directory."""
        cogs_dir = Path("cogs")
        
        if not cogs_dir.exists():
            logger.warning("Cogs directory not found. Creating...")
            cogs_dir.mkdir(exist_ok=True)
            return
            
        # Load each .py file in the cogs directory
        for cog_file in cogs_dir.glob("*.py"):
            if cog_file.name.startswith("_"):
                continue
                
            cog_name = f"cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                self.loaded_cogs.append(cog_name)
                logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {str(e)}")
                
    async def reload_cogs(self) -> None:
        """Reload all loaded cogs."""
        for cog in self.loaded_cogs[:]:  # Create a copy of the list to iterate
            try:
                await self.reload_extension(cog)
                logger.info(f"Reloaded cog: {cog}")
            except Exception as e:
                logger.error(f"Failed to reload cog {cog}: {str(e)}")
                # Try to load it again if reload fails
                try:
                    await self.load_extension(cog)
                    logger.info(f"Re-loaded cog after reload failure: {cog}")
                except Exception as e2:
                    logger.error(f"Failed to re-load cog {cog} after reload failure: {str(e2)}")
                    self.loaded_cogs.remove(cog)
                    
    @listen()
    async def on_ready(self) -> None:
        """Event fired when the bot is ready."""
        logger.info(f"Logged in as {self.user}")
        
        # Load all cogs
        await self.load_cogs()
        
        logger.info("Bot is ready!")
        
    @listen()
    async def on_error(self, error: Exception) -> None:
        """Global error handler."""
        logger.error(f"An error occurred: {str(error)}", exc_info=error)

# Create global bot instance
bot = WhiteoutBot()

def run():
    """Function to start the bot - called by starter.py"""
    try:
        bot.start()
    except KeyboardInterrupt:
        logger.info("Bot shutdown initiated by user")
    except Exception as e:
        logger.critical(f"Fatal error occurred: {str(e)}", exc_info=e)
    finally:
        logger.info("Bot shutdown complete")

# Only run directly if not imported
if __name__ == "__main__":
    run()
