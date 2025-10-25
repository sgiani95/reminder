from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import json
import logging
from datetime import datetime, timedelta
from input_validation import parse_datetime, validate_todo, check_message_format

logger = logging.getLogger(__name__)

class EventManager:
    """Manages event storage, loading, saving, and cleanup."""
    
    def __init__(self, events_file: str):
        self.events_file = Path(events_file)
        self._events: List[Dict[str, Any]] = []
        self.load_events()
    
    def load_events(self) -> List[Dict[str, Any]]:
        """Load events from JSON and filter expired ones."""
        if not self.events_file.exists():
            self._events = []
            self.save_events()
            return self._events
        
        try:
            with self.events_file.open("r") as f:
                loaded_events = json.load(f)
            self._events = self._cleanup_expired(loaded_events)
            self.save_events()  # Persist cleanup
            logger.info(f"Loaded {len(self._events)} events")
            return self._events
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load events: {e}")
            self._events = []
            return self._events
    
    def _cleanup_expired(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out expired terminated events."""
        current_time = datetime.now()
        return [
            event for event in events
            if not (event.get("type") == "terminated" and event.get("active") and
                    self._parse_event_time(event["time"])[0] and
                    self._parse_event_time(event["time"])[0] < current_time)
        ]
    
    def _parse_event_time(self, time_str: str) -> Tuple[Optional[datetime], str, bool]:
        """Helper to parse event time."""
        return parse_datetime(time_str)
    
    def save_events(self) -> bool:
        """Save events to JSON."""
        try:
            with self.events_file.open("w") as f:
                json.dump(self._events, f, indent=4)
            return True
        except IOError as e:
            logger.error(f"Failed to save events: {e}")
            return False
    
    def add_event(self, event: Dict[str, Any]) -> bool:
        """Add a new event."""
        if self._validate_event_for_add(event):
            self._events.append(event)
            return self.save_events()
        return False
    
    def _validate_event_for_add(self, event: Dict[str, Any]) -> bool:
        """Validate before adding (basic checks)."""
        message = event.get("message", "")
        time_input = event.get("time", "")
        event_type = event.get("type", "")
        
        if not check_message_format(message):
            logger.warning(f"Invalid message format: {message}")
            return False
        
        if event_type == "todo":
            if not validate_todo(message, self._events):
                logger.warning(f"Duplicate todo: {message}")
                return False
        elif event_type == "terminated":
            dt, _, _ = self._parse_event_time(time_input)
            if not dt:
                logger.warning(f"Invalid time for terminated event: {time_input}")
                return False
        
        return True
    
    def delete_event_by_message(self, message: str) -> bool:
        """Delete event by message (case-insensitive)."""
        lower_message = message.lower()
        matched = [e for e in self._events if e.get("message", "").lower() == lower_message and e.get("active")]
        if not matched:
            return False
        
        if len(matched) > 1:
            logger.warning(f"Multiple matches for deletion '{message}'; deleting first.")
        
        self._events.remove(matched[0])
        return self.save_events()
    
    def get_active_events(self, show_upcoming: bool = False) -> List[Dict[str, Any]]:
        """Get filtered active events; optionally only upcoming in next 24h."""
        current_time = datetime.now()
        all_active = [e for e in self._events if e.get("active")]
        todos = [e for e in all_active if e["type"] == "todo"]
        terminated = [e for e in all_active if e["type"] == "terminated"]
        
        # Sort
        todos.sort(key=lambda e: e["id"])
        terminated.sort(key=lambda e: self._parse_event_time(e["time"])[0] or datetime.max)
        
        if show_upcoming:
            threshold = current_time + timedelta(hours=24)
            terminated = [e for e in terminated if current_time <= self._parse_event_time(e["time"])[0] <= threshold]
        
        return todos + terminated
    
    def get_upcoming_for_reminders(self) -> List[Dict[str, Any]]:
        """Get events due in next 24h for reminders."""
        current_time = datetime.now()
        threshold = current_time + timedelta(hours=24)
        return [
            e for e in self._events
            if e["type"] == "terminated" and e.get("active") and
               current_time <= self._parse_event_time(e["time"])[0] <= threshold
        ]