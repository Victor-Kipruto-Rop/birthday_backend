"""Availability window for birthday wishes and gift payments."""

from datetime import datetime
from zoneinfo import ZoneInfo

from config import Config

DEFAULT_TIMEZONE = ZoneInfo("Africa/Nairobi")


def submission_start() -> datetime:
    """Return the configured opening time as a timezone-aware datetime."""
    start = datetime.fromisoformat(Config.SUBMISSION_START_ISO)
    return start if start.tzinfo else start.replace(tzinfo=DEFAULT_TIMEZONE)


def submission_cutoff() -> datetime:
    """Return the configured closing time as a timezone-aware datetime."""
    cutoff = datetime.fromisoformat(Config.SUBMISSION_CUTOFF_ISO)
    return cutoff if cutoff.tzinfo else cutoff.replace(tzinfo=DEFAULT_TIMEZONE)


def submissions_open(now: datetime | None = None) -> bool:
    """Return whether wishes and new gift payments may be submitted now."""
    start = submission_start()
    cutoff = submission_cutoff()
    current = now or datetime.now(start.tzinfo)
    if current.tzinfo is None:
        current = current.replace(tzinfo=start.tzinfo)
    else:
        current = current.astimezone(start.tzinfo)
    return start <= current < cutoff
