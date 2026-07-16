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

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

# Determine storage backend based on Redis availability.
storage_uri = None
if Config.REDIS_URL:
    storage_uri = Config.REDIS_URL
    logger.info("Rate limiter using Redis backend: %s", Config.REDIS_URL)
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
