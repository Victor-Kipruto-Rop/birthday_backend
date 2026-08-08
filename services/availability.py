"""Availability window for birthday wishes and gift payments."""

from datetime import datetime
from zoneinfo import ZoneInfo

# The deadline is midnight at the end of 8 August 2026 in East Africa Time.
SUBMISSION_CUTOFF = datetime(2026, 8, 9, 0, 0, tzinfo=ZoneInfo("Africa/Nairobi"))


def submissions_open() -> bool:
    """Return whether wishes and new gift payments may still be submitted."""
    return datetime.now(SUBMISSION_CUTOFF.tzinfo) < SUBMISSION_CUTOFF
