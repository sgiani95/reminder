from datetime import datetime
import re

def check_message_format(message: str) -> bool:
    """Check if the message is not empty and meets basic format requirements."""
    if not message or message.strip() == "":
        return False
    return True

def validate_todo(message: str, events: list) -> bool:
    """Check if a to-do is not a duplicate."""
    for event in events:
        if event["message"] == message and event["type"] == "todo" and event["active"]:
            return False
    return True

def parse_datetime(time_str: str):
    """Parse datetime string and infer year if not provided."""
    formats = [
        "%Y-%m-%d %H:%M",
        "%m-%d %H:%M"
    ]
    is_inferred = False
    dt = None
    formatted_time = time_str

    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            if fmt == "%m-%d %H:%M":
                # Infer year: use next year if date has passed
                current_year = datetime.now().year
                dt = dt.replace(year=current_year)
                if dt < datetime.now():
                    dt = dt.replace(year=current_year + 1)
                is_inferred = True
                formatted_time = dt.strftime("%Y-%m-%d %H:%M")
            break
        except ValueError:
            continue

    return dt, formatted_time, is_inferred

def get_error_message(error_type: str) -> str:
    """Return appropriate error message based on error type."""
    error_messages = {
        "empty": "❌ Message cannot be empty",
        "duplicate_todo": "❌ This to-do already exists",
        "invalid_time": "❌ Invalid time format. Use YYYY-MM-DD HH:MM or MM-DD HH:MM"
    }
    return error_messages.get(error_type, "❌ Unknown error")