"""Availability window for birthday wishes and gift payments."""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = ZoneInfo("Africa/Nairobi")


def _now() -> datetime:
    """Return the current time in the application's local timezone."""
    return datetime.now(DEFAULT_TIMEZONE)


def submission_cutoff() -> datetime:
    """Return tomorrow's midnight as the end of today's submission window."""
    tomorrow = _now().date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=DEFAULT_TIMEZONE)


def submissions_open() -> bool:
    """Return whether today's midnight-to-midnight submission window is open."""
    return _now() < submission_cutoff()
