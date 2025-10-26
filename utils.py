from typing import Optional
import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import GROUP_CHAT_ID

logger = logging.getLogger(__name__)

async def validate_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure commands are from the allowed group."""
    chat_id = str(update.effective_chat.id) if update.effective_chat else None
    if chat_id != GROUP_CHAT_ID:
        if update.effective_message:
            await update.effective_message.reply_text("🚫 This bot only works in the MammamiaPizzeria group!")
        logger.warning(f"Unauthorized access attempt from chat {chat_id}")
        return False
    return True

async def format_response(message: str, add_credit: bool = True) -> str:
    """Format response with emojis and optional bot credit."""
    formatted = f"{message}\n"
    if add_credit:
        formatted += "\n🍕 Powered by @PytstsyToDobot"
    return formatted

async def send_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE, message: str, add_credit: bool = True
) -> None:
    """Send formatted message to the group."""
    if not update.effective_message:
        return
    try:
        await update.effective_message.reply_text(await format_response(message, add_credit))
    except Exception as e:
        logger.error(f"Failed to send message: {e}")