"""
tests/conftest.py
==================
Pytest fixtures and configuration for the test suite.
"""

import os
import pytest
from app import create_app


@pytest.fixture
def app():
    """Create and configure a test instance of the app."""
    os.environ["SECRET_KEY"] = "test-key"
    os.environ["FRONTEND_URL"] = "http://localhost:3000"
    os.environ["SMTP_SERVER"] = "smtp.test.local"
    os.environ["SMTP_PORT"] = "587"
    os.environ["SMTP_EMAIL"] = "test@test.local"
    os.environ["SMTP_PASSWORD"] = "test"
    os.environ["RECIPIENT_EMAIL"] = "owner@test.local"
    os.environ["PAYHERO_BASE_URL"] = "https://backend.payhero.co.ke/api/v2"
    os.environ["PAYHERO_USERNAME"] = "test"
    os.environ["PAYHERO_PASSWORD"] = "test"
    os.environ["PAYHERO_CHANNEL_ID"] = "1"
    os.environ["PAYHERO_CALLBACK_URL"] = "http://localhost:5000/api/payhero/callback"
    os.environ["LOG_LEVEL"] = "ERROR"
    os.environ["DATA_DIR"] = ".test_data"
    os.environ["DATABASE_URL"] = ""  # Use JSON storage for tests

    app_instance = create_app()
    app_instance.config["TESTING"] = True

    yield app_instance

    # Cleanup
    import shutil
    if os.path.exists(".test_data"):
        shutil.rmtree(".test_data")


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()
