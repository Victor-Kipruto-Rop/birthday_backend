"""
services/payhero_service.py
============================
All Pay Hero API integration logic lives here:
    - Basic Auth header generation
    - STK Push initiation
    - Payment status checks
    - Transient-failure retry handling
    - Transaction finalization (shared by callback and polling paths)

Pay Hero API reference: https://payhero.co.ke/
"""

import base64
import time
from typing import Any, Optional

import requests

from config import Config
from models.storage import transaction_repository
from services.smtp_service import send_payment_failed, send_payment_success
from utils.helpers import current_timestamp, generate_reference
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 1.5
_REQUEST_TIMEOUT = 20

# Errors worth retrying - network blips and server-side hiccups, not
# validation/auth errors which will never succeed on retry.
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


def _normalize_url(base: str) -> str:
    """Strip trailing slashes to prevent double slashes in URL concatenation."""
    return base.rstrip("/") if base else base


def _normalize_status(raw_status: str) -> str:
    """Map Pay Hero's various status strings to one of: success, failed, pending."""
    _SUCCESS_STATUSES = {"success", "completed", "paid"}
    _FAILED_STATUSES = {"failed", "cancelled", "canceled", "declined", "error"}
    _PENDING_STATUSES = {"queued", "pending", "processing"}
    
    status = (raw_status or "").strip().lower()
    if status in _SUCCESS_STATUSES:
        return "success"
    if status in _FAILED_STATUSES:
        return "failed"
    if status in _PENDING_STATUSES:
        return "pending"
    logger.warning("Unrecognized Pay Hero status value: %r - treating as pending.", raw_status)
    return "pending"


