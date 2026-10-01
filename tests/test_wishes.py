"""
tests/test_wishes.py
=====================
Tests for the /api/wish endpoint and related validation.
"""

import pytest

from config import Config, normalize_redis_url, parse_frontend_origins
from services.availability import submissions_open


def test_parse_frontend_origins_supports_csv():
    """A comma-separated FRONTEND_URL should expand to multiple allowed origins."""
    assert parse_frontend_origins("https://a.example, https://b.example") == [
        "https://a.example",
        "https://b.example",
    ]


def test_normalize_redis_url_accepts_redis_cli_output():
    """A copied redis-cli command should be normalized to its connection URI."""
    assert normalize_redis_url("redis-cli -u redis://localhost:6379/0") == (
        "redis://localhost:6379/0"
    )


def test_normalize_redis_url_rejects_non_redis_values():
    """Invalid Redis configuration should fail with an actionable message."""
    with pytest.raises(RuntimeError, match="REDIS_URL must be a Redis URI"):
        normalize_redis_url("redis-cli --tls")


def test_health_check(client):
    """GET /api/health should return healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


def test_root_serves_pulsegate_page(client):
    """GET / should serve the PulseGate landing page."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"<h1>PulseGate</h1>" in response.data
    assert b"SYSTEM ONLINE" in response.data


def test_root_falls_back_to_bundled_pulsegate_page(client, monkeypatch):
    """GET / should work when the frontend repository is deployed separately."""
    import routes.health as health_routes

    monkeypatch.setattr(health_routes, "_PULSEGATE_PAGE", health_routes.Path("missing-pulsegate.html"))
    response = client.get("/")
    assert response.status_code == 200
    assert b"<h1>PulseGate</h1>" in response.data


def test_availability_check(client):
    """GET /api/availability should expose the configured submission window."""
    response = client.get("/api/availability")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert isinstance(data["data"]["open"], bool)
    assert data["data"]["start_iso"] == Config.SUBMISSION_START_ISO
    assert "cutoff_iso" in data["data"]


@pytest.mark.parametrize(
    ("now", "expected"),
    [
        ("2026-09-30T23:59:59+03:00", False),
        ("2026-10-01T00:00:00+03:00", True),
        ("2026-10-01T20:02:45+03:00", True),
        ("2026-10-02T23:59:59+03:00", True),
        ("2026-10-03T00:00:00+03:00", False),
    ],
)
def test_submission_window_boundaries(monkeypatch, now, expected):
    """The window opens immediately and closes exclusively at Saturday midnight."""
    from datetime import datetime

    monkeypatch.setattr(Config, "SUBMISSION_START_ISO", "2026-10-01T00:00:00+03:00")
    monkeypatch.setattr(Config, "SUBMISSION_CUTOFF_ISO", "2026-10-03T00:00:00+03:00")
    assert submissions_open(datetime.fromisoformat(now)) is expected


def test_health_page_renders(client):
    """GET /health should return an HTML status page."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.mimetype.startswith("text/html")
    assert b"Health Check" in response.data
    assert b"/api/health" in response.data


def test_api_page_renders(client):
    """GET /api should return the API landing page."""
    response = client.get("/api")
    assert response.status_code == 200
    assert response.mimetype.startswith("text/html")
    assert b"API Endpoints" in response.data
    assert b"/api/health" in response.data


def test_admin_wishes_requires_token(client):
    """The wishes export must never be publicly accessible."""
    response = client.get("/api/admin/wishes")
    assert response.status_code == 401


def test_wish_submit_valid(client):
    """POST /api/wish with valid data should create a wish."""
    response = client.post(
        "/api/wish",
        json={
            "name": "Jane Doe",
            "phone": "0712345678",
            "message": "Happy birthday! Wishing you the best.",
        },
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["name"] == "Jane Doe"
    assert "created_at" in data["data"]


def test_wish_submission_rejected_outside_window(client, monkeypatch):
    """The API must reject a wish before the opening time, even if the UI is bypassed."""
    monkeypatch.setattr(Config, "SUBMISSION_START_ISO", "2999-01-01T00:00:00+03:00")
    response = client.post(
        "/api/wish",
        json={
            "name": "Jane Doe",
            "phone": "0712345678",
            "message": "Happy birthday!",
        },
    )
    assert response.status_code == 403


def test_wish_missing_name(client):
    """POST /api/wish without name should return 422."""
    response = client.post(
        "/api/wish",
        json={"phone": "0712345678", "message": "Happy birthday!"},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert data["success"] is False
    assert "name" in data["errors"]


def test_wish_missing_phone(client):
    """POST /api/wish without phone should return 422."""
    response = client.post(
        "/api/wish",
        json={"name": "Jane Doe", "message": "Happy birthday!"},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "phone" in data["errors"]


def test_wish_invalid_phone(client):
    """POST /api/wish with invalid phone should return 422."""
    response = client.post(
        "/api/wish",
        json={
            "name": "Jane Doe",
            "phone": "123",  # Invalid
            "message": "Happy birthday!",
        },
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "phone" in data["errors"]


def test_wish_missing_message(client):
    """POST /api/wish without message should return 422."""
    response = client.post(
        "/api/wish",
        json={"name": "Jane Doe", "phone": "0712345678"},
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "message" in data["errors"]


def test_wish_message_too_long(client):
    """POST /api/wish with message > 1000 chars should return 422."""
    response = client.post(
        "/api/wish",
        json={
            "name": "Jane Doe",
            "phone": "0712345678",
            "message": "a" * 1001,  # Too long
        },
    )
    assert response.status_code == 422
    data = response.get_json()
    assert "message" in data["errors"]


def test_wish_rate_limit(client):
    """POST /api/wish more than 5 times per minute should return 429."""
    names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank"]
    for i, name in enumerate(names):
        response = client.post(
            "/api/wish",
            json={
                "name": name,
                "phone": "0712345678",
                "message": "Happy birthday!",
            },
        )
        if i < 5:
            assert response.status_code == 201, f"Wish #{i} failed: {response.get_json()}"
        else:
            # 6th request should be rate-limited
            assert response.status_code == 429
            data = response.get_json()
            assert data["success"] is False
