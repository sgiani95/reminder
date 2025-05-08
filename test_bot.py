import asyncio
import logging
import os
from telegram import Bot
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError
from telegram_interface import validate_group, format_response, send_message, todo_command, confirm_date, cancel_conversation, done_command, list_command, help_command, error_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("test_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot token and chat ID
BOT_TOKEN = os.getenv("TESTBOT_TOKEN")
CHAT_ID = "-1002593119445"  # MammamiaPizzeria chat ID

async def validate_token(bot: Bot) -> bool:
    """Validate the bot token by checking bot info."""
    try:
        bot_info = await bot.get_me()
        logger.info(f"Bot token validated successfully. Bot username: @{bot_info.username}")
        return True
    except TelegramError as e:
        logger.error(f"Invalid bot token: {str(e)}")
        return False

async def start_test_bot():
    """Start the test bot to process commands."""
    logger.info("Starting test bot")
    token = os.getenv("TESTBOT_TOKEN")
    if not token:
        logger.error("TESTBOT_TOKEN environment variable not set")
        return None

    try:
        application = Application.builder().token(token).build()
        logger.info("Test bot application built successfully")

        # Setup handlers (reusing telegram_interface handlers)
        todo_handler = ConversationHandler(
            entry_points=[CommandHandler("todo", todo_command)],
            states={0: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_date)]},
            fallbacks=[CommandHandler("cancel", cancel_conversation)],
            per_user=True,
            per_chat=True,
            conversation_timeout=300
        )
        application.add_handler(todo_handler)
        application.add_handler(CommandHandler("done", done_command))
        application.add_handler(CommandHandler("list", list_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_error_handler(error_handler)
        logger.info("Test bot handlers setup completed")

        await application.initialize()
        logger.info("Test bot application initialized")
        return application
    except Exception as e:
        logger.error(f"Failed to start test bot: {str(e)}", exc_info=True)
        return None

async def send_command(bot: Bot, command: str) -> str:
    """Send a command to the bot."""
    try:
        logger.info(f"Sending command: {command}")
        message = await bot.send_message(chat_id=CHAT_ID, text=command)
        logger.info(f"Command sent successfully: {command} (Message ID: {message.message_id})")
        return "Command sent successfully"
    except TelegramError as e:
        logger.error(f"Error sending command {command}: {str(e)}")
        return f"Error: {str(e)}"

async def run_tests():
    """Run unit tests by starting the test bot and sending commands."""
    if not BOT_TOKEN:
        logger.error("TESTBOT_TOKEN environment variable not set")
        return

    # Start test bot
    application = await start_test_bot()
    if not application:
        logger.error("Test suite aborted due to test bot startup failure")
        return

    # Create bot instance for sending commands
    bot = Bot(token=BOT_TOKEN)
    
    # Validate token
    if not await validate_token(bot):
        logger.error("Test suite aborted due to invalid token")
        await application.shutdown()
        return
    
    test_cases = [
        ("/list", "Should list events or show 'No active events'"),
        ("/todo Fix bike", "Should add to-do: Fix bike"),
        ("/done Fix bike", "Should mark Fix bike as completed"),
        ("/todo Pizza 01-25 19:00", "Should ask for confirmation"),
        ("y", "Should confirm Pizza event"),
        ("/todo Pizza night 2025-07-25 19:00", "Should add event directly"),
        ("/help", "Should show help message"),
        ("/cancel", "Should cancel any pending operation")
    ]
    
    logger.info("Starting tests. Check MammamiaPizzeria chat and test_bot.log for bot responses.")
    
    # Start polling in the background
    polling_task = asyncio.create_task(application.run_polling(allowed_updates=["message", "callback_query"]))
    
    # Send test commands
    for command, description in test_cases:
        logger.info(f"Running test: {description}")
        result = await send_command(bot, command)
        logger.info(f"Test result: {result}")
        logger.info(
            f"Verify response in MammamiaPizzeria chat and "
            f"~/repos/reminder/test_bot.log\n"
        )
        await asyncio.sleep(2)  # Delay to ensure bot processes commands

    # Stop polling and shutdown
    await application.stop()
    await application.shutdown()
    polling_task.cancel()
    logger.info("Test bot shutdown completed")

async def main():
    """Main function to run the tests."""
    try:
        await run_tests()
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())