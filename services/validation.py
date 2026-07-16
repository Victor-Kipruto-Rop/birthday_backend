"""
services/validation.py
=======================
Validation and sanitization for all user-supplied input:
names, phone numbers, amounts, and messages.

Every function returns a tuple of (is_valid: bool, error_message: str | None)
so calling code can quickly branch on validity while surfacing a clear
error message to the client.
"""

import re
from typing import Optional

from utils.helpers import is_valid_kenyan_phone

_NAME_PATTERN = re.compile(r"^[a-zA-Z\s'\-.]{2,60}$")
_MAX_MESSAGE_LENGTH = 1000
_MIN_AMOUNT = 1
_MAX_AMOUNT = 250_000  # sane upper bound for a gift transaction


def sanitize_text(value: str) -> str:
    """Strip whitespace and remove characters that have no place in plain text fields."""
    if not isinstance(value, str):
        return ""
    # Remove control characters and excessive whitespace.
    cleaned = re.sub(r"[\x00-\x1f\x7f]", "", value)
    return cleaned.strip()


def validate_name(name: str) -> tuple[bool, Optional[str]]:
    """Validate a person's display name."""
    name = sanitize_text(name)
    if not name:
        return False, "Name is required."
    if not _NAME_PATTERN.match(name):
        return False, "Name must be 2-60 characters and contain only letters, spaces, or hyphens."
    return True, None


def validate_phone(phone: str) -> tuple[bool, Optional[str]]:
    """Validate a Kenyan phone number for M-Pesa/Pay Hero transactions."""
    phone = sanitize_text(phone)
    if not phone:
        return False, "Phone number is required."
    if not is_valid_kenyan_phone(phone):
        return False, "Please provide a valid Safaricom phone number (e.g. 0712345678)."
    return True, None


def validate_message(message: str) -> tuple[bool, Optional[str]]:
    """Validate a birthday wish message."""
    message = sanitize_text(message)
    if not message:
        return False, "Message is required."
    if len(message) > _MAX_MESSAGE_LENGTH:
        return False, f"Message must be under {_MAX_MESSAGE_LENGTH} characters."
    return True, None


def validate_amount(amount) -> tuple[bool, Optional[str]]:
    """Validate a gift/payment amount."""
    try:
        amount_value = float(amount)
    except (TypeError, ValueError):
        return False, "Amount must be a valid number."

    if amount_value < _MIN_AMOUNT:
        return False, f"Amount must be at least {_MIN_AMOUNT}."
    if amount_value > _MAX_AMOUNT:
        return False, f"Amount must not exceed {_MAX_AMOUNT}."
    return True, None


def validate_wish_payload(data: dict) -> tuple[bool, dict]:
    """
    Validate an incoming /api/wish payload.
    Returns (is_valid, errors_dict). errors_dict is empty when valid.
    """
    errors = {}

    valid, msg = validate_name(data.get("name", ""))
    if not valid:
        errors["name"] = msg

    valid, msg = validate_phone(data.get("phone", ""))
    if not valid:
        errors["phone"] = msg

    valid, msg = validate_message(data.get("message", ""))
    if not valid:
        errors["message"] = msg

    return (len(errors) == 0), errors


def validate_payment_payload(data: dict) -> tuple[bool, dict]:
    """
    Validate an incoming /api/payment payload.
    Returns (is_valid, errors_dict). errors_dict is empty when valid.
    """
    errors = {}

    valid, msg = validate_phone(data.get("phone", ""))
    if not valid:
        errors["phone"] = msg

    valid, msg = validate_amount(data.get("amount", ""))
    if not valid:
        errors["amount"] = msg

    return (len(errors) == 0), errors
