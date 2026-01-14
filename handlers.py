from typing import Optional
import logging
import re
from datetime import datetime, time as dt_time, timedelta  # Renamed 'time' to 'dt_time' to avoid shadowing
import time  # For sleep in retries
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    Application,
)
from input_validation import parse_datetime, get_error_message, check_message_format, validate_todo
from utils import validate_group, send_message
from event_manager import EventManager
from config import GROUP_CHAT_ID, config
import requests  # Add to top imports if missing (pre-installed on Pi)
import random  # For picking a fact
from html import unescape  # For decoding entities like &#91;

# Global manager instance
EVENT_MANAGER = EventManager(config["EVENTS_FILE"])

logger = logging.getLogger(__name__)

# Conversation states
CONFIRMATION = 0

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[int]:
    """Handle /todo command."""
    if not await validate_group(update, context):
        return None

    if not context.args:
        await send_message(update, context, "Usage: /todo <message> [DD.MM.YYYY HH:MM|DD.MM HH:MM|DD.MM.YYYY] (use two digits for day and month)")
        return None

    input_text = " ".join(context.args).strip()
    time_match = re.search(r"(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}|\d{2}\.\d{2} \d{2}:\d{2}|\d{2}\.\d{2}\.\d{4})$", input_text)
    
    if time_match:
        time_input = time_match.group(1)
        message = input_text[: time_match.start()].strip()
        event_type = "terminated"
    else:
        message = input_text
        time_input = "todo"
        event_type = "todo"

    # Validate
    if not check_message_format(message):
        await send_message(update, context, get_error_message("empty"))
        return None
    if event_type == "todo" and not validate_todo(message, EVENT_MANAGER._events):
        await send_message(update, context, get_error_message("duplicate_todo"))
        return None
    if event_type == "terminated":
        dt, _, _ = parse_datetime(time_input)
        if not dt:
            await send_message(update, context, get_error_message("invalid_time"))
            return None

    # Create event
    event_id = len(EVENT_MANAGER._events) + 1
    event = {
        "id": event_id,
        "message": message,
        "time": time_input,
        "type": event_type,
        "active": True,
        "chat_id": GROUP_CHAT_ID,
    }

    if event_type == "terminated":
        dt, formatted_time, is_inferred = parse_datetime(time_input)
        event["time"] = formatted_time
        if is_inferred:
            # Pending confirmation
            context.user_data["pending_event"] = event
            await send_message(update, context, f"Interpreted as {formatted_time} [Y/n]")
            return CONFIRMATION

    # Add directly
    if EVENT_MANAGER.add_event(event):
        await send_message(update, context, f"Added {event_type}: {message} ({event['time']})")
    else:
        await send_message(update, context, "Failed to add event")
    return None

async def confirm_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date confirmation/correction."""
    if not await validate_group(update, context):
        return ConversationHandler.END

    if not update.effective_message:
        return ConversationHandler.END

    response = update.effective_message.text.lower().strip()
    pending_event = context.user_data.get("pending_event")

    if not pending_event:
        await send_message(update, context, "No pending event to confirm")
        return ConversationHandler.END

    if response == "y":
        if EVENT_MANAGER.add_event(pending_event):
            await send_message(update, context, f"Added {pending_event['type']}: {pending_event['message']} ({pending_event['time']})")
        else:
            await send_message(update, context, "Failed to add event")
    elif response == "n":
        await send_message(update, context, "Event canceled")
    else:
        # Try as correction
        dt, formatted_time, _ = parse_datetime(response)
        if dt:
            pending_event["time"] = formatted_time
            if EVENT_MANAGER.add_event(pending_event):
                await send_message(update, context, f"Added {pending_event['type']}: {pending_event['message']} ({formatted_time})")
            else:
                await send_message(update, context, "Failed to add corrected event")
        else:
            await send_message(update, context, "Invalid correction. Use DD.MM.YYYY HH:MM, DD.MM HH:MM, or DD.MM.YYYY (two digits for day and month)")
            return CONFIRMATION

    context.user_data.clear()
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation."""
    await send_message(update, context, "Operation canceled")
    context.user_data.clear()
    return ConversationHandler.END

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /done command."""
    if not await validate_group(update, context):
        return

    if not context.args:
        await send_message(update, context, "Usage: /done <message>")
        return

    message = " ".join(context.args).strip()
    if EVENT_MANAGER.delete_event_by_message(message):
        await send_message(update, context, f"To-do completed and removed: {message}")
    else:
        await send_message(update, context, f"No active to-do found: {message}")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /list command with categorized output."""
    if not await validate_group(update, context):
        return

    show_upcoming_only = context.args and context.args[0].lower() == "upcoming"

    current_time = datetime.now()
    threshold = current_time + timedelta(hours=24)

    # Get all active items
    all_active = [e for e in EVENT_MANAGER._events if e.get("active")]
    todos = [e for e in all_active if e["type"] == "todo"]
    all_terminated = [e for e in all_active if e["type"] == "terminated"]

    # Sort todos by ID
    todos.sort(key=lambda e: e["id"])

    # Sort all terminated by datetime
    def get_event_dt(event):
        dt, _, _ = parse_datetime(event["time"])
        return dt if dt else datetime.max
    all_terminated.sort(key=get_event_dt)

    if show_upcoming_only:
        # Legacy: To-dos + upcoming events only
        upcoming_events = [e for e in all_terminated if current_time <= get_event_dt(e) <= threshold]
        filtered_events = todos + upcoming_events
        if not filtered_events:
            await send_message(update, context, "No upcoming events within 24 hours.")
            return
        header = "Upcoming Events and To-Dos (next 24 hours):\n"
        response = header
        for event in filtered_events:
            event_type = "To-Do" if event["type"] == "todo" else "Event"
            response += f"- {event_type}: {event['message']} ({event['time']})\n"
        await send_message(update, context, response)
        return

    # Default: Categorized view
    upcoming_events = [e for e in all_terminated if current_time <= get_event_dt(e) <= threshold]
    future_events = [e for e in all_terminated if get_event_dt(e) > threshold]

    # Build response sections
    response_parts = []

    # To-Dos section
    if todos:
        response_parts.append("**To-Dos:**")
        for todo in todos:
            response_parts.append(f"\n- {todo['message']}")
    else:
        response_parts.append("**To-Dos:** None")

    response_parts.append("\n- - - - - - - - - - - - - - - -")

    # Upcoming Events section
    if upcoming_events:
        response_parts.append("\n**Upcoming Events (next 24 hours):**")
        for event in upcoming_events:
            response_parts.append(f"\n- {event['message']} ({event['time']})")
    else:
        response_parts.append("\n**Upcoming Events (next 24 hours):** None")

    response_parts.append("\n- - - - - - - - - - - - - - - -")

    # Future Events section
    if future_events:
        response_parts.append("\n**Future Events:**")
        for event in future_events:
            response_parts.append(f"\n- {event['message']} ({event['time']})")
    else:
        response_parts.append("\n**Future Events:** None")

    # Combine and send (strip trailing newline)
    full_response = "".join(response_parts).strip()
    if not any([todos, upcoming_events, future_events]):
        full_response = "No active events or to-dos."

    await send_message(update, context, full_response)

FALLBACK_FACTS = [
    "Wusstet ihr? Die erste Pizza Margherita wurde 1889 in Neapel erfunden – genau wie unser Bot, nur mit mehr Käse!",
    "Fun Fact: 'Pizza' kommt vom Lateinischen 'pinsa' (flach drücken). Passt perfekt zu unserem Teig!",
    "Historisch: Am 28. November 1582 führte Papst Gregor XIII. den gregorianischen Kalender ein – Zeit für Termine!",
    "Italien-Tipp: 'Buon appetito!' heißt 'Guten Appetit' – probiert es beim nächsten Bissen.",
    "Pizza-Legende: Die Tomate kam 1540 aus Amerika nach Italien – danke, Entdecker, für unsere Sauce!"
]

async def send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily reminders for upcoming events—or a Wikiquote 'Zitat der Woche' if none."""
    upcoming = EVENT_MANAGER.get_upcoming_for_reminders()
    
    if upcoming:
        # Existing: Send reminders
        for event in upcoming:
            reminder_msg = f"Reminder: {event['message']} is scheduled for {event['time']}!"
            try:
                await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=reminder_msg)
                logger.info(f"Sent reminder for: {event['message']}")
            except Exception as e:
                logger.error(f"Failed to send reminder for {event['message']}: {e}")
    else:
        # Updated: Fetch Zitat der Woche with retry
        quote_text = None
        api_url = "https://de.wikiquote.org/wiki/Wikiquote:Hauptseite"
        headers = {'User-Agent': 'PytstsyToDoBot/1.0 (https://github.com/sgiani95/reminder; samuele@yourdomain.ch)'}
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Fetching quote attempt {attempt + 1}/{max_retries} from {api_url}")
                response = requests.get(api_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    html = response.text
                    # Refined regex: Capture from "Zitat der Woche" until edit link (handles table | prefix)
                    match = re.search(
                        r'Zitat der Woche.*?\|?\s*(.+?)(?=$$   \[bearbeiten   $$\]|$$   \s*\[bearbeiten \$\$\$\$ |\|Zitat der|<h2>|<div class="mw-parser-output">|Neue Seiten)',
                        html,
                        re.DOTALL | re.IGNORECASE
                    )
                    if match:
                        quote_html = match.group(1)
                        # Decode HTML entities (e.g., &#160; → space, &#91; → [)
                        quote_html = unescape(quote_html)
                        # Flatten wiki links: [Text](url) → Text
                        quote_text = re.sub(r'\[([^ $$]+)\]\([^)]+  \]', r'\1', quote_html)
                        # Strip remaining tags, brackets, and wiki markup
                        quote_text = re.sub(r'<.*?>|$$   \[.*?   $$\]|$$   .*?   $$|\{.*?\}', '', quote_text).strip()
                        # Normalize whitespace and fix common splits (e.g., "D er" → "Der")
                        quote_text = re.sub(r'\s+', ' ', quote_text)
                        quote_text = re.sub(r'D er\b', 'Der', quote_text)  # Quick fix for line-break artifacts
                        # Trim after final citation period (stops at "S. 184")
                        if '.' in quote_text:
                            quote_text = quote_text[:quote_text.rfind('.') + 1].strip()
                        if quote_text and len(quote_text) > 20:  # Sanity check
                            logger.info(f"Quote fetched successfully: {quote_text[:50]}...")
                            break
                    else:
                        raise ValueError("No quote section found in HTML")
                else:
                    logger.warning(f"API status {response.status_code}: {response.text[:100]}...")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
            except Exception as e:
                logger.warning(f"Quote fetch attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logger.error(f"All retries failed for {api_url}")
        
        if quote_text:
            # Truncate if long
            if len(quote_text) > 400:
                quote_text = quote_text[:400] + "..."
            placeholder_msg = (
                f"Guten Morgen! Keine Termine heute – Zitat der Woche:\n\n"
                f"{quote_text}\n\n"
                f"Was denkt ihr darüber? 💭"
            )
        else:
            # Fallback: Random static fact
            fallback = random.choice(FALLBACK_FACTS)
            placeholder_msg = (
                f"Guten Morgen! Keine Termine heute – hier ein kleiner Fun Fact als Plan B:\n\n"
                f"{fallback}\n\n"
                f"Zeit für Kreativität in der Küche!"
            )
            logger.info("Using fallback fact due to scrape failure")
        
        try:
            await context.bot.send_message(chat_id=GROUP_CHAT_ID, text=placeholder_msg)
            logger.info("Sent daily quote/fact (no events)")
        except Exception as e:
            logger.error(f"Failed to send daily quote/fact: {e}")
            
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not await validate_group(update, context):
        return

    response = (
        "@PytstsyToDobot Help\n\n"
        "/todo <message> [DD.MM.YYYY HH:MM|DD.MM HH:MM|DD.MM.YYYY] - Add an event or to-do (use two digits for day and month)\n"
        "/done <message> - Mark a to-do as completed and remove it\n"
        "/list [upcoming|all] - List all active events and to-dos, or only upcoming events (next 24 hours)\n"
        "/help - Show this help\n\n"
        "Bot sends daily reminders at 8 AM. For group '{GROUP_CHAT_ID}' only."
    ).format(GROUP_CHAT_ID=GROUP_CHAT_ID)
    await send_message(update, context, response)