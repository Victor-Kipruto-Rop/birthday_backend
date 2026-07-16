"""
models/storage.py
==================
Data persistence layer.

This currently uses simple JSON files on disk, but is deliberately
structured as a repository pattern (`JSONRepository` base class with
concrete `WishRepository` / `TransactionRepository` subclasses) so
that swapping in SQLite or PostgreSQL later only requires writing new
repository classes with the same public method signatures - no
changes needed in routes/services that consume them.

Note: JSON-file storage is fine for a small birthday-site MVP, but is
not safe for high-concurrency writes. A basic file lock is used to
reduce (not eliminate) race conditions between concurrent requests.
"""

import json
import os
import threading
from typing import Any, Optional

from config import Config
from utils.helpers import current_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)

_write_lock = threading.Lock()


class JSONRepository:
    """
    Generic JSON-file-backed repository storing a list of dict records.

    Subclasses just set `filename` and get full CRUD-style operations
    for free. The on-disk file always contains a JSON array.
    """

    filename: str = "records.json"

    def __init__(self):
        os.makedirs(Config.DATA_DIR, exist_ok=True)
        self.filepath = os.path.join(Config.DATA_DIR, self.filename)
        if not os.path.exists(self.filepath):
            self._write_all([])

    def _read_all(self) -> list[dict[str, Any]]:
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.error("Failed to read storage file %s: %s", self.filepath, exc)
            return []

    def _write_all(self, records: list[dict[str, Any]]) -> None:
        with _write_lock:
            tmp_path = f"{self.filepath}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, default=str)
            os.replace(tmp_path, self.filepath)  # atomic write

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        """Append a new record, stamping it with a created_at timestamp."""
        record = {**record, "created_at": current_timestamp()}
        records = self._read_all()
        records.append(record)
        self._write_all(records)
        return record

    def find_all(self) -> list[dict[str, Any]]:
        """Return every stored record."""
        return self._read_all()

    def find_by(self, key: str, value: Any) -> Optional[dict[str, Any]]:
        """Return the first record where record[key] == value, or None."""
        for record in self._read_all():
            if record.get(key) == value:
                return record
        return None

    def update_by(self, key: str, value: Any, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update the first record matching key == value, in place."""
        records = self._read_all()
        for record in records:
            if record.get(key) == value:
                record.update(updates)
                record["updated_at"] = current_timestamp()
                self._write_all(records)
                return record
        return None


class WishRepository(JSONRepository):
    """Stores birthday wishes submitted through /api/wish."""

    filename = "wishes.json"


class TransactionRepository(JSONRepository):
    """Stores gift payment transactions and their statuses."""

    filename = "transactions.json"

    def find_by_reference(self, reference: str) -> Optional[dict[str, Any]]:
        return self.find_by("reference", reference)

    def update_status(self, reference: str, status: str, extra: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        updates = {"status": status}
        if extra:
            updates.update(extra)
        return self.update_by("reference", reference, updates)


# Shared singleton instances used across the app.
wish_repository = WishRepository()
transaction_repository = TransactionRepository()
