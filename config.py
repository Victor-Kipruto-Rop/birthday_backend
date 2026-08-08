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
import secrets
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
from urllib.parse import urlparse

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


def parse_frontend_origins(value: str) -> list[str]:
    """Parse a comma-separated list of frontend origins for CORS."""
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    return origins or ["http://localhost:3000"]


class Config:
    """Application-wide configuration object."""

    # --- Core Flask config -------------------------------------------------
    SECRET_KEY: str = _get_env("SECRET_KEY", default="dev-secret-key-change-me")

    # --- Frontend / CORS -----------------------------------------------------
    FRONTEND_URL: str = _get_env(
        "FRONTEND_URL",
        default="http://localhost:3000,https://birthday-frontend-gamma.vercel.app",
    )
    FRONTEND_URLS: list[str] = parse_frontend_origins(FRONTEND_URL)

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
    ADMIN_TOKEN: str = _get_env("ADMIN_TOKEN", default="")

    # --- Submission availability ------------------------------------------
    # ISO-8601 timestamp with timezone, e.g. 2026-08-09T00:00:00+03:00.
    SUBMISSION_CUTOFF_ISO: str = _get_env(
        "SUBMISSION_CUTOFF_ISO", default="2026-08-09T00:00:00+03:00"
    )

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
        try:
            cutoff = datetime.fromisoformat(cls.SUBMISSION_CUTOFF_ISO)
            if cutoff.tzinfo is None:
                raise ValueError("timezone is missing")
        except ValueError as exc:
            raise RuntimeError(
                "SUBMISSION_CUTOFF_ISO must be a timezone-aware ISO-8601 timestamp."
            ) from exc
        if not cls.PAYHERO_CHANNEL_ID.isdigit():
            raise RuntimeError("PAYHERO_CHANNEL_ID must contain only digits.")
        callback_url = urlparse(cls.PAYHERO_CALLBACK_URL)
        if callback_url.scheme != "https" and callback_url.hostname not in {"localhost", "127.0.0.1"}:
            raise RuntimeError("PAYHERO_CALLBACK_URL must use HTTPS in production.")
        
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

    @classmethod
    def _load_or_generate_admin_token(cls) -> str:
        """Load an admin token from disk or generate one if none was provided."""
        if cls.ADMIN_TOKEN:
            return cls.ADMIN_TOKEN

        token_file = Path(cls.DATA_DIR) / ".admin_token"
        token_file.parent.mkdir(parents=True, exist_ok=True)

        if token_file.exists():
            token = token_file.read_text(encoding="utf-8").strip()
            if token:
                return token

        token = secrets.token_urlsafe(32)
        token_file.write_text(token, encoding="utf-8")
        try:
            token_file.chmod(0o600)
        except OSError:
            pass
        return token


# Ensure a secure admin token exists even when ADMIN_TOKEN is not configured.
Config.ADMIN_TOKEN = Config._load_or_generate_admin_token()

