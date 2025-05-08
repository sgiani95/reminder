from telegram import Update
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, ContextTypes, filters
import logging
import re
from input_validation import parse_datetime, validate_todo, check_message_format, get_error_message

# In-memory event storage (to be replaced with JSON in Step 3)
events = []

# Group chat ID for MammamiaPizzeria
GROUP_CHAT_ID = "-1002593119445"

# Conversation states
CONFIRMATION = 0

async def validate_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Ensure commands are sent from MammamiaPizzeria group."""
    if not update.effective_chat or str(update.effective_chat.id) != GROUP_CHAT_ID:
        if update.effective_message:
            await update.effective_message.reply_text("🚫 This bot only works in the MammamiaPizzeria group!")
        logging.warning(f"Unauthorized access attempt from chat ID {update.effective_chat.id if update.effective_chat else 'None'}")
        return False
    return True

async def format_response(message: str) -> str:
    """Format response with emojis and mobile-friendly layout."""
    return f"{message}\n🍕 Powered by @PytstsyTestBot"

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE, message: str):
    """Send a message to the group."""
    if not update.effective_message:
        logging.error("No effective message available to reply")
        return
    formatted_message = await format_response(message)
    try:
        await update.effective_message.reply_text(formatted_message)
        logging.info(f"Sent message to {GROUP_CHAT_ID}: {message}")
    except Exception as e:
        logging.error(f"Failed to send message: {str(e)}")

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM] command."""
    logging.info("Entering todo_command")
    if not await validate_group(update, context):
        return None

    if not context.args:
        await send_message(update, context, "❌ Usage: /todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM]")
        return None

    input_text = " ".join(context.args)
    logging.info(f"Processing /todo: {input_text}")

    # Check for time format (YYYY-MM-DD HH:MM or MM-DD HH:MM)
    time_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}|\d{1,2}-\d{1,2} \d{2}:\d{2})$", input_text)
    
    if time_match:
        # Terminated event with time
        time_input = time_match.group(1)
        message = input_text[:time_match.start()].strip()
        logging.info(f"Time matched: {time_input}, Message: {message}")
        if not message:
            await send_message(update, context, get_error_message("empty"))
            return None
        event_type = "terminated"
    else:
        # To-do (no time specified)
        message = input_text.strip()
        time_input = "todo"
        logging.info(f"No time matched, treating as to-do: {message}")
        event_type = "todo"

    if not check_message_format(message):
        await send_message(update, context, get_error_message("empty"))
        return None

    if event_type == "todo" and not validate_todo(message, events):
        await send_message(update, context, get_error_message("duplicate_todo"))
        return None

    if event_type == "terminated":
        try:
            logging.info(f"Calling parse_datetime with: {time_input}")
            dt, formatted_time, is_inferred = parse_datetime(time_input)
            if not dt:
                await send_message(update, context, get_error_message("invalid_time"))
                return None
            time_input = formatted_time
            logging.info(f"Parsed time: {time_input}, Inferred: {is_inferred}")
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
                logging.info(f"Entered CONFIRMATION state for {time_input}")
                return CONFIRMATION
        except Exception as e:
            logging.error(f"Error parsing datetime in /todo: {str(e)}")
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
    logging.info(f"Added event: {event}")
    await send_message(update, context, f"✅ Added {event_type}: {message} ({time_input})")
    return None

async def confirm_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation response for inferred dates."""
    logging.info("Entering confirm_date")
    if not await validate_group(update, context):
        return ConversationHandler.END

    if not update.effective_message:
        logging.error("No effective message available in confirm_date")
        return ConversationHandler.END

    response = update.effective_message.text.lower()
    pending_event = context.user_data.get("pending_event")

    if not pending_event:
        await send_message(update, context, "❌ No pending event to confirm")
        return ConversationHandler.END

    if response == "y":
        events.append(pending_event)
        logging.info(f"Added confirmed event: {pending_event}")
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
            logging.info(f"Added corrected event: {pending_event}")
            await send_message(update, context, f"✅ Added {pending_event['type']}: {pending_event['message']} ({formatted_time})")
        except Exception as e:
            logging.error(f"Error parsing correction in confirm_date: {str(e)}")
            await send_message(update, context, f"❌ Invalid correction. Use YYYY-MM-DD HH:MM or MM-DD HH:MM")
            return CONFIRMATION

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    logging.info("Entering cancel_conversation")
    await send_message(update, context, "❌ Operation canceled")
    context.user_data.clear()
    return ConversationHandler.END

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /done <message> command to mark to-do as completed."""
    logging.info("Entering done_command")
    if not await validate_group(update, context):
        return

    if not context.args:
        await send_message(update, context, "❌ Usage: /done <message>")
        return

    message = " ".join(context.args)
    found = False
    for event in events:
        if event["message"] == message and event["type"] == "todo" and event["active"]:
            event["active"] = False
            found = True
            logging.info(f"Marked to-do as done: {message}")
            break

    if found:
        await send_message(update, context, f"✅ To-do completed: {message}")
    else:
        await send_message(update, context, f"❌ No active to-do found: {message}")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command to show active events and to-dos."""
    logging.info("Entering list_command")
    if not await validate_group(update, context):
        return

    if not events:
        await send_message(update, context, "ℹ️ No active events or to-dos.")
        return

    response = "📋 Active Events and To-Dos:\n"
    for event in events:
        if event["active"]:
            event_type = "To-Do" if event["type"] == "todo" else "Event"
            response += f"- {event_type}: {event['message']} ({event['time']})\n"
    await send_message(update, context, response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command to show usage instructions."""
    logging.info("Entering help_command")
    if not await validate_group(update, context):
        return

    response = (
        "📖 @PytstsyTestBot Help\n\n"
        "/todo <message> [YYYY-MM-DD HH:MM|MM-DD HH:MM] - Add an event or to-do\n"
        "/done <message> - Mark a to-do as completed\n"
        "/list - List all active events and to-dos\n"
        "/help - Show this help message\n"
        "/cancel - Cancel current operation\n\n"
        "Examples:\n"
        "- /todo Pizza night 2025-07-25 19:00\n"
        "- /todo Pizza night 08-25 19:00\n"
        "- /todo Fix bike\n"
        "- /done Fix bike"
    )
    await send_message(update, context, response)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logging.error(f"Update {update} caused error: {context.error}")

def setup_handlers(application: Application):
    """Initialize bot and register command handlers."""
    logging.info("Setting up command handlers")
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
    logging.info("Command handlers registered")