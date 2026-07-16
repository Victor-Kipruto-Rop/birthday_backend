"""
utils/helpers.py
=================
Small, reusable helper functions used across the codebase:
phone number formatting, timestamps, reference generation, and
currency formatting.
"""

import random
import re
import string
from datetime import datetime, timezone


def format_phone_number(phone: str) -> str:
    """
    Normalize a Kenyan phone number into the 2547XXXXXXXX / 2541XXXXXXXX
    format required by Pay Hero / M-Pesa.

    Accepts formats like:
        0712345678
        +254712345678
        254712345678
        712345678
    """
    if not phone:
        return ""

    cleaned = re.sub(r"\D", "", phone)  # strip non-digits

    if cleaned.startswith("254") and len(cleaned) == 12:
        return cleaned
    if cleaned.startswith("0") and len(cleaned) == 10:
        return "254" + cleaned[1:]
    if len(cleaned) == 9:  # e.g. 712345678
        return "254" + cleaned
    if cleaned.startswith("2540"):
        # e.g. accidental 2540712345678
        return "254" + cleaned[4:]

    return cleaned


def is_valid_kenyan_phone(phone: str) -> bool:
    """Check whether a formatted phone number matches a valid Safaricom pattern."""
    formatted = format_phone_number(phone)
    return bool(re.fullmatch(r"254(7|1)\d{8}", formatted))


def current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def generate_reference(prefix: str = "BDAY") -> str:
    """Generate a short, random, unique-enough reference code."""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    timestamp_part = datetime.now(timezone.utc).strftime("%y%m%d%H%M%S")
    return f"{prefix}-{timestamp_part}-{suffix}"


def format_currency(amount: float, currency: str = "KES") -> str:
    """Format a numeric amount as a currency string, e.g. KES 1,500.00."""
    try:
        return f"{currency} {float(amount):,.2f}"
    except (TypeError, ValueError):
        return f"{currency} 0.00"
