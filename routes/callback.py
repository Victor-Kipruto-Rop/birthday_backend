"""
routes/callback.py
===================
POST /api/payhero/callback - receives asynchronous payment result
notifications from Pay Hero, validates the payload, updates the
transaction record, sends a confirmation email, and always returns
HTTP 200 (per Pay Hero's requirement so it does not endlessly retry).
"""

from flask import Blueprint, request

from models.storage import transaction_repository
from services.smtp_service import send_payment_failed, send_payment_success
from utils.logger import get_logger
from utils.responses import success

callback_bp = Blueprint("callback", __name__)
logger = get_logger(__name__)


def _extract_callback_fields(payload: dict) -> dict:
    """
    Normalize the relevant fields out of Pay Hero's callback payload.
    Pay Hero's exact payload shape can vary by integration; this pulls
    out the fields defensively with fallbacks.
    """
    response = payload.get("response", payload)
    return {
        "reference": response.get("external_reference") or response.get("reference"),
        "status": (response.get("status") or response.get("ResultCode") or "").lower(),
        "provider_reference": response.get("mpesa_receipt_number") or response.get("provider_reference"),
        "amount": response.get("amount"),
        "raw": payload,
    }


@callback_bp.route("/api/payhero/callback", methods=["POST"])
def payhero_callback():
    """Handle an incoming Pay Hero payment callback."""
    payload = request.get_json(silent=True) or {}

    if not payload:
        logger.warning("Received empty/invalid Pay Hero callback payload.")
        # Still return 200 - Pay Hero should not retry on a malformed
        # payload from its own side, and there is nothing useful we can do.
        return success(message="Callback received.", status_code=200)

    fields = _extract_callback_fields(payload)
    reference = fields["reference"]

    if not reference:
        logger.warning("Callback missing a transaction reference: %s", payload)
        return success(message="Callback received.", status_code=200)

    local_record = transaction_repository.find_by_reference(reference)
    if not local_record:
        logger.warning("Callback for unknown transaction reference: %s", reference)
        return success(message="Callback received.", status_code=200)

    # Idempotency guard: if we've already processed a terminal status for
    # this transaction, do not re-send emails or re-process the callback.
    if local_record.get("status") in ("success", "failed"):
        logger.info("Duplicate callback for already-finalized transaction %s - ignoring.", reference)
        return success(message="Callback already processed.", status_code=200)

    is_success = fields["status"] in ("success", "completed", "0", "paid")

    new_status = "success" if is_success else "failed"
    transaction_repository.update_status(
        reference,
        new_status,
        extra={"provider_reference": fields["provider_reference"], "raw_callback": fields["raw"]},
    )

    logger.info("Transaction %s finalized with status: %s", reference, new_status)

    name = local_record.get("name", "Anonymous")
    phone = local_record.get("phone", "")
    amount = local_record.get("amount", fields.get("amount") or 0)

    if is_success:
        send_payment_success(name, phone, amount, reference)
    else:
        send_payment_failed(name, phone, amount, reference, reason=fields["status"] or "declined")

    return success(message="Callback processed successfully.", status_code=200)
