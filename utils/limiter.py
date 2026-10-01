"""
utils/limiter.py
=================
Shared Flask-Limiter instance used to rate-limit sensitive, publicly
reachable endpoints (wishes, payments) against spam/abuse.

Defined in its own module (rather than inside app.py) so route
blueprints can import and apply `@limiter.limit(...)` without creating
a circular import with the app factory.

Storage backend:
  - If REDIS_URL is set: uses Redis (shared across multiple workers/instances)
  - Otherwise: uses in-memory storage (only works with a single worker)

For production with multiple Gunicorn workers or horizontal scaling,
set REDIS_URL to a Redis instance, e.g. redis://localhost:6379/0
"""

from urllib.parse import urlparse

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


def _redis_host(storage_uri: str) -> str:
    """Return only the host[:port] of a Redis URL, with credentials removed.

    Used for logging so operators can see WHICH Redis instance is in use
    without the account password ending up in log files.
    """
    try:
        parsed = urlparse(storage_uri)
        return parsed.netloc.rsplit("@", 1)[-1] or "unknown"
    except Exception:  # noqa: BLE001 - logging must never raise
        return "unknown"

# Determine storage backend based on Redis availability.
storage_uri = None
if Config.REDIS_URL:
    storage_uri = Config.REDIS_URL
    # Never log the raw URL: a Redis connection string embeds the account
    # password (redis://user:password@host:port). Log only the host so a
    # misconfiguration is still diagnosable without leaking the secret.
    logger.info(
        "Rate limiter using Redis backend at host %s.",
        _redis_host(storage_uri),
    )
else:
    logger.warning(
        "REDIS_URL not set. Rate limiter using in-memory storage, "
        "which only works with a single worker. For multiple workers "
        "or scaling, set REDIS_URL to a Redis instance."
    )

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=storage_uri,
    default_limits=[],  # no blanket default - each route sets its own limit
)
