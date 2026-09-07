"""Persistent Part Master (Master Linh Kiện) registry backed by SQLite.

Responsibilities
----------------
1. Store and manage master parts: item_code (Mã linh kiện), item_name (Tên linh kiện),
   and rev (Revision).
2. Validate inputs:
   - item_code must not be empty (auto-trimmed, uppercase).
   - item_name must not be empty (prevents missing data).
   - rev must be exactly two digits between "01" and "99".
3. Provide fast lookup by item_code to auto-fill item_name and rev on the main form.
4. Support listing, searching, upserting, and deleting part master records.
"""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class PartMaster:
    """Represents a master part entry."""

    item_code: str
    item_name: str
    rev: str
    updated_at: str = ""


class PartMasterValidationError(ValueError):
    """Raised when part master data fails validation."""


def validate_part_master(item_code: object, item_name: object, rev: object) -> tuple[str, str, str]:
    """Validate and normalize part master fields.

    Rules:
    - item_code: Non-empty, uppercase, trimmed.
    - item_name: Non-empty, trimmed.
    - rev: Exactly 2 digits, "01" to "99".

    Returns:
        (clean_item_code, clean_item_name, clean_rev)
    Raises:
        PartMasterValidationError if any rule is violated.
    """
    code_str = str(item_code or "").strip().upper()
    if not code_str:
        raise PartMasterValidationError("Vui lòng nhập Mã linh kiện!")

    name_str = str(item_name or "").strip()
    if not name_str:
        raise PartMasterValidationError("Vui lòng nhập Tên linh kiện!")

    rev_str = str(rev or "").strip()
    if not rev_str:
        raise PartMasterValidationError("Vui lòng nhập Rev linh kiện!")

    if not (len(rev_str) == 2 and rev_str.isdigit() and 1 <= int(rev_str) <= 99):
        raise PartMasterValidationError(
            f"Rev linh kiện '{rev_str}' không hợp lệ. Rev bắt buộc phải là đúng 2 chữ số (từ 01 đến 99)!"
        )

    return code_str, name_str, rev_str


class PartMasterRegistry:
    """SQLite-backed persistent Part Master registry."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        self._init_connection()

    def _init_connection(self) -> None:
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30.0)
        self._conn.row_factory = sqlite3.Row
        self._setup_pragmas()
        self._create_schema()

    def _setup_pragmas(self) -> None:
        self._conn.execute("PRAGMA busy_timeout=30000")
        is_network = self._db_path.startswith(r"\\") or self._db_path.startswith("//")
        if is_network:
            self._conn.execute("PRAGMA journal_mode=DELETE")
        elif self._db_path != ":memory:":
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                pass

    def _create_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS part_master (
                    item_code TEXT PRIMARY KEY,
                    item_name TEXT NOT NULL,
                    rev TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_part_master_item_name
                ON part_master(item_name);
                """
            )

    def close(self) -> None:
        with self._lock:
            if hasattr(self, "_conn") and self._conn:
                try:
                    self._conn.close()
                except Exception:
                    pass

    def get(self, item_code: str) -> PartMaster | None:
        """Look up a part master entry by item_code (case-insensitive, trimmed)."""
        clean_code = str(item_code or "").strip().upper()
        if not clean_code:
            return None

        with self._lock:
            cur = self._conn.execute(
                "SELECT item_code, item_name, rev, updated_at FROM part_master WHERE item_code = ?",
                (clean_code,),
            )
            row = cur.fetchone()
            if row:
                return PartMaster(
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    rev=row["rev"],
                    updated_at=row["updated_at"],
                )
            return None

    def upsert(self, item_code: object, item_name: object, rev: object) -> PartMaster:
        """Validate and insert or update a part master record."""
        code_clean, name_clean, rev_clean = validate_part_master(item_code, item_name, rev)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO part_master (item_code, item_name, rev, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(item_code) DO UPDATE SET
                    item_name = excluded.item_name,
                    rev = excluded.rev,
                    updated_at = excluded.updated_at;
                """,
                (code_clean, name_clean, rev_clean, now_str),
            )

        return PartMaster(
            item_code=code_clean,
            item_name=name_clean,
            rev=rev_clean,
            updated_at=now_str,
        )

    def delete(self, item_code: str) -> bool:
        """Delete a part master entry by item_code. Returns True if deleted."""
        clean_code = str(item_code or "").strip().upper()
        if not clean_code:
            return False

        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM part_master WHERE item_code = ?",
                (clean_code,),
            )
            return cur.rowcount > 0

    def list_all(self, search_query: str = "") -> list[PartMaster]:
        """List part master entries, optionally filtered by search_query."""
        query = str(search_query or "").strip().upper()
        with self._lock:
            if query:
                pattern = f"%{query}%"
                cur = self._conn.execute(
                    """
                    SELECT item_code, item_name, rev, updated_at
                    FROM part_master
                    WHERE item_code LIKE ? OR UPPER(item_name) LIKE ?
                    ORDER BY item_code ASC;
                    """,
                    (pattern, pattern),
                )
            else:
                cur = self._conn.execute(
                    """
                    SELECT item_code, item_name, rev, updated_at
                    FROM part_master
                    ORDER BY item_code ASC;
                    """
                )

            return [
                PartMaster(
                    item_code=row["item_code"],
                    item_name=row["item_name"],
                    rev=row["rev"],
                    updated_at=row["updated_at"],
                )
                for row in cur.fetchall()
            ]

    def count(self) -> int:
        """Return total number of registered parts in master."""
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM part_master")
            return int(cur.fetchone()[0])
