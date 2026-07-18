"""
models/storage.py
==================
Data persistence layer using a repository pattern.

Automatically chooses the storage backend based on config:
  - If DATABASE_URL is set: PostgreSQL (persistent, scales across workers)
  - Otherwise: JSON files on disk (ephemeral on Render free tier, but zero setup)

The repository pattern (JSONRepository / PostgresRepository base classes with
concrete WishRepository / TransactionRepository subclasses) means swapping
backends only requires adding a new repository class — routes and services
never know or care which backend is in use. All public methods (add, find_all,
find_by, update_by) are backend-agnostic.

Note: on Render's free tier, local disk storage is wiped on redeploy and
most restarts. For production persistence, set DATABASE_URL to a PostgreSQL
database (e.g. Supabase) or pay for Render's persistent disk add-on.
"""

import json
import os
import threading
from contextlib import contextmanager
from typing import Any, Optional

from config import Config
from utils.helpers import current_timestamp
from utils.logger import get_logger

logger = get_logger(__name__)

# In-process lock: guards against races between threads within one
# Gunicorn worker.
_write_lock = threading.Lock()

try:
    import fcntl
    _FCNTL_AVAILABLE = True
except ImportError:
    # fcntl is POSIX-only. Render/production runs Linux, so this is
    # expected to always succeed there; the flag exists mainly so local
    # development on an unsupported OS degrades gracefully (with a
    # warning) instead of crashing.
    _FCNTL_AVAILABLE = False
    logger.warning(
        "fcntl not available on this platform - cross-process file "
        "locking is disabled. Do not run multiple worker processes "
        "against this storage backend in this environment."
    )


@contextmanager
def _cross_process_lock(lock_path: str):
    """
    Hold an OS-level advisory file lock for the duration of the `with`
    block. This protects the JSON storage files across multiple
    Gunicorn worker *processes*, which a plain threading.Lock cannot do
    since each process has its own Python memory space.
    """
    if not _FCNTL_AVAILABLE:
        yield
        return

    # Ensure the directory for the lock file exists
    lock_dir = os.path.dirname(lock_path)
    if lock_dir:
        os.makedirs(lock_dir, exist_ok=True)
    
    lock_file = open(lock_path, "a+")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        lock_file.close()



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
        self.lock_path = f"{self.filepath}.lock"
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
        """
        Append a new record, stamping it with a created_at timestamp.

        The read-modify-write sequence is wrapped in a cross-process
        file lock so two Gunicorn workers appending at the same instant
        cannot silently clobber each other's write.
        """
        record = {**record, "created_at": current_timestamp()}
        with _cross_process_lock(self.lock_path):
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
        """
        Update the first record matching key == value, in place.

        Wrapped in the same cross-process lock as `add` for the same
        reason: this is a read-modify-write sequence, not a single
        atomic operation.
        """
        with _cross_process_lock(self.lock_path):
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


# PostgreSQL-backed repository classes (used if DATABASE_URL is configured).
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


class PostgresRepository:
    """
    PostgreSQL-backed repository. Stores records in a PostgreSQL table.

    Subclasses set `table_name` and get full CRUD operations for free,
    mirroring the JSONRepository interface exactly.
    """

    table_name: str = "records"

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._init_table()

    def _get_connection(self):
        """Get a fresh database connection for this operation."""
        return psycopg2.connect(self.connection_string)

    def _init_table(self) -> None:
        """Create the table if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.table_name} (
                            id SERIAL PRIMARY KEY,
                            data JSONB NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()
        except Exception as exc:
            logger.error("Failed to initialize %s table: %s", self.table_name, exc)

    def add(self, record: dict[str, Any]) -> dict[str, Any]:
        """Append a new record, stamping it with a created_at timestamp."""
        record = {**record, "created_at": current_timestamp()}
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"INSERT INTO {self.table_name} (data) VALUES (%s) RETURNING data",
                        (json.dumps(record, default=str),),
                    )
                    result = cur.fetchone()
                    conn.commit()
                    return dict(result["data"]) if result else record
        except Exception as exc:
            logger.error("Failed to add record to %s: %s", self.table_name, exc)
            return record

    def find_all(self) -> list[dict[str, Any]]:
        """Return every stored record."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(f"SELECT data FROM {self.table_name} ORDER BY created_at DESC")
                    rows = cur.fetchall()
                    return [dict(row["data"]) for row in rows]
        except Exception as exc:
            logger.error("Failed to fetch records from %s: %s", self.table_name, exc)
            return []

    def find_by(self, key: str, value: Any) -> Optional[dict[str, Any]]:
        """Return the first record where record[key] == value, or None."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT data FROM {self.table_name} WHERE data->>%s = %s LIMIT 1",
                        (key, str(value)),
                    )
                    row = cur.fetchone()
                    return dict(row["data"]) if row else None
        except Exception as exc:
            logger.error("Failed to find record in %s: %s", self.table_name, exc)
            return None

    def update_by(self, key: str, value: Any, updates: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update the first record matching key == value, in place."""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        f"SELECT data FROM {self.table_name} WHERE data->>%s = %s LIMIT 1",
                        (key, str(value)),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None

                    record = dict(row["data"])
                    record.update(updates)
                    record["updated_at"] = current_timestamp()

                    cur.execute(
                        f"UPDATE {self.table_name} SET data = %s WHERE data->>%s = %s RETURNING data",
                        (json.dumps(record, default=str), key, str(value)),
                    )
                    result = cur.fetchone()
                    conn.commit()
                    return dict(result["data"]) if result else record
        except Exception as exc:
            logger.error("Failed to update record in %s: %s", self.table_name, exc)
            return None


class PostgresWishRepository(PostgresRepository):
    """Stores birthday wishes in PostgreSQL."""

    table_name = "wishes"


class PostgresTransactionRepository(PostgresRepository):
    """Stores gift payment transactions in PostgreSQL."""

    table_name = "transactions"

    def find_by_reference(self, reference: str) -> Optional[dict[str, Any]]:
        return self.find_by("reference", reference)

    def update_status(self, reference: str, status: str, extra: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
        updates = {"status": status}
        if extra:
            updates.update(extra)
        return self.update_by("reference", reference, updates)


# Shared singleton instances used across the app.
# Automatically selects storage backend: PostgreSQL if configured, else JSON files.

if Config.DATABASE_URL and _PSYCOPG2_AVAILABLE:
    logger.info("Using PostgreSQL for persistence (DATABASE_URL is set).")
    wish_repository = PostgresWishRepository(Config.DATABASE_URL)
    transaction_repository = PostgresTransactionRepository(Config.DATABASE_URL)
elif Config.DATABASE_URL and not _PSYCOPG2_AVAILABLE:
    logger.error(
        "DATABASE_URL is set but psycopg2 is not installed. "
        "Run: pip install psycopg2-binary. Falling back to JSON storage (ephemeral on Render)."
    )
    wish_repository = WishRepository()
    transaction_repository = TransactionRepository()
else:
    if Config.DATABASE_URL is None or Config.DATABASE_URL == "":
        logger.warning(
            "DATABASE_URL not set. Using JSON file storage, which is ephemeral on Render "
            "(wiped on redeploy/restart). For production, set DATABASE_URL to a PostgreSQL "
            "database URL (e.g. from Supabase or add a paid persistent disk to Render)."
        )
    wish_repository = WishRepository()
    transaction_repository = TransactionRepository()
