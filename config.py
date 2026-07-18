"""
config.py
=========
Centralized application configuration.

All configuration values are loaded from environment variables (via a
`.env` file during local development, or the hosting platform's
environment variable settings in production - e.g. Render).

Nothing in this file should ever contain a hardcoded secret. If a
required variable is missing, sensible defaults are used only where it
is safe to do so (e.g. LOG_LEVEL); anything security or payment related
will raise a clear error at startup instead of failing silently later.
"""

import os
from dotenv import load_dotenv

# Load variables from a .env file if present (local development).
# In production (Render), environment variables are injected directly
# by the platform, so load_dotenv() simply becomes a no-op there.
load_dotenv()


def _get_env(name: str, default: str | None = None, required: bool = False) -> str:
    """Fetch an environment variable with optional required enforcement."""
    value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(
            f"Missing required environment variable: '{name}'. "
            f"Please set it in your .env file or hosting platform config."
        )
    return value


class Config:
    """Application-wide configuration object."""

    # --- Core Flask config -------------------------------------------------
    SECRET_KEY: str = _get_env("SECRET_KEY", default="dev-secret-key-change-me")

    # --- Frontend / CORS -----------------------------------------------------
    FRONTEND_URL: str = _get_env("FRONTEND_URL", default="http://localhost:3000")

    # --- SMTP / Email config -------------------------------------------------
    SMTP_SERVER: str = _get_env("SMTP_SERVER", default="smtp.gmail.com")
    SMTP_PORT: int = int(_get_env("SMTP_PORT", default="587"))
    SMTP_EMAIL: str = _get_env("SMTP_EMAIL", default="")
    SMTP_PASSWORD: str = _get_env("SMTP_PASSWORD", default="")
    RECIPIENT_EMAIL: str = _get_env("RECIPIENT_EMAIL", default="")

    # --- Pay Hero config -------------------------------------------------
    PAYHERO_BASE_URL: str = _get_env(
        "PAYHERO_BASE_URL", default="https://backend.payhero.co.ke/api/v2"
    )
    PAYHERO_USERNAME: str = _get_env("PAYHERO_USERNAME", default="")
    PAYHERO_PASSWORD: str = _get_env("PAYHERO_PASSWORD", default="")
    PAYHERO_CHANNEL_ID: str = _get_env("PAYHERO_CHANNEL_ID", default="")
    PAYHERO_PROVIDER: str = _get_env("PAYHERO_PROVIDER", default="m-pesa")
    PAYHERO_CALLBACK_URL: str = _get_env("PAYHERO_CALLBACK_URL", default="")

    # --- Logging -------------------------------------------------
    LOG_LEVEL: str = _get_env("LOG_LEVEL", default="INFO")

    # --- Storage -------------------------------------------------
    # Base directory for JSON-file storage (see models/storage.py).
    DATA_DIR: str = _get_env("DATA_DIR", default="data")

    # --- Database (optional, replaces JSON if set) ----------------
    # PostgreSQL URL, e.g. postgresql://user:pass@localhost/birthday_db
    # If set, all storage goes to PostgreSQL. If not set, falls back to JSON files.
    DATABASE_URL: str = _get_env("DATABASE_URL", default="")

    # --- Redis (optional, for scaling rate limiter) ----------------
    # Redis URL for distributed rate limiting, e.g. redis://localhost:6379/0
    # If set, rate limits are enforced across multiple workers/instances.
    # If not set, falls back to in-memory (only works with single worker).
    REDIS_URL: str = _get_env("REDIS_URL", default="")

    @classmethod
    def validate(cls) -> list[str]:
        """
        Perform startup validation. Pay Hero credentials are REQUIRED
        for production — app must not boot without them.
        Returns list of warnings; raises RuntimeError on critical missing config.
        """
        warnings = []
        
        # SOFT WARNINGS (app boots but user sees warnings in logs)
        if cls.SECRET_KEY == "dev-secret-key-change-me":
            warnings.append("SECRET_KEY is using the insecure default value.")
        if not cls.SMTP_EMAIL or not cls.SMTP_PASSWORD:
            warnings.append("SMTP_EMAIL / SMTP_PASSWORD not fully configured.")
        
        # HARD FAILURES (app cannot boot without these)
        if not cls.PAYHERO_USERNAME:
            raise RuntimeError(
                "PAYHERO_USERNAME not set. Cannot boot without Pay Hero credentials. "
                "Set via: export PAYHERO_USERNAME=... (or Render Environment dashboard)"
            )
        if not cls.PAYHERO_PASSWORD:
            raise RuntimeError(
                "PAYHERO_PASSWORD not set. Cannot boot without Pay Hero credentials. "
                "Set via: export PAYHERO_PASSWORD=... (or Render Environment dashboard)"
            )
        if not cls.PAYHERO_CHANNEL_ID:
            raise RuntimeError(
                "PAYHERO_CHANNEL_ID not set. Cannot boot without Pay Hero credentials. "
                "Set via: export PAYHERO_CHANNEL_ID=... (or Render Environment dashboard)"
            )
        if not cls.PAYHERO_CALLBACK_URL:
            raise RuntimeError(
                "PAYHERO_CALLBACK_URL not set. Payment callbacks will fail. "
                "Set via: export PAYHERO_CALLBACK_URL=https://your-backend/api/payhero/callback"
            )
        
        return warnings

