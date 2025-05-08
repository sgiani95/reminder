from datetime import datetime, date
import re
from typing import Union, Tuple
import logging

def parse_datetime(time_input: str) -> Tuple[Union[datetime, None], str, bool]:
    """Parse and validate datetime, infer year if missing, return (datetime, formatted_time, is_inferred)."""
    logging.info(f"Parsing datetime: {time_input}")
    # Regex for YYYY-MM-DD HH:MM or MM-DD HH:MM
    time_match = re.match(r"^(\d{4}-\d{2}-\d{2}|\d{1,2}-\d{1,2}) \d{2}:\d{2}$", time_input)
    if not time_match:
        logging.warning(f"Invalid datetime format: {time_input}")
        return None, "", False

    is_inferred = False
    try:
        if len(time_input.split("-")[0]) == 2:  # MM-DD HH:MM
            month, day = map(int, time_input.split(" ")[0].split("-"))
            hour, minute = map(int, time_input.split(" ")[1].split(":"))
            current_year = datetime.now().year
            today = date.today()
            event_date = date(current_year, month, day)
            # Infer year: next year if before today, current year otherwise
            year = current_year + 1 if event_date < today else current_year
            time_input = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}"
            is_inferred = True
        # Parse and validate datetime
        dt = datetime.strptime(time_input, "%Y-%m-%d %H:%M")
        logging.info(f"Parsed datetime: {dt}")
        return dt, time_input, is_inferred
    except ValueError as e:
        logging.error(f"Error parsing datetime: {str(e)}")
        return None, "", False

def validate_todo(message: str, events: list) -> bool:
    """Check if to-do message is unique and valid."""
    if not message or len(message) > 4096:
        return False
    return not any(event["message"] == message and event["type"] == "todo" and event["active"] for event in events)

def check_message_format(message: str) -> bool:
    """Ensure message is non-empty and within Telegram limits."""
    return bool(message) and len(message) <= 4096

def get_error_message(error_type: str) -> str:
    """Generate user-friendly error messages."""
    errors = {
        "empty": "❌ Message cannot be empty",
        "invalid_time": "❌ Invalid time format. Use YYYY-MM-DD HH:MM or MM-DD HH:MM",
        "duplicate_todo": "❌ To-do already exists",
        "invalid_message": "❌ Message too long or invalid"
    }
    return errors.get(error_type, "❌ Unknown error")