import logging
import os
from telegram.ext import Application
from telegram_interface import setup_handlers

# Setup logging
logging.basicConfig(filename='telegram_message.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Load bot token from environment variable
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logging.error("BOT_TOKEN environment variable not set")
        raise ValueError("BOT_TOKEN environment variable not set")

    # Initialize bot application
    application = Application.builder().token(bot_token).build()

    # Setup command handlers
    setup_handlers(application)

    # Start polling
    logging.info("Starting bot polling")
    application.run_polling()

if __name__ == "__main__":
    main()