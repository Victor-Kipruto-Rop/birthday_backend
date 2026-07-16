"""
routes package
===============
Exposes all Flask blueprints so app.py can import and register them
in one place.
"""

from routes.health import health_bp
from routes.wishes import wishes_bp
from routes.payments import payments_bp
from routes.callback import callback_bp

__all__ = ["health_bp", "wishes_bp", "payments_bp", "callback_bp"]
