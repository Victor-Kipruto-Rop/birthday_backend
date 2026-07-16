"""
routes/payments.py
===================
POST /api/payment                          - initiate an STK Push gift payment
GET  /api/payment-status/<transaction_id>  - check the status of a transaction
"""

from flask import Blueprint, request

from models.storage import transaction_repository
from services.payhero_service import PayHeroError, check_payment_status, initiate_stk_push
from services.validation import sanitize_text, validate_payment_payload
from utils.helpers import format_phone_number
from utils.logger import get_logger
from utils.responses import error, server_error, success, validation_error

payments_bp = Blueprint("payments", __name__)
logger = get_logger(__name__)


@payments_bp.route("/api/payment", methods=["POST"])
def initiate_payment():
    """Validate a gift payment request and initiate an STK Push via Pay Hero."""
    data = request.get_json(silent=True) or {}

    is_valid, errors = validate_payment_payload(data)
    if not is_valid:
        return validation_error(errors)

    phone = format_phone_number(data.get("phone", ""))
    amount = float(data.get("amount"))
    name = sanitize_text(data.get("name", "")) or "Anonymous"

    try:
        result = initiate_stk_push(phone=phone, amount=amount)
    except PayHeroError as exc:
        logger.error("STK Push initiation failed: %s", exc)
        return error("Unable to initiate payment. Please try again shortly.", status_code=502)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error initiating payment: %s", exc)
        return server_error("Something went wrong while processing your payment.")

    try:
        transaction_repository.add({
            "reference": result["reference"],
            "name": name,
            "phone": phone,
            "amount": amount,
            "status": "pending",
        })
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to persist transaction record: %s", exc)
        # The STK push has already been sent to the user's phone, so we
        # still return success - the callback will reconcile status.

    return success(
        message="Payment initiated. Please check your phone to complete the transaction.",
        data={
            "reference": result["reference"],
            "phone": phone,
            "amount": amount,
        },
        status_code=202,
    )


@payments_bp.route("/api/payment-status/<transaction_id>", methods=["GET"])
def get_payment_status(transaction_id: str):
    """Check the current status of a gift payment transaction."""
    local_record = transaction_repository.find_by_reference(transaction_id)
    if not local_record:
        return error("Transaction not found.", status_code=404)

    # If we already have a final status recorded (via the callback),
    # return it directly without hitting Pay Hero again.
    if local_record.get("status") in ("success", "failed"):
        return success(message="Payment status retrieved.", data=local_record)

    try:
        provider_status = check_payment_status(transaction_id)
    except PayHeroError as exc:
        logger.warning("Could not fetch live status from Pay Hero: %s", exc)
        return success(
            message="Payment is still pending confirmation.",
            data=local_record,
        )

    return success(
        message="Payment status retrieved.",
        data={
            **local_record,
            "provider_status": provider_status,
        },
    )
