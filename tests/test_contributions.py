"""
tests/test_contributions.py
===========================
Regression tests for the live contributions endpoint.
"""

from unittest.mock import MagicMock, patch


def make_mock_payhero_initiate():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"reference":"E8UWT7CLUW"}'
    mock_resp.json.return_value = {"reference": "E8UWT7CLUW"}
    return mock_resp


def make_mock_payhero_status_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"status":"SUCCESS"}'
    mock_resp.json.return_value = {"status": "SUCCESS"}
    return mock_resp


def test_contributions_endpoint_returns_wishes_and_successful_gifts(client):
    # Create a wish and a successful gift transaction.
    response = client.post(
        "/api/wish",
        json={"name": "Alice", "phone": "0712345678", "message": "Happy birthday!"},
    )
    assert response.status_code == 201

    mock_payhero_initiate = make_mock_payhero_initiate()
    with patch("services.payhero_service._request", return_value=mock_payhero_initiate):
        response = client.post(
            "/api/payment",
            json={"name": "Bob", "phone": "0712345678", "amount": 100},
        )
    assert response.status_code == 202
    payment_ref = response.get_json()["data"]["reference"]

    mock_payhero_status_success = make_mock_payhero_status_success()
    with patch("services.payhero_service._request_with_retry", return_value=mock_payhero_status_success):
        callback_response = client.post(
            "/api/payhero/callback",
            json={"response": {"external_reference": payment_ref, "status": "success"}},
        )
    assert callback_response.status_code == 200

    response = client.get("/api/contributions")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["counts"]["wishes"] == 1
    assert data["data"]["counts"]["gifts"] == 1
    assert len(data["data"]["wishes"]) == 1
    assert len(data["data"]["gifts"]) == 1
    assert data["data"]["wishes"][0]["name"] == "Alice"
    assert data["data"]["gifts"][0]["amount"] == 100
