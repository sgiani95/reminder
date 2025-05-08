import asyncio
import logging
import os
import subprocess
from telegram import Bot
from telegram.error import TelegramError

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

def check_running_bot() -> bool:
    """Check if main.py bot instance is running."""
    try:
        result = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, check=True
        )
        if "python3 /home/sgiani/repos/reminder/main.py" in result.stdout:
            logger.info(
                "Detected running bot instance (main.py). Ensure it is processing updates.\n"
                "To stop it (optional):\n"
                "  pkill -f 'python3 /home/sgiani/repos/reminder/main.py'\n"
                "To restart it:\n"
                "  /bin/python3 /home/sgiani/repos/reminder/main.py"
            )
            return True
        logger.info("No running bot instance detected. Start main.py to process commands.")
        return False
    except subprocess.SubprocessError as e:
        logger.error(f"Error checking running bot: {str(e)}")
        return False

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
    """Run unit tests by sending commands to the bot."""
    if not BOT_TOKEN:
        logger.error("TESTBOT_TOKEN environment variable not set")
        return

    bot = Bot(token=BOT_TOKEN)
    
    # Validate token
    if not await validate_token(bot):
        logger.error("Test suite aborted due to invalid token")
        return
    
    # Check for running bot instance
    if not check_running_bot():
        logger.warning(
            "No running bot instance (main.py) detected. Start it to process commands:\n"
            "  /bin/python3 /home/sgiani/repos/reminder/main.py"
        )
    
    test_cases = [
        ("/list", "Should list events or show 'No active events'"),
        ("/todo Fix bike", "Should add to-do: Fix bike"),
        ("/done Fix bike", "Should remove to-do: Fix bike"),
        ("/todo Pizza 01-25 19:00", "Should ask for confirmation"),
        ("y", "Should confirm Pizza event"),
        ("/todo Pizza night 2025-07-25 19:00", "Should add event directly"),
        ("/todo Old event 2025-05-01 12:00", "Should add event that will be removed as expired"),
        ("/list", "Should not show expired Old event"),
        ("/help", "Should show help message"),
        ("/cancel", "Should cancel any pending operation")
    ]
    
    logger.info("Starting tests. Check MammamiaPizzeria chat and telegram_message.log for bot responses.")
    for command, description in test_cases:
        logger.info(f"Running test: {description}")
        result = await send_command(bot, command)
        logger.info(f"Test result: {result}")
        logger.info(
            f"Verify response in MammamiaPizzeria chat and "
            f"~/repos/reminder/telegram_message.log\n"
        )
        await asyncio.sleep(2)  # Increased delay to ensure bot processes commands

async def main():
    """Main function to run the tests."""
    try:
        await run_tests()
    except Exception as e:
        logger.error(f"Test suite failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())