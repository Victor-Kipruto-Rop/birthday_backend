"""
tests/test_payments.py
=======================
Tests for the /api/payment, /api/payment-status, and /api/payhero/callback
endpoints, including callback forgery protection.
"""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_payhero_initiate():
    """Mock Pay Hero STK Push initiation response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"reference":"E8UWT7CLUW"}'
    mock_resp.json.return_value = {"reference": "E8UWT7CLUW"}
    return mock_resp


@pytest.fixture
def mock_payhero_status_success():
    """Mock Pay Hero status check response (successful payment)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status":"SUCCESS"}'
    mock_resp.json.return_value = {"status": "SUCCESS"}
    return mock_resp


@pytest.fixture
def mock_payhero_status_failed():
    """Mock Pay Hero status check response (failed payment)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status":"FAILED"}'
    mock_resp.json.return_value = {"status": "FAILED"}
    return mock_resp


def test_payment_submit_valid(client, mock_payhero_initiate):
    """POST /api/payment with valid data should initiate STK Push."""
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        response = client.post(
            "/api/payment",
            json={"name": "Jane Doe", "phone": "0712345678", "amount": 500},
        )
    assert response.status_code == 202
    data = response.get_json()
    assert data["success"] is True
    assert "reference" in data["data"]
    assert data["data"]["amount"] == 500


def test_payment_missing_phone(client):
    """POST /api/payment without phone should return 422."""
    response = client.post(
        "/api/payment",
        json={"name": "Jane Doe", "amount": 500},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "phone" in data["errors"]


def test_payment_invalid_amount(client):
    """POST /api/payment with invalid amount should return 422."""
    response = client.post(
        "/api/payment",
        json={"name": "Jane Doe", "phone": "0712345678", "amount": "invalid"},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "amount" in data["errors"]


def test_payment_amount_too_low(client):
    """POST /api/payment with amount < 1 should return 422."""
    response = client.post(
        "/api/payment",
        json={"name": "Jane Doe", "phone": "0712345678", "amount": 0},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "amount" in data["errors"]


def test_payment_rate_limit(client, mock_payhero_initiate):
    """POST /api/payment more than 5 times per minute should return 429."""
    phones = ["0712345671", "0712345672", "0712345673", "0712345674", "0712345675", "0712345676"]
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        for i, phone in enumerate(phones):
            response = client.post(
                "/api/payment",
                json={"name": "Payer", "phone": phone, "amount": 100},
            )
            if i < 5:
                assert response.status_code == 202, f"Payment #{i} failed: {response.get_json()}"
            else:
                # 6th request should be rate-limited
                assert response.status_code == 429
                data = response.get_json()
                assert data["success"] is False


def test_callback_forged_success_rejected(client, mock_payhero_initiate, mock_payhero_status_failed):
    """Forged 'success' callback should be rejected if Pay Hero says 'failed'."""
    # First, create a transaction via /api/payment
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        response = client.post(
            "/api/payment",
            json={"name": "Jane Doe", "phone": "0712345678", "amount": 500},
        )
    assert response.status_code == 202
    ref = response.get_json()["data"]["reference"]

    # Send a forged "success" callback
    with patch("services.payhero_service._request_with_retry", return_value=mock_payhero_status_failed):
        response = client.post(
            "/api/payhero/callback",
            json={"response": {"external_reference": ref, "status": "success"}},
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True

    # Verify the transaction status is "failed" (not "success" from the forged body)
    response = client.get(f"/api/payment-status/{ref}")
    assert response.status_code == 200
    transaction = response.get_json()["data"]
    assert transaction["status"] == "failed"


def test_callback_genuine_success(client, mock_payhero_initiate, mock_payhero_status_success):
    """Genuine successful callback should update transaction status."""
    # Create a transaction
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        response = client.post(
            "/api/payment",
            json={"name": "Jane Doe", "phone": "0712345678", "amount": 500},
        )
    assert response.status_code == 202
    ref = response.get_json()["data"]["reference"]

    # Send a successful callback
    with patch("services.payhero_service._request_with_retry", return_value=mock_payhero_status_success):
        response = client.post(
            "/api/payhero/callback",
            json={"response": {"external_reference": ref, "status": "success"}},
        )

    assert response.status_code == 200

    # Verify the transaction status is "success"
    response = client.get(f"/api/payment-status/{ref}")
    assert response.status_code == 200
    transaction = response.get_json()["data"]
    assert transaction["status"] == "success"


def test_callback_duplicate_ignored(client, mock_payhero_initiate, mock_payhero_status_success):
    """Duplicate callbacks for the same transaction should be idempotent."""
    # Create and finalize a transaction
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        response = client.post(
            "/api/payment",
            json={"name": "Jane Doe", "phone": "0712345678", "amount": 500},
        )
    ref = response.get_json()["data"]["reference"]

    with patch("services.payhero_service._request_with_retry", return_value=mock_payhero_status_success):
        response1 = client.post(
            "/api/payhero/callback",
            json={"response": {"external_reference": ref, "status": "success"}},
        )
    assert response1.status_code == 200

    # Send the same callback again
    with patch("services.payhero_service._request_with_retry", return_value=mock_payhero_status_success):
        response2 = client.post(
            "/api/payhero/callback",
            json={"response": {"external_reference": ref, "status": "success"}},
        )

    # Should still return 200, but indicate it was already processed
    assert response2.status_code == 200
    data = response2.get_json()
    assert "already processed" in data["message"].lower()
