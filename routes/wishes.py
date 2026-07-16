"""
routes/wishes.py
=================
POST /api/wish - accept a birthday wish (name, phone, message),
validate it, persist it, and email a notification.
"""

from flask import Blueprint, request

from models.storage import wish_repository
from services.smtp_service import send_wish_email
from services.validation import sanitize_text, validate_wish_payload
from utils.helpers import format_phone_number
from utils.limiter import limiter
from utils.logger import get_logger
from utils.responses import server_error, success, validation_error

wishes_bp = Blueprint("wishes", __name__)
logger = get_logger(__name__)


@wishes_bp.route("/api/wish", methods=["POST"])
@limiter.limit("5 per minute")
def submit_wish():
    """Receive, validate, store, and email a birthday wish."""
    data = request.get_json(silent=True) or {}

    is_valid, errors = validate_wish_payload(data)
    if not is_valid:
        return validation_error(errors)

    name = sanitize_text(data.get("name", ""))
    phone = format_phone_number(data.get("phone", ""))
    message = sanitize_text(data.get("message", ""))

    try:
        record = wish_repository.add({
            "name": name,
            "phone": phone,
            "message": message,
        })
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to store wish: %s", exc)
        return server_error("Failed to save your wish. Please try again.")

    # Email delivery failures should not fail the request - the wish is
    # already safely stored. We log it and let the response succeed.
    email_sent = send_wish_email(name, phone, message)
    if not email_sent:
        logger.warning("Wish stored but notification email failed to send.")

    return success(
        message="Birthday wish sent successfully.",
        data={
            "name": record["name"],
            "created_at": record["created_at"],
        },
        status_code=201,
    )
