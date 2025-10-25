from datetime import datetime
from typing import Optional, Tuple
import re

# Constants for regex patterns
DATE_TIME_FULL = r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$"
DATE_TIME_INFER = r"^\d{2}\.\d{2} \d{2}:\d{2}$"
DATE_ONLY = r"^\d{2}\.\d{2}\.\d{4}$"

class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass

def parse_datetime(time_input: str) -> Tuple[Optional[datetime], str, bool]:
    """
    Parse and validate datetime input in supported formats.
    Returns (datetime object, formatted string, is_inferred flag).
    
    Supported formats:
    - DD.MM.YYYY HH:MM (full)
    - DD.MM HH:MM (infer year, prefer future)
    - DD.MM.YYYY (date only, assume 00:00)
    
    Examples (on Oct 25, 2025):
    - "25.10.2025 18:00" → datetime(2025,10,25,18,0), "25.10.2025 18:00", False
    - "26.10 18:00" → datetime(2025,10,26,18,0), "26.10.2025 18:00", True
    - "01.10 18:00" → datetime(2026,10,1,18,0), "01.10.2026 18:00", True (since 2025-10-01 is past)
    - "25.12.2025" → datetime(2025,12,25,0,0), "25.12.2025", False
    """
    time_input = time_input.strip()
    if not time_input:
        return None, "", False

    now = datetime.now()
    is_inferred = False

    try:
        if re.match(DATE_TIME_INFER, time_input):
            # Split into date_part (DD.MM) and time_part (HH:MM)
            parts = time_input.split()
            if len(parts) != 2:
                return None, "", False
            date_part, time_part = parts
            # Infer year: try current, fall back to next if past
            candidate = f"{date_part}.{now.year} {time_part}"
            dt = datetime.strptime(candidate, "%d.%m.%Y %H:%M")
            if dt.date() < now.date():  # If date is past, bump year
                dt = dt.replace(year=dt.year + 1)
                is_inferred = True
            formatted_time = dt.strftime("%d.%m.%Y %H:%M")
            return dt, formatted_time, is_inferred

        elif re.match(DATE_TIME_FULL, time_input):
            dt = datetime.strptime(time_input, "%d.%m.%Y %H:%M")
            formatted_time = dt.strftime("%d.%m.%Y %H:%M")
            return dt, formatted_time, False

        elif re.match(DATE_ONLY, time_input):
            dt = datetime.strptime(f"{time_input} 00:00", "%d.%m.%Y %H:%M")
            formatted_time = dt.strftime("%d.%m.%Y")
            return dt, formatted_time, False

        else:
            return None, "", False

    except ValueError:
        return None, "", False

def validate_todo(message: str, events: list[dict]) -> bool:
    """
    Check if a to-do with the given message already exists (case-insensitive).
    
    Args:
        message: The to-do message to check.
        events: List of event dicts.
    
    Returns:
        True if unique, False if duplicate.
    """
    lower_message = message.strip().lower()
    for event in events:
        if (
            event.get("type") == "todo"
            and event.get("active")
            and event.get("message", "").strip().lower() == lower_message
        ):
            return False
    return True

def check_message_format(message: str) -> bool:
    """
    Validate message: non-empty after strip, max 4096 chars (Telegram limit).
    
    Args:
        message: The message to validate.
    
    Returns:
        True if valid.
    """
    stripped = message.strip()
    return bool(stripped) and len(stripped) <= 4096

def get_error_message(error_type: str) -> str:
    """
    Get a formatted error message by type.
    
    Args:
        error_type: Key like "empty", "duplicate_todo", "invalid_time".
    
    Returns:
        Error string, or generic if unknown.
    """
    errors = {
        "empty": "❌ Empty or invalid message",
        "duplicate_todo": "❌ Duplicate to-do (case-insensitive)",
        "invalid_time": "❌ Invalid date/time format. Use DD.MM.YYYY HH:MM, DD.MM HH:MM, or DD.MM.YYYY (two digits for day and month)"
    }
    return errors.get(error_type, "❌ Unknown error")

def validate_event(message: str, time_input: str, event_type: str, events: list[dict]) -> Tuple[bool, str]:
    """
    Orchestrate validation for an event or to-do.
    
    Args:
        message: Event/to-do message.
        time_input: Time string (or "todo").
        event_type: "todo" or "terminated".
        events: List of existing events.
    
    Returns:
        (is_valid: bool, error_msg: str)
    """
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