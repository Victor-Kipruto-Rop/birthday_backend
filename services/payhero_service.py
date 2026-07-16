"""
services/payhero_service.py
============================
All Pay Hero API integration logic lives here:
    - Basic Auth header generation
    - STK Push initiation
    - Payment status checks
    - Transient-failure retry handling

Pay Hero API reference: https://payhero.co.ke/
"""

import base64
import time
from typing import Any, Optional

import requests

from config import Config
from utils.helpers import generate_reference
from utils.logger import get_logger

logger = get_logger(__name__)

_MAX_RETRIES = 3
_RETRY_BACKOFF_SECONDS = 1.5
_REQUEST_TIMEOUT = 20

# Errors worth retrying - network blips and server-side hiccups, not
# validation/auth errors which will never succeed on retry.
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504}


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
        "provider": "m-pesa",
        "external_reference": reference,
        "callback_url": Config.PAYHERO_CALLBACK_URL,
    }

    url = f"{Config.PAYHERO_BASE_URL}/payments"

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
    url = f"{Config.PAYHERO_BASE_URL}/transaction-status"
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
