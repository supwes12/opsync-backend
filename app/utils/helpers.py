"""Utility helpers for UUID generation and datetime formatting."""
import uuid
from datetime import datetime, timezone


def generate_uuid():
    """Generate a new UUID4 string."""
    return str(uuid.uuid4())


def utc_now():
    """Return the current UTC datetime."""
    return datetime.now(timezone.utc)
