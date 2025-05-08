import os
import logging
from telegram.ext import Application
from telegram_interface import setup_handlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("telegram_message.log")
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function to start the bot."""
    logger.info("Starting bot")
    token = os.getenv("BOT_TOKEN")
    if not token:
        logger.error("BOT_TOKEN environment variable not set")
        return

    try:
        # Build application
        application = Application.builder().token(token).build()
        logger.info("Application built successfully")

        # Setup handlers
        setup_handlers(application)
        logger.info("Handlers setup completed")

        # Run application
        logger.info("Starting polling")
        application.run_polling(allowed_updates=["message", "callback_query"])
        logger.info("Polling stopped")
    except Exception as e:
        logger.error(f"Failed to start bot: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Bot script started")
    main()