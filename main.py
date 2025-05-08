import os
import logging
from telegram.ext import Application
from telegram_interface import setup_handlers

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("telegram_message.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot."""
    logger.info("Starting test bot")
    token = os.getenv("TESTBOT_TOKEN")
    if not token:
        logger.error("TESTBOT_TOKEN environment variable not set")
        return

    try:
        # Build application
        application = Application.builder().token(token).build()
        logger.info("Application built successfully")

        # Setup handlers
        setup_handlers(application)
        logger.info("Handlers setup completed")

        # Initialize application
        await application.initialize()
        logger.info("Application initialized")

        # Start polling
        logger.info("Starting polling")
        await application.run_polling(allowed_updates=["message", "callback_query"])
        logger.info("Polling stopped")

        # Shutdown application
        await application.shutdown()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Failed to start test bot: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    logger.info("Test bot script started")
    import asyncio
    asyncio.run(main())