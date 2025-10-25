import os
from typing import NoReturn
import logging
from telegram.ext import Application

# Align with telegram_interface.py logging setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

from telegram_interface import setup_handlers

def main() -> NoReturn:
    """
    Main entry point: Build and run the Telegram bot application.
    
    Expects BOT_TOKEN env var to be set.
    """
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable not set")
        raise ValueError("BOT_TOKEN environment variable not set")

    try:
        # Build application
        application = Application.builder().token(token).build()
        
        # Setup handlers
        setup_handlers(application)
        logger.info("Bot handlers set up successfully")
        
        # Run polling
        application.run_polling(
            allowed_updates=["message", "callback_query"]  # List for JSON serialization
        )
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()