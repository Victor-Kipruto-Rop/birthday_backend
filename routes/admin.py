"""Protected read-only endpoints for the owner."""

import hmac

from flask import Blueprint, request

from config import Config
from models.storage import wish_repository
from utils.responses import error, success

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/api/admin/wishes", methods=["GET"])
def list_wishes():
    """Return stored wishes to the owner with the configured admin token."""
    supplied = request.headers.get("X-Admin-Token", "")
    if not Config.ADMIN_TOKEN or not hmac.compare_digest(supplied, Config.ADMIN_TOKEN):
        return error("Unauthorized.", status_code=401)
    return success(message="Wishes retrieved.", data={"wishes": wish_repository.find_all()})