class PayHeroError(Exception):
    """Raised when a Pay Hero API call fails after all retries are exhausted."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def _get_auth_header() -> dict:
    """Build the Basic Authentication header required by the Pay Hero API."""
    credentials = f"{Config.PAYHERO_USERNAME}:{Config.PAYHERO_PASSWORD}"
    encoded = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json",
    }


def _request(method: str, url: str, **kwargs) -> requests.Response:
    """
    Perform an HTTP request without retries. Used for one-shot operations
    like STK Push initiation that should never be automatically repeated.
    """
    try:
        return requests.request(method, url, timeout=_REQUEST_TIMEOUT, **kwargs)
    except requests.exceptions.RequestException as exc:
        logger.error("Pay Hero request failed: %s", exc)
        raise PayHeroError(f"Pay Hero request failed: {exc}")


def _request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    """
    Perform an HTTP request with retry-on-transient-failure behavior.
    Retries on network errors and 5xx responses using exponential backoff.
    Raises PayHeroError if all attempts fail.

    Only used for idempotent operations like status checks that can safely
    be retried without side effects.
    """
    last_exception: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = requests.request(method, url, timeout=_REQUEST_TIMEOUT, **kwargs)

            if response.status_code in _RETRYABLE_STATUS_CODES:
                logger.warning(
                    "Pay Hero returned retryable status %s (attempt %d/%d)",
                    response.status_code, attempt, _MAX_RETRIES,
                )
                last_exception = PayHeroError(
                    f"Pay Hero server error: {response.status_code}", response.status_code
                )
                time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
                continue

            return response

        except requests.exceptions.RequestException as exc:
            logger.warning(
                "Pay Hero request error on attempt %d/%d: %s", attempt, _MAX_RETRIES, exc
            )
            last_exception = exc
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt)

    logger.error("Pay Hero request failed after %d attempts: %s", _MAX_RETRIES, last_exception)
    raise PayHeroError(f"Pay Hero request failed after {_MAX_RETRIES} attempts: {last_exception}")


def initiate_stk_push(phone: str, amount: float, reference: Optional[str] = None) -> dict[str, Any]:
    """
    Initiate an STK Push payment request via Pay Hero.

    IMPORTANT: This method does NOT retry on network/5xx errors. If the request
    fails or times out, we don't automatically resend it, because Pay Hero may
    have already processed the push (sending an M-Pesa prompt to the customer's
    phone). Retrying could result in a duplicate prompt, confusing the customer.

    If the request fails here, the transaction record is still created in a
    "pending" state, and the customer can retry or we can poll later via
    check_payment_status (which safely retries).

    Returns a dict with the transaction reference and Pay Hero's raw response.
    Raises PayHeroError on failure.
    """
    reference = reference or generate_reference("GIFT")

    payload = {
        "amount": amount,
        "phone_number": phone,
        "channel_id": Config.PAYHERO_CHANNEL_ID,
        "provider": Config.PAYHERO_PROVIDER,
        "external_reference": reference,
        "callback_url": Config.PAYHERO_CALLBACK_URL,
    }

    base_url = _normalize_url(Config.PAYHERO_BASE_URL)
    url = f"{base_url}/payments"

    try:
        response = _request("POST", url, json=payload, headers=_get_auth_header())
    except PayHeroError:
        raise

    if response.status_code not in (200, 201):
        logger.error("STK Push failed: %s - %s", response.status_code, response.text)
        raise PayHeroError(
            f"Failed to initiate payment (status {response.status_code})", response.status_code
        )

    data = response.json() if response.content else {}
    logger.info("STK Push initiated successfully. Reference: %s", reference)

    return {
        "reference": reference,
        "phone": phone,
        "amount": amount,
        "provider_response": data,
    }


def check_payment_status(transaction_id: str) -> dict[str, Any]:
    """
    Check the status of a previously initiated payment.

    Returns the raw Pay Hero status payload. Raises PayHeroError on failure.
    """
    base_url = _normalize_url(Config.PAYHERO_BASE_URL)
    url = f"{base_url}/transaction-status"
    params = {"reference": transaction_id}

    response = _request_with_retry("GET", url, params=params, headers=_get_auth_header())

    if response.status_code != 200:
        logger.error(
            "Payment status check failed for %s: %s - %s",
            transaction_id, response.status_code, response.text,
        )
        raise PayHeroError(
            f"Failed to check payment status (status {response.status_code})",
            response.status_code,
        )

    return response.json() if response.content else {}


def finalize_transaction(
    transaction_ref: str, local_record: dict[str, Any], provider_status: dict[str, Any]
) -> None:
    """
    Finalize a transaction after receiving terminal status from Pay Hero.
    
    This shared function is used by both the callback handler and polling status
    checks to ensure consistent finalization logic regardless of how the status
    is obtained.
    
    Args:
        transaction_ref: Transaction reference
        local_record: Local transaction record from storage
        provider_status: Raw Pay Hero API response containing status
        
    Raises: Nothing (logs errors instead)
    """
    verified_status = _normalize_status(provider_status.get("status"))
    
    # Don't finalize if status is still pending
    if verified_status == "pending":
        logger.info("Transaction %s status still pending, not finalizing", transaction_ref)
        return
    
    try:
        # Update storage with terminal status
        transaction_repository.update_status(
            transaction_ref,
            verified_status,
            extra={
                "provider_reference": provider_status.get("mpesa_receipt_number")
                or provider_status.get("provider_reference"),
                "verified_provider_status": provider_status,
                "finalized_at": current_timestamp(),
            },
        )
        
        logger.info("Transaction %s finalized with status: %s", transaction_ref, verified_status)
        
        # Send notification email
        name = local_record.get("name", "Anonymous")
        amount = local_record.get("amount", 0)
        
        if verified_status == "success":
            send_payment_success(name, local_record.get("phone", ""), amount, transaction_ref)
        else:
            send_payment_failed(name, local_record.get("phone", ""), amount, transaction_ref, reason=verified_status)
    
    except Exception as exc:
        logger.error("Failed to finalize transaction %s: %s", transaction_ref, exc)
        # Log the error but don't raise - finalization can be retried later
