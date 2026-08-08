"""
routes/contributions.py
=======================
Public API for retrieving live birthday contributions.

This endpoint returns wishes and successfully completed gift transactions
from the application storage. It intentionally omits private fields like phone
numbers and transaction references so the page can display real contributors
while preserving sender privacy.
"""

from flask import Blueprint

from models.storage import transaction_repository, wish_repository
from utils.responses import success

contributions_bp = Blueprint("contributions", __name__)


def _safe_wish(record: dict) -> dict:
    return {
        "name": record.get("name", "Anonymous"),
        "message": record.get("message", ""),
        "created_at": record.get("created_at"),
    }


def _safe_gift(record: dict) -> dict:
    return {
        "name": record.get("name", "Anonymous"),
        "amount": record.get("amount"),
        "status": record.get("status"),
        "created_at": record.get("created_at"),
    }


def _is_successful_gift(record: dict) -> bool:
    return str(record.get("status", "")).lower() == "success"


@contributions_bp.route("/api/contributions", methods=["GET"])
def list_contributions():
    """Return the live wishes and completed gifts that have been recorded."""
    wishes = [
        _safe_wish(record)
        for record in wish_repository.find_all()
    ]
    gifts = [
        _safe_gift(record)
        for record in transaction_repository.find_all()
        if _is_successful_gift(record)
    ]

    # Sort newest-first based on the timestamp values stored by the backend.
    wishes.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    gifts.sort(key=lambda item: item.get("created_at") or "", reverse=True)

    return success(
        message="Contributions retrieved successfully.",
        data={
            "counts": {
                "wishes": len(wishes),
                "gifts": len(gifts),
            },
            "wishes": wishes,
            "gifts": gifts,
        },
    )
