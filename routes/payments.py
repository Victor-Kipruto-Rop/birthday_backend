"""
routes/payments.py
===================
POST /api/payment                          - initiate an STK Push gift payment
GET  /api/payment-status/<transaction_id>  - check the status of a transaction

SECURITY NOTES:
- Payment initiation does NOT return the customer's phone number (privacy)
- Status responses do not include sensitive fields
- Polling path finalizes transactions if they reach terminal status (fixes Issue 4)
"""

from flask import Blueprint, request

from models.storage import transaction_repository
from services.payhero_service import PayHeroError, check_payment_status, finalize_transaction, initiate_stk_push
from services.validation import sanitize_text, validate_payment_payload
from utils.helpers import format_phone_number
from utils.limiter import limiter
from utils.logger import get_logger
from utils.responses import error, server_error, success, validation_error

payments_bp = Blueprint("payments", __name__)
logger = get_logger(__name__)


def _safe_transaction_data(record: dict) -> dict:
    """
    Extract safe transaction data for API responses.
    Excludes sensitive fields like phone numbers and raw provider responses.
    """
    return {
        "reference": record.get("reference"),
        "status": record.get("status"),
        "amount": record.get("amount"),
        "created_at": record.get("created_at"),
        "finalized_at": record.get("finalized_at"),
    }


@payments_bp.route("/api/payment", methods=["POST"])
@limiter.limit("5 per minute")
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
            # NOTE: NOT returning phone number (privacy protection)
            "amount": amount,
        },
        status_code=202,
    )


@payments_bp.route("/api/payment-status/<transaction_id>", methods=["GET"])
def get_payment_status(transaction_id: str):
    """
    Check the current status of a gift payment transaction.
    
    For fast frontend polling, this endpoint:
    1. Returns cached local status immediately if terminal (success/failed)
    2. Attempts ONE quick check with Pay Hero (no retries, fail-fast)
    3. Finalizes if status is terminal
    
    Frontend should poll frequently (every 1-2 sec) for best UX.
    """
    logger.info("=== PAYMENT STATUS CHECK ===")
    logger.info("Transaction ID: %s", transaction_id)
    
    local_record = transaction_repository.find_by_reference(transaction_id)
    if not local_record:
        logger.warning("Transaction not found: %s", transaction_id)
        return error("Transaction not found.", status_code=404)

    logger.info("Local status: %s | Amount: %s | Created: %s | Finalized: %s", 
                local_record.get("status"), 
                local_record.get("amount"),
                local_record.get("created_at"),
                local_record.get("finalized_at"))

    # If we already have a final status recorded (via the callback),
    # return it directly without hitting Pay Hero again.
    if local_record.get("status") in ("success", "failed"):
        logger.info("✅ Returning cached terminal status: %s", local_record.get("status"))
        return success(message="Payment status retrieved.", data=_safe_transaction_data(local_record))

    # Try to fetch live status from Pay Hero (single attempt, no retries)
    try:
        logger.info("🔄 Checking live status with Pay Hero...")
        provider_status = check_payment_status(transaction_id)
        logger.info("Pay Hero status: %s", provider_status.get("status"))
    except PayHeroError as exc:
        logger.debug("Could not fetch live status from Pay Hero (will retry later): %s", exc)
        # Return current local status - callback will update it when it arrives
        logger.info("Returning current local status (Pay Hero check failed)")
        return success(
            message="Payment is still pending confirmation.",
            data=_safe_transaction_data(local_record),
        )

    # CRITICAL FIX (Issue 4): If status is now terminal, finalize it immediately
    # This ensures payments don't stay "pending" forever if the callback never fires
    try:
        logger.info("🔄 Finalizing transaction with provider status: %s", provider_status.get("status"))
        finalize_transaction(transaction_id, local_record, provider_status)
        # Reload updated record after finalization
        local_record = transaction_repository.find_by_reference(transaction_id) or local_record
        logger.info("✅ Transaction finalized. New status: %s", local_record.get("status"))
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to finalize transaction during polling: %s", exc)
        # Still return the response; finalization can be retried on next poll

    logger.info("Returning status: %s", local_record.get("status"))
    return success(
        message="Payment status retrieved.",
        data=_safe_transaction_data(local_record),
    )
