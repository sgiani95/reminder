from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, ContextTypes, filters, JobQueue
import logging
import re
import json
import os
from datetime import datetime, timedelta, time
from logging.handlers import TimedRotatingFileHandler
from input_validation import parse_datetime, validate_todo, check_message_format, get_error_message

# Conversation states
CONFIRMATION = 0

# Configure logging with daily rotation
def setup_logging(log_file):
    """Set up logging with daily rotation."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,  # Rotate every day
                backupCount=14  # Keep 14 days of logs
            )
        ]
    )
    return logging.getLogger(__name__)

def load_config(config_file="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        logger.error(f"Configuration file {config_file} not found")
        raise
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in {config_file}")
        raise

def validate_config(config):
    """Validate configuration dictionary."""
    required_fields = ["GROUP_CHAT_ID", "EVENTS_FILE", "LOG_FILE"]
    for field in required_fields:
        if field not in config:
            return False, f"Missing required field: {field}"
        if not isinstance(config[field], str) or not config[field]:
            return False, f"Invalid {field}: must be a non-empty string"
    if not config["GROUP_CHAT_ID"].startswith("-100"):
        return False, "Invalid GROUP_CHAT_ID: must start with '-100'"
    return True, ""

# Load and validate configuration
logger = setup_logging("telegram_message.log")  # Temporary logger for config errors
try:
    config = load_config()
    is_valid, error_message = validate_config(config)
    if not is_valid:
        logger.error(f"Configuration error: {error_message}")
        raise ValueError(error_message)
    GROUP_CHAT_ID = config["GROUP_CHAT_ID"]
    EVENTS_FILE = config["EVENTS_FILE"]
    logger = setup_logging(config["LOG_FILE"])  # Reconfigure logger with config file
except Exception as e:
    logger.error(f"Failed to initialize bot: {str(e)}")
    raise

# Event storage file
def load_events():
    """Load events from JSON file and filter out expired events."""
    if os.path.exists(EVENTS_FILE):
        try:
            with open(EVENTS_FILE, "r") as f:
                loaded_events = json.load(f)
            # Filter out expired terminated events
            current_time = datetime.now()
            filtered_events = []
            for event in loaded_events:
                if event["type"] == "terminated" and event["active"]:
                    dt, _, _ = parse_datetime(event["time"])
                    if dt and dt < current_time:
                        logger.info(f"Removing expired event: {event['message']} ({event['time']})")
                        delete_event(event["message"])  # Use delete_event for consistency
                        continue
                filtered_events.append(event)
            # Save filtered events back to file
            save_events(filtered_events)
            return filtered_events
        except Exception as e:
            logger.error(f"Failed to load events: {str(e)}")
            return []
    return []

def save_events(events):
    """Save events to JSON file."""
    try:
        with open(EVENTS_FILE, "w") as f:
            json.dump(events, f, indent=4)
        logger.info("Events saved to JSON")
        return True
    except Exception as e:
        logger.error(f"Failed to save events: {str(e)}")
        return False

def delete_event(message):
    """Delete an event or to-do by message (case-insensitive)."""
    global events
    matched_events = [
        event for event in events
        if event["message"].lower() == message.lower() and event["active"]
    ]
    if not matched_events:
        return False
    if len(matched_events) > 1:
        logger.warning(f"Multiple events matched for deletion: {message}. Deleting first match.")
    event = matched_events[0]
    events.remove(event)
    logger.info(f"Deleted {event['type']}: {event['message']}")
    if not save_events(events):
        logger.error(f"Failed to save events after deleting: {event['message']}")
        return False
    return True

def validate_event(message, time_input, event_type, events):
    """Validate an event or to-do before creation."""
    if not check_message_format(message):
        return False, get_error_message("empty")
    if event_type == "todo":
        if not validate_todo(message, events):
            return False, get_error_message("duplicate_todo")
    elif event_type == "terminated":
        dt, _, _ = parse_datetime(time_input)
        if not dt:
            return False, get_error_message("invalid_time")
    return True, ""

# Initialize events
events = load_events()

async def validate_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure commands are sent from MammamiaPizzeria group."""
    if not update.effective_chat or str(update.effective_chat.id) != GROUP_CHAT_ID:
        if update.effective_message:
            await update.effective_message.reply_text("🚫 This bot only works in the MammamiaPizzeria group!")
        logger.warning(f"Unauthorized access attempt from chat ID {update.effective_chat.id if update.effective_chat else 'None'}")
        return False
    return True

async def format_response(message: str) -> str:
    """Format response with emojis and mobile-friendly layout."""
    return f"{message}\n🍕 Powered by @PytstsyToDobot"

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send a message to the group."""
    if not update.effective_message:
        logger.error("No effective message available to reply")
        return
    formatted_message = await format_response(message)
    try:
        await update.effective_message.reply_text(formatted_message)
        logger.info(f"Sent message to {GROUP_CHAT_ID}: {message}")
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM] command."""
    logger.info("Entering todo_command")
    if not await validate_group(update, context):
        return None

    if not context.args:
        await send_message(update, context, "❌ Usage: /todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM]")
        return None

    input_text = " ".join(context.args)
    logger.info(f"Processing /todo: {input_text}")

    # Check for time format (YYYY-MM-DD HH:MM or MM-DD HH:MM)
    time_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}|\d{1,2}-\d{1,2} \d{2}:\d{2})$", input_text)
    
    if time_match:
        # Terminated event with time
        time_input = time_match.group(1)
        message = input_text[:time_match.start()].strip()
        logger.info(f"Time matched: {time_input}, Message: {message}")
        event_type = "terminated"
    else:
        # To-do (no time specified)
        message = input_text.strip()
        time_input = "todo"
        logger.info(f"No time matched, treating as to-do: {message}")
        event_type = "todo"

    # Validate event/to-do
    is_valid, error_message = validate_event(message, time_input, event_type, events)
    if not is_valid:
        await send_message(update, context, error_message)
        return None

    if event_type == "terminated":
        try:
            logger.info(f"Calling parse_datetime with: {time_input}")
            dt, formatted_time, is_inferred = parse_datetime(time_input)
            if not dt:
                await send_message(update, context, get_error_message("invalid_time"))
                return None
            time_input = formatted_time
            logger.info(f"Parsed time: {time_input}, Inferred: {is_inferred}")
            if is_inferred:
                # Store pending event and ask for confirmation
                context.user_data["pending_event"] = {
                    "id": len(events) + 1,
                    "message": message,
                    "time": time_input,
                    "type": event_type,
                    "active": True,
                    "chat_id": GROUP_CHAT_ID
                }
                await send_message(update, context, f"Interpreted as {time_input} [Y/n]")
                logger.info(f"Entered CONFIRMATION state for {time_input}")
                return CONFIRMATION
        except Exception as e:
            logger.error(f"Error parsing datetime in /todo: {str(e)}")
            await send_message(update, context, get_error_message("invalid_time"))
            return None

    # Create event directly for to-dos or non-inferred dates
    event = {
        "id": len(events) + 1,
        "message": message,
        "time": time_input,
        "type": event_type,
        "active": True,
        "chat_id": GROUP_CHAT_ID
    }
    events.append(event)
    save_events(events)
    logger.info(f"Added event: {event}")
    await send_message(update, context, f"✅ Added {event_type}: {message} ({time_input})")
    return None

async def confirm_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation response for inferred dates."""
    logger.info("Entering confirm_date")
    if not await validate_group(update, context):
        return ConversationHandler.END

    if not update.effective_message:
        logger.error("No effective message available in confirm_date")
        return ConversationHandler.END

    response = update.effective_message.text.lower()
    pending_event = context.user_data.get("pending_event")

    if not pending_event:
        await send_message(update, context, "❌ No pending event to confirm")
        return ConversationHandler.END

    if response == "y":
        events.append(pending_event)
        save_events(events)
        logger.info(f"Added confirmed event: {pending_event}")
        await send_message(update, context, f"✅ Added {pending_event['type']}: {pending_event['message']} ({pending_event['time']})")
    elif response == "n":
        await send_message(update, context, "❌ Event canceled")
    else:
        # Treat as correction (new time input)
        try:
            dt, formatted_time, _ = parse_datetime(response)
            if not dt:
                await send_message(update, context, f"❌ Invalid correction. Use YYYY-MM-DD HH:MM or MM-DD HH:MM")
                return CONFIRMATION
            pending_event["time"] = formatted_time
            events.append(pending_event)
            save_events(events)
            logger.info(f"Added corrected event: {pending_event}")
            await send_message(update, context, f"✅ Added {pending_event['type']}: {pending_event['message']} ({formatted_time})")
        except Exception as e:
            logger.error(f"Error parsing correction in confirm_date: {str(e)}")
            await send_message(update, context, f"❌ Invalid correction. Use YYYY-MM-DD HH:MM or MM-DD HH:MM")
            return CONFIRMATION

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    logger.info("Entering cancel_conversation")
    await send_message(update, context, "❌ Operation canceled")
    context.user_data.clear()
    return ConversationHandler.END

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done <message> command to remove to-do from events."""
    logger.info("Entering done_command")
    if not await validate_group(update, context):
        return

    if not context.args:
        await send_message(update, context, "❌ Usage: /done <message>")
        return

    message = " ".join(context.args)
    if delete_event(message):
        await send_message(update, context, f"✅ To-do completed and removed: {message}")
    else:
        await send_message(update, context, f"❌ No active to-do found: {message}")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list [upcoming|all] command to show active events and to-dos."""
    logger.info("Entering list_command")
    if not await validate_group(update, context):
        return

    # Filter out expired events
    global events
    current_time = datetime.now()
    events = [
        event for event in events
        if not (
            event["type"] == "terminated" and
            event["active"] and
            parse_datetime(event["time"])[0] and
            parse_datetime(event["time"])[0] < current_time
        )
    ]
    save_events(events)

    # Check for 'upcoming' or 'all' argument
    show_upcoming = context.args and context.args[0].lower() == "upcoming"
    show_all = context.args and context.args[0].lower() == "all"

    if show_upcoming:
        reminder_threshold = current_time + timedelta(hours=24)
        filtered_events = [
            event for event in events
            if event["type"] == "terminated" and
               event["active"] and
               parse_datetime(event["time"])[0] and
               current_time <= parse_datetime(event["time"])[0] <= reminder_threshold
        ]
    else:
        filtered_events = [event for event in events if event["active"]]

    if not filtered_events:
        await send_message(update, context, "ℹ️ No active events or to-dos." if not show_upcoming else "ℹ️ No upcoming events within 24 hours.")
        return

    response = "📋 Active Events and To-Dos:\n" if not show_upcoming else "🔔 Upcoming Events (next 24 hours):\n"
    for event in filtered_events:
        event_type = "To-Do" if event["type"] == "todo" else "Event"
        response += f"- {event_type}: {event['message']} ({event['time']})\n"
    await send_message(update, context, response)

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    """Check for upcoming events and send reminders."""
    logger.info("Checking for upcoming events")
    global events
    current_time = datetime.now()
    reminder_threshold = current_time + timedelta(hours=24)
    
    upcoming_events = []
    for event in events:
        if event["type"] == "terminated" and event["active"]:
            dt, _, _ = parse_datetime(event["time"])
            if dt and current_time <= dt <= reminder_threshold:
                upcoming_events.append(event)

    if not upcoming_events:
        logger.info("No upcoming events within 24 hours")
        return

    for event in upcoming_events:
        message = f"🔔 Reminder: {event['message']} is scheduled for {event['time']}!"
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
            logger.info(f"Sent reminder for event: {event['message']} ({event['time']})")
        except Exception as e:
            logger.error(f"Failed to send reminder for {event['message']}: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command to show usage instructions."""
    logger.info("Entering help_command")
    if not await validate_group(update, context):
        return

    response = (
        "📖 @PytstsyToDobot Help\n\n"
        "/todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM] - Add an event or to-do\n"
        "/done <message> - Mark a to-do as completed and remove it\n"
        "/list [upcoming|all] - List all active events and to-dos, or only upcoming events (next 24 hours)\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "Examples:\n"
        "- /todo Pizza night 2025-07-25 19:00\n"
        "- /todo Pizza night 08-25 19:00\n"
        "- /todo Fix bike\n"
        "- /done Fix bike\n"
        "- /list\n"
        "- /list upcoming\n"
        "- /list all"
    )
    await send_message(update, context, response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")

def setup_handlers(application: Application):
    """Initialize bot and register command handlers."""
    logger.info("Setting up command handlers")
    todo_handler = ConversationHandler(
        entry_points=[CommandHandler("todo", todo_command)],
        states={CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_date)]},
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
        per_user=True,
        per_chat=True,
        conversation_timeout=300  # 5 minutes timeout
    )
    application.add_handler(todo_handler)
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_error_handler(error_handler)
    
    # Schedule daily reminder checks at 8 AM
    job_queue = application.job_queue
    job_queue.run_daily(send_reminders, time=time(hour=8, minute=0), name="daily_reminders")
    
    logger.info("Command handlers and job queue registered")