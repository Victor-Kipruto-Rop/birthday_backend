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
from utils.logger import get_logger

logger = get_logger(__name__)


def create_app() -> Flask:
    """Application factory - builds and configures the Flask app instance."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Restrict CORS to the configured frontend origin only.
    CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_URL}})

    # Register all route blueprints.
    app.register_blueprint(health_bp)
    app.register_blueprint(wishes_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(callback_bp)

    # Surface any soft configuration warnings at startup.
    for warning in Config.validate():
        logger.warning("Configuration warning: %s", warning)

    logger.info("Flask app created and configured successfully.")
    return app


app = create_app()

if __name__ == "__main__":
    # Local development server only. In production, Gunicorn imports
    # `app` directly (see Procfile / start command: gunicorn app:app).
    app.run(host="0.0.0.0", port=5000, debug=False)
