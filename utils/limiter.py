"""
utils/limiter.py
=================
Shared Flask-Limiter instance used to rate-limit sensitive, publicly
reachable endpoints (wishes, payments) against spam/abuse.

Defined in its own module (rather than inside app.py) so route
blueprints can import and apply `@limiter.limit(...)` without creating
a circular import with the app factory.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Uses in-memory storage by default, which is fine for a single-worker
# deployment. If this app ever runs multiple Gunicorn workers or scales
# horizontally, point storage_uri at a shared backend (e.g. Redis) so
# limits are enforced consistently across processes/instances.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],  # no blanket default - each route sets its own limit
)
