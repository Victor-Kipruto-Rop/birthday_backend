"""
app.py
======
Application entry point.

Responsibilities (and nothing else):
    - Create the Flask app
    - Enable CORS (restricted to FRONTEND_URL)
    - Load configuration
    - Register Blueprints
    - Start the app (when run directly / locally)

All business logic lives in services/, all persistence in models/,
and all request handling in routes/.
"""

from flask import Flask
from flask_cors import CORS

from config import Config
from routes import health_bp, wishes_bp, payments_bp, callback_bp
from utils.limiter import limiter
from utils.logger import get_logger
from utils.responses import error as error_response

logger = get_logger(__name__)


def create_app() -> Flask:
    """Application factory - builds and configures the Flask app instance."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Validate critical configuration at startup - raises RuntimeError if missing
    warnings = Config.validate()
    for warning in warnings:
        logger.warning("Configuration warning: %s", warning)

    # Restrict CORS to the configured frontend origin only.
    CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})

    # Attach the shared rate limiter (per-route limits are declared in
    # the route modules themselves via @limiter.limit(...)).
    limiter.init_app(app)

    # Register all route blueprints.
    app.register_blueprint(health_bp)
    app.register_blueprint(wishes_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(callback_bp)

    @app.errorhandler(429)
    def handle_rate_limit(_exc):
        """Return rate-limit errors in the same JSON envelope as everything else."""
        return error_response(
            "Too many requests. Please wait a moment and try again.",
            status_code=429,
        )

    logger.info("Flask app created and configured successfully.")
    return app


# Create app instance for Gunicorn (production)
# In tests, pytest fixtures create the app via create_app()
try:
    app = create_app()
except RuntimeError as exc:
    # App cannot boot without credentials - log and re-raise
    # This prevents the app from starting with missing config
    logger.error("Cannot boot app: %s", exc)
    raise

if __name__ == "__main__":
    # Local development server only. In production, Gunicorn imports
    # `app` directly (see Procfile / start command: gunicorn app:app).
    app.run(host="0.0.0.0", port=5000, debug=False)
