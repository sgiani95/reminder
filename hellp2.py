import asyncio
from telegram import Bot
import logging
import os

# Setup logging
logging.basicConfig(filename='telegram_message.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

#async def send_test_message(bot_token, chat_id, message="Test message from @PytstsyToDobot! 🍕"):
async def send_test_message(bot_token, chat_id, message="/list"):

    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=chat_id, text=message)
        logging.info(f"Message sent to chat ID {chat_id}: {message}")
        print(f"Message sent successfully to chat ID {chat_id}!")
    except Exception as e:
        logging.error(f"Failed to send message to chat ID {chat_id}: {str(e)}")
        print(f"Error for chat ID {chat_id}: {str(e)}")

if __name__ == "__main__":
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")  # Load token from environment variable
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set")
    GROUP_CHAT_ID = "-1002593119445"  # MammamiaPizzeria chat ID
    USER_CHAT_ID = "1502264833"  # Replace with your user ID (e.g., 123456789)

    # Run async function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(send_test_message(BOT_TOKEN, GROUP_CHAT_ID))
    # Uncomment to test private chat
    # loop.run_until_complete(send_test_message(BOT_TOKEN, USER_CHAT_ID, "Private test from @PytstsyToDobot! 🍕"))
