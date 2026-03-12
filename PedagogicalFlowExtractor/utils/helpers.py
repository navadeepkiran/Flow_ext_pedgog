"""Common helper functions for PedagogicalFlowExtractor."""

import json
import os
from datetime import datetime

from utils.config import resolve_path


def load_json(path: str) -> dict | list:
    """Load a JSON file, resolving relative paths from project root."""
    full_path = resolve_path(path) if not os.path.isabs(path) else path
    with open(full_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: dict | list, path: str, indent: int = 2) -> str:
    """Save data as JSON file. Returns the full path written to."""
    full_path = resolve_path(path) if not os.path.isabs(path) else path
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    return full_path


def format_timestamp(seconds: float) -> str:
    """Convert seconds to MM:SS format.

    Args:
        seconds: Time in seconds.

    Returns:
        Formatted string like '3:45'.
    """
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}:{secs:02d}"


def now_iso() -> str:
    """Return current UTC time in ISO 8601 format."""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
