from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, ContextTypes, filters, JobQueue
import re
import json
import os
from datetime import datetime, timedelta, time
from input_validation import parse_datetime, validate_todo, check_message_format, get_error_message

# Conversation states
CONFIRMATION = 0

def load_config(config_file="config.json"):
    """Load configuration from JSON file."""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise ValueError(f"Configuration file {config_file} not found")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON in {config_file}")

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
try:
    config = load_config()
    is_valid, error_message = validate_config(config)
    if not is_valid:
        raise ValueError(error_message)
    GROUP_CHAT_ID = config["GROUP_CHAT_ID"]
    EVENTS_FILE = config["EVENTS_FILE"]
except Exception as e:
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
                        delete_event(event["message"])
                        continue
                filtered_events.append(event)
            # Save filtered events back to file
            save_events(filtered_events)
            return filtered_events
        except Exception:
            return []
    return []

def save_events(events):
    """Save events to JSON file."""
    try:
        with open(EVENTS_FILE, "w") as f:
            json.dump(events, f, indent=4)
        return True
    except Exception:
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
        print(f"Multiple events matched for deletion: {message}. Deleting first match.")
    event = matched_events[0]
    events.remove(event)
    if not save_events(events):
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
        return False
    return True

async def format_response(message: str) -> str:
    """Format response with emojis and mobile-friendly layout."""
    return f"{message}\n🍕 Powered by @PytstsyToDobot"

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send a message to the group."""
    if not update.effective_message:
        return
    formatted_message = await format_response(message)
    try:
        await update.effective_message.reply_text(formatted_message)
    except Exception:
        pass

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todo <message> [DD.MM.YYYY HH:MM|DD.MM HH:MM|DD.MM.YYYY] command."""
    if not await validate_group(update, context):
        return None

    if not context.args:
        await send_message(update, context, "❌ Usage: /todo <message> [DD.MM.YYYY HH:MM|DD.MM HH:MM|DD.MM.YYYY] (use two digits for day and month)")
        return None

    input_text = " ".join(context.args)
    # Check for time or date format (DD.MM.YYYY HH:MM, DD.MM HH:MM, or DD.MM.YYYY)
    time_match = re.search(r"(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}|\d{2}\.\d{2} \d{2}:\d{2}|\d{2}\.\d{2}\.\d{4})$", input_text)
    
    if time_match:
        # Terminated event with time or date
        time_input = time_match.group(1)
        message = input_text[:time_match.start()].strip()
        event_type = "terminated"
    else:
        # To-do (no time specified)
        message = input_text.strip()
        time_input = "todo"
        event_type = "todo"

    # Validate event/to-do
    is_valid, error_message = validate_event(message, time_input, event_type, events)
    if not is_valid:
        await send_message(update, context, error_message)
        return None

    if event_type == "terminated":
        try:
            dt, formatted_time, is_inferred = parse_datetime(time_input)
            if not dt:
                await send_message(update, context, get_error_message("invalid_time"))
                return None
            time_input = formatted_time
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
                return CONFIRMATION
        except Exception:
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
    await send_message(update, context, f"✅ Added {event_type}: {message} ({time_input})")
    return None

async def confirm_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation response for inferred dates."""
    if not await validate_group(update, context):
        return ConversationHandler.END

    if not update.effective_message:
        return ConversationHandler.END

    response = update.effective_message.text.lower()
    pending_event = context.user_data.get("pending_event")

    if not pending_event:
        await send_message(update, context, "❌ No pending event to confirm")
        return ConversationHandler.END

    if response == "y":
        events.append(pending_event)
        save_events(events)
        await send_message(update, context, f"✅ Added {pending_event['type']}: {pending_event['message']} ({pending_event['time']})")
    elif response == "n":
        await send_message(update, context, "❌ Event canceled")
    else:
        # Treat as correction (new time input)
        try:
            dt, formatted_time, _ = parse_datetime(response)
            if not dt:
                await send_message(update, context, f"❌ Invalid correction. Use DD.MM.YYYY HH:MM, DD.MM HH:MM, or DD.MM.YYYY (two digits for day and month)")
                return CONFIRMATION
            pending_event["time"] = formatted_time
            events.append(pending_event)
            save_events(events)
            await send_message(update, context, f"✅ Added {pending_event['type']}: {pending_event['message']} ({formatted_time})")
        except Exception:
            await send_message(update, context, f"❌ Invalid correction. Use DD.MM.YYYY HH:MM, DD.MM HH:MM, or DD.MM.YYYY (two digits for day and month)")
            return CONFIRMATION

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await send_message(update, context, "❌ Operation canceled")
    context.user_data.clear()
    return ConversationHandler.END

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done <message> command to remove to-do from events."""
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

    # Split events into todo and terminated
    todo_events = [event for event in events if event["type"] == "todo" and event["active"]]
    terminated_events = [event for event in events if event["type"] == "terminated" and event["active"]]

    # Sort todo events by id
    todo_events = sorted(todo_events, key=lambda x: x["id"])

    # Sort terminated events by datetime
    def get_event_datetime(event):
        dt, _, _ = parse_datetime(event["time"])
        return dt if dt else datetime.max  # Use max for invalid dates to sort them last
    terminated_events = sorted(terminated_events, key=get_event_datetime)

    if show_upcoming:
        reminder_threshold = current_time + timedelta(hours=24)
        terminated_events = [
            event for event in terminated_events
            if parse_datetime(event["time"])[0] and
               current_time <= parse_datetime(event["time"])[0] <= reminder_threshold
        ]
        filtered_events = todo_events + terminated_events
    else:
        filtered_events = todo_events + terminated_events

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
    global events
    current_time = datetime.now()
    reminder_threshold = current_time + timedelta(hours=24)
    
    upcoming_events = []
    for event in events:
        if event["type"] == "terminated" and event["active"]:
            dt, formatted_time, _ = parse_datetime(event["time"])
            if dt and current_time <= dt <= reminder_threshold:
                upcoming_events.append(event)

    if not upcoming_events:
        return

    for event in upcoming_events:
        message = f"🔔 Reminder: {event['message']} is scheduled for {event['time']}!"
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
        except Exception:
            pass

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command to show usage instructions."""
    if not await validate_group(update, context):
        return

    response = (
        "📖 @PytstsyToDobot Help\n\n"
        "/todo <message> [DD.MM.YYYY HH:MM|DD.MM HH:MM|DD.MM.YYYY] - Add an event or to-do (use two digits for day and month)\n"
        "/done <message> - Mark a to-do as completed and remove it\n"
        "/list [upcoming|all] - List all active events and to-dos, or only upcoming events (next 24 hours)\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "Examples:\n"
        "- /todo Pizza night 25.07.2025 19:00\n"
        "- /todo Pizza night 25.07 19:00\n"
        "- /todo Pizza123 25.12.2025\n"
        "- /todo Fix bike\n"
        "- /done Fix bike\n"
        "- /list\n"
        "- /list upcoming\n"
        "- /list all"
    )
    await send_message(update, context, response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    pass

def setup_handlers(application: Application):
    """Initialize bot and register command handlers."""
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
    application.add_handler(CommandHandler("cancel", cancel_conversation))
    application.add_error_handler(error_handler)
    
    # Schedule daily reminder checks at 8 AM
    job_queue = application.job_queue
    job_queue.run_daily(send_reminders, time=time(hour=8, minute=0), name="daily_reminders")