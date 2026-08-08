"""
routes/health.py
=================
GET /api/health - simple health check endpoint used by Render and any
uptime monitors to verify the service is running.
"""

from flask import Blueprint

from services.availability import submission_cutoff, submissions_open
from utils.responses import success

health_bp = Blueprint("health", __name__)


@health_bp.route("/api/health", methods=["GET"])
def health_check():
    """Return a basic healthy status payload."""
    return success(message="Service is healthy.", data={"status": "healthy"})


@health_bp.route("/api/availability", methods=["GET"])
def availability_check():
    """Return the configured submission window for frontend synchronization."""
    return success(
        message="Availability retrieved.",
        data={
            "open": submissions_open(),
            "cutoff_iso": submission_cutoff().isoformat(),
        },
    )
