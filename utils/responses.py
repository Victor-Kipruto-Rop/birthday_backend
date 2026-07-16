"""
utils/responses.py
===================
Reusable, consistent JSON response builders for every API endpoint.

Every response returned by the API follows one of these two shapes:

Success:
    {
        "success": true,
        "message": "...",
        "data": { ... }
    }

Error:
    {
        "success": false,
        "message": "...",
        "errors": { ... }   # optional, e.g. field-level validation errors
    }
"""

from typing import Any, Optional
from flask import jsonify, Response


def success(message: str = "Success", data: Optional[Any] = None, status_code: int = 200) -> tuple[Response, int]:
    """Build a standard success JSON response."""
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {},
    }
    return jsonify(payload), status_code


def error(message: str = "An error occurred", status_code: int = 400, errors: Optional[Any] = None) -> tuple[Response, int]:
    """Build a standard error JSON response."""
    payload = {
        "success": False,
        "message": message,
    }
    if errors is not None:
        payload["errors"] = errors
    return jsonify(payload), status_code


def validation_error(errors: Any, message: str = "Validation failed") -> tuple[Response, int]:
    """Build a 422 validation error JSON response."""
    return error(message=message, status_code=422, errors=errors)


def server_error(message: str = "Internal server error") -> tuple[Response, int]:
    """Build a 500 server error JSON response."""
    return error(message=message, status_code=500)
