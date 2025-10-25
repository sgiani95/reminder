from pathlib import Path
from typing import Dict
import json
import logging

logger = logging.getLogger(__name__)

def load_config(config_file: str = "config.json") -> Dict[str, str]:
    """Load and validate configuration from JSON."""
    config_path = Path(config_file)
    if not config_path.exists():
        raise ValueError(f"Configuration file {config_file} not found")
    
    try:
        with config_path.open("r") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {config_file}: {e}")
    
    required_fields = {"GROUP_CHAT_ID", "EVENTS_FILE", "LOG_FILE"}
    missing = required_fields - set(config.keys())
    if missing:
        raise ValueError(f"Missing required fields: {missing}")
    
    for field in required_fields:
        if not isinstance(config[field], str) or not config[field]:
            raise ValueError(f"Invalid {field}: must be a non-empty string")
    
    if not config["GROUP_CHAT_ID"].startswith("-100"):
        raise ValueError("Invalid GROUP_CHAT_ID: must start with '-100'")
    
    logger.info("Configuration loaded successfully")
    return config

# Global config (loaded once)
config = load_config()
GROUP_CHAT_ID = config["GROUP_CHAT_ID"]