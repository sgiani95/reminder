import os
from telegram.ext import Application
from telegram_interface import setup_handlers

def main():
    """Main function to start the bot."""
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN environment variable not set")  # Replace logger.error with print
        return

    try:
        # Build application
        application = Application.builder().token(token).build()
        # Setup handlers
        setup_handlers(application)
        # Run application
        application.run_polling(allowed_updates=["message", "callback_query"])
    except Exception as e:
        print(f"Failed to start bot: {str(e)}")  # Replace logger.error with print
        raise

if __name__ == "__main__":
    main()