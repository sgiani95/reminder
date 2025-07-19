from datetime import datetime
import re

def parse_datetime(time_input):
    """Parse and validate datetime input, returning (datetime, formatted_time, is_inferred)."""
    try:
        # Handle DD.MM HH:MM format (infer year)
        if re.match(r"^\d{2}\.\d{2} \d{2}:\d{2}$", time_input):
            current_year = datetime.now().year
            assumed_time = f"{time_input}.{current_year}"
            try:
                dt = datetime.strptime(assumed_time, "%d.%m.%Y %H:%M")
                if dt.day > 31 or dt.month > 12 or dt.hour > 23 or dt.minute > 59:
                    return None, None, False
            except ValueError:
                # Try next year if date has passed
                dt = datetime.strptime(f"{time_input}.{current_year + 1}", "%d.%m.%Y %H:%M")
                if dt.day > 31 or dt.month > 12 or dt.hour > 23 or dt.minute > 59:
                    return None, None, False
            formatted_time = dt.strftime("%d.%m.%Y %H:%M")
            return dt, formatted_time, True
        # Handle DD.MM.YYYY HH:MM format
        elif re.match(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$", time_input):
            dt = datetime.strptime(time_input, "%d.%m.%Y %H:%M")
            if dt.day > 31 or dt.month > 12 or dt.hour > 23 or dt.minute > 59:
                return None, None, False
            formatted_time = dt.strftime("%d.%m.%Y %H:%M")
            return dt, formatted_time, False
        # Handle DD.MM.YYYY format (date only, assume 00:00)
        elif re.match(r"^\d{2}\.\d{2}\.\d{4}$", time_input):
            dt = datetime.strptime(f"{time_input} 00:00", "%d.%m.%Y %H:%M")
            if dt.day > 31 or dt.month > 12:
                return None, None, False
            formatted_time = dt.strftime("%d.%m.%Y")
            return dt, formatted_time, False
        else:
            return None, None, False
    except ValueError:
        return None, None, False

def validate_todo(message, events):
    """Check if a to-do already exists."""
    for event in events:
        if event["message"] == message and event["type"] == "todo" and event["active"]:
            return False
    return True

def check_message_format(message):
    """Validate message format (not empty, valid characters)."""
    if not message or message.strip() == "":
        return False
    # Add any specific format checks if needed (e.g., max length, allowed chars)
    return True

def get_error_message(error_type):
    """Return formatted error message."""
    errors = {
        "empty": "❌ Empty or invalid message",
        "duplicate_todo": "❌ Duplicate to-do",
        "invalid_time": "❌ Invalid date/time format"
    }
    return errors.get(error_type, "❌ Unknown error")

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