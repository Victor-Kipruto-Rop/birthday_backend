"""Availability window for birthday wishes and gift payments."""

from datetime import datetime
from zoneinfo import ZoneInfo

from config import Config

DEFAULT_TIMEZONE = ZoneInfo("Africa/Nairobi")


def submission_cutoff() -> datetime:
    """Return the configured cutoff as a timezone-aware datetime."""
    cutoff = datetime.fromisoformat(Config.SUBMISSION_CUTOFF_ISO)
    return cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=DEFAULT_TIMEZONE)


def submissions_open() -> bool:
    """Return whether wishes and new gift payments may still be submitted."""
    cutoff = submission_cutoff()
    return datetime.now(cutoff.tzinfo) < cutoff
