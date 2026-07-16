"""
tests/test_wishes.py
=====================
Tests for the /api/wish endpoint and related validation.
"""

import pytest


def test_health_check(client):
    """GET /api/health should return healthy status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"


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
