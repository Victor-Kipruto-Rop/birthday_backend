"""
routes/callback.py
===================
POST /api/payhero/callback - receives asynchronous payment result
notifications from Pay Hero, validates the payload, updates the
transaction record, sends a confirmation email, and always returns
HTTP 200 (per Pay Hero's requirement so it does not endlessly retry).

SECURITY NOTE - callback verification:
Pay Hero does not publish a webhook signature or shared-secret scheme
(unlike Stripe/GitHub/PayPal), so the payload's own "status" field
cannot be trusted at face value - anyone who learns or guesses a
transaction reference could POST a forged "success" body to this
endpoint. To close that gap, the callback is treated only as a
*trigger*: it tells us which transaction to look at, but the actual
status is always re-confirmed with our own authenticated call back to
Pay Hero's transaction-status endpoint (Basic Auth, server-to-server)
before anything is finalized or an email is sent. A forged callback
body cannot change that outcome because we never act on it directly.
"""

from flask import Blueprint, request

from models.storage import transaction_repository
from services.payhero_service import PayHeroError, check_payment_status, finalize_transaction
from utils.logger import get_logger
from utils.responses import success

callback_bp = Blueprint("callback", __name__)
logger = get_logger(__name__)


def _extract_reference(payload: dict) -> str | None:
    """
    Pull only the transaction reference out of the callback payload.
    This is the ONLY field we trust from the untrusted callback body -
    it is used exclusively to look up which transaction to re-verify,
    never to determine the outcome.
    """
    response = payload.get("response", payload)
    return response.get("external_reference") or response.get("reference")


@callback_bp.route("/api/payhero/callback", methods=["POST"])
def payhero_callback():
    """Handle an incoming Pay Hero payment callback."""
    payload = request.get_json(silent=True) or {}
    
    logger.info("=== PAYHERO CALLBACK RECEIVED ===")
    logger.info("Payload: %s", payload)

    if not payload:
        logger.warning("Received empty/invalid Pay Hero callback payload.")
        # Still return 200 - Pay Hero should not retry on a malformed
        # payload from its own side, and there is nothing useful we can do.
        return success(message="Callback received.", status_code=200)

    reference = _extract_reference(payload)
    logger.info("Extracted reference: %s", reference)
    
    if not reference:
        logger.warning("Callback missing a transaction reference: %s", payload)
        return success(message="Callback received.", status_code=200)

    local_record = transaction_repository.find_by_reference(reference)
    if not local_record:
        logger.warning("Callback for unknown transaction reference: %s", reference)
        return success(message="Callback received.", status_code=200)

    logger.info("Local record found for %s - Current status: %s", reference, local_record.get("status"))

    # Idempotency guard: if we've already processed a terminal status for
    # this transaction, do not re-send emails or re-process the callback.
    if local_record.get("status") in ("success", "failed"):
        logger.info("Duplicate callback for already-finalized transaction %s - ignoring.", reference)
        return success(message="Callback already processed.", status_code=200)

    # Re-verify the real outcome directly with Pay Hero using our own
    # authenticated request, rather than trusting the callback body.
    try:
        provider_status = check_payment_status(reference)
        logger.info("✅ Verified status from Pay Hero: %s", provider_status.get("status"))
    except PayHeroError as exc:
        logger.error("❌ Could not verify callback for %s via Pay Hero API: %s", reference, exc)
        # Do not finalize on an unverifiable callback. Pay Hero (or our
        # own /api/payment-status polling) will give us another chance
        # to confirm this transaction later.
        return success(message="Callback received, verification pending.", status_code=200)

    # Use shared finalization logic (same as polling path)
    logger.info("🔄 Finalizing transaction %s with provider status: %s", reference, provider_status)
    finalize_transaction(reference, local_record, provider_status)
    
    logger.info("✅ Transaction %s finalized successfully", reference)
    return success(message="Callback processed successfully.", status_code=200)
