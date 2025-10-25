from typing import NoReturn
import logging
from datetime import time  # Added for JobQueue run_daily
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from config import config
from handlers import (
    todo_command,
    confirm_date,
    cancel_conversation,
    done_command,
    list_command,
    help_command,
    error_handler,
    send_reminders,
    CONFIRMATION,
)
from utils import validate_group  # For any direct use, if needed

# Logging setup (global for the module)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def setup_handlers(application: Application) -> None:
    """Set up bot handlers and job queue."""
    todo_handler = ConversationHandler(
        entry_points=[CommandHandler("todo", todo_command)],
        states={CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_date)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        conversation_timeout=300,  # 5 minutes
    )
    
    application.add_handler(todo_handler)
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    application.add_error_handler(error_handler)
    
    # Daily reminders at 8 AM
    application.job_queue.run_daily(send_reminders, time=time(hour=8, minute=0), name="daily_reminders")
    logger.info("Handlers and job queue set up")