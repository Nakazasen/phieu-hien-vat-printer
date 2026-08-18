"""Persistent PO registry backed by SQLite.

Responsibilities
----------------
1. Auto-generate PO numbers in the format ``11YYMMDDNN`` where NN is a daily
   sequence from 01 to 99.
2. Enforce global uniqueness of the composite key
   ``(po, po_detail, po_sub, box)`` across all sessions, including manual
   entry and Excel import.
3. Provide constants for the fixed PO detail (``00010``) and PO sub
   (``+001``).

The database file ``po_registry.db`` lives in the application's runtime
directory (next to the EXE or next to the source script) and survives
application restarts.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from datetime import date, datetime
from pathlib import Path
from typing import Any

AUTO_PO_PREFIX = "11"
FIXED_PO_DETAIL = "00010"
FIXED_PO_SUB = "+001"
MAX_NN = 99


class PORegistryError(Exception):
    """Base error for PO registry operations."""


class DuplicateComboError(PORegistryError):
    """Raised when a (po, po_detail, po_sub, box) combo already exists."""


class DailySequenceExhaustedError(PORegistryError):
    """Raised when the daily NN sequence exceeds 99."""


class PORegistry:
    """SQLite-backed PO number generator and uniqueness enforcer.

    Parameters
    ----------
    db_path:
        Path to the SQLite database file.  Use ``":memory:"`` for tests.
    """

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = str(db_path)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS po_registry (
                po        TEXT    NOT NULL,
                po_detail TEXT    NOT NULL,
                po_sub    TEXT    NOT NULL,
                box       TEXT    NOT NULL,
                created_at TEXT   NOT NULL DEFAULT (datetime('now','localtime')),
                PRIMARY KEY (po, po_detail, po_sub, box)
            );

            CREATE TABLE IF NOT EXISTS po_sequence (
                date_key  TEXT    PRIMARY KEY,
                next_nn   INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # PO generation
    # ------------------------------------------------------------------

    def generate_po(self, target_date: date | None = None) -> str:
        """Generate the next PO number for *target_date* (default: today).

        Format: ``11YYMMDDNN``

        The NN counter is atomically incremented inside a transaction so
        concurrent calls are safe.

        Raises
        ------
        DailySequenceExhaustedError
            If NN would exceed 99 for the given date.
        """
        if target_date is None:
            target_date = datetime.now().date()

        date_key = target_date.strftime("%Y%m%d")
        yy = target_date.strftime("%y")
        mm = target_date.strftime("%m")
        dd = target_date.strftime("%d")

        cursor = self._conn.cursor()
        try:
            cursor.execute("BEGIN IMMEDIATE")

            row = cursor.execute(
                "SELECT next_nn FROM po_sequence WHERE date_key = ?",
                (date_key,),
            ).fetchone()

            if row is None:
                nn = 1
                cursor.execute(
                    "INSERT INTO po_sequence (date_key, next_nn) VALUES (?, ?)",
                    (date_key, nn + 1),
                )
            else:
                nn = row[0]
                if nn > MAX_NN:
                    raise DailySequenceExhaustedError(
                        f"Đã hết số thứ tự PO trong ngày {target_date.isoformat()} "
                        f"(tối đa {MAX_NN:02d})."
                    )
                cursor.execute(
                    "UPDATE po_sequence SET next_nn = ? WHERE date_key = ?",
                    (nn + 1, date_key),
                )

            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

        return f"{AUTO_PO_PREFIX}{yy}{mm}{dd}{nn:02d}"

    # ------------------------------------------------------------------
    # Uniqueness enforcement
    # ------------------------------------------------------------------

    def register_combo(
        self,
        po: str,
        po_detail: str,
        po_sub: str,
        box: str,
    ) -> None:
        """Register a ``(po, po_detail, po_sub, box)`` combination.

        Raises
        ------
        DuplicateComboError
            If the exact combination already exists in the registry.
        """
        try:
            self._conn.execute(
                "INSERT INTO po_registry (po, po_detail, po_sub, box) "
                "VALUES (?, ?, ?, ?)",
                (po, po_detail, po_sub, box),
            )
            self._conn.commit()
        except sqlite3.IntegrityError:
            raise DuplicateComboError(
                f"Chuỗi PO đã tồn tại: PO={po}, "
                f"PO chi tiết={po_detail}, PO phụ={po_sub}, Box={box}."
            )

    def register_combos(
        self,
        combos: Sequence[tuple[str, str, str, str]],
    ) -> None:
        """Register multiple combos atomically.

        If any combo is duplicate (either within the batch or against existing
        data), the entire batch is rolled back and ``DuplicateComboError`` is
        raised.

        Parameters
        ----------
        combos:
            Each element is ``(po, po_detail, po_sub, box)``.
        """
        if not combos:
            return
        try:
            for po, po_detail, po_sub, box in combos:
                try:
                    self._conn.execute(
                        "INSERT INTO po_registry (po, po_detail, po_sub, box) "
                        "VALUES (?, ?, ?, ?)",
                        (po, po_detail, po_sub, box),
                    )
                except sqlite3.IntegrityError:
                    raise DuplicateComboError(
                        f"Chuỗi PO đã tồn tại: PO={po}, "
                        f"PO chi tiết={po_detail}, PO phụ={po_sub}, Box={box}."
                    )
            self._conn.commit()
        except DuplicateComboError:
            self._conn.rollback()
            raise
        except Exception:
            self._conn.rollback()
            raise


    def is_registered(
        self,
        po: str,
        po_detail: str,
        po_sub: str,
        box: str,
    ) -> bool:
        """Check whether a combination already exists."""
        row = self._conn.execute(
            "SELECT 1 FROM po_registry "
            "WHERE po = ? AND po_detail = ? AND po_sub = ? AND box = ?",
            (po, po_detail, po_sub, box),
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def count_registered(self) -> int:
        """Return the total number of registered combos."""
        row = self._conn.execute("SELECT COUNT(*) FROM po_registry").fetchone()
        return row[0] if row else 0

    def current_nn(self, target_date: date | None = None) -> int:
        """Return the current (next available) NN for *target_date*."""
        if target_date is None:
            target_date = datetime.now().date()
        date_key = target_date.strftime("%Y%m%d")
        row = self._conn.execute(
            "SELECT next_nn FROM po_sequence WHERE date_key = ?",
            (date_key,),
        ).fetchone()
        return row[0] if row else 1

    def fetch_history(self, search: str = "", limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Fetch history records from po_registry with optional search filter."""
        search = search.strip()
        if search:
            query = """
                SELECT po, po_detail, po_sub, box, created_at
                FROM po_registry
                WHERE po LIKE ? OR po_detail LIKE ? OR po_sub LIKE ? OR box LIKE ? OR created_at LIKE ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            pattern = f"%{search}%"
            rows = self._conn.execute(query, (pattern, pattern, pattern, pattern, pattern, limit, offset)).fetchall()
        else:
            query = """
                SELECT po, po_detail, po_sub, box, created_at
                FROM po_registry
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            rows = self._conn.execute(query, (limit, offset)).fetchall()

        return [
            {
                "po": r[0],
                "po_detail": r[1],
                "po_sub": r[2],
                "box": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]

    def get_statistics(self) -> dict[str, Any]:
        """Return high-level statistics about registered POs."""
        total = self.count_registered()
        today_row = self._conn.execute(
            "SELECT COUNT(*) FROM po_registry WHERE date(created_at) = date('now','localtime')"
        ).fetchone()
        today_count = today_row[0] if today_row else 0
        current_nn = self.current_nn()
        today = datetime.now().date()
        next_po = f"{AUTO_PO_PREFIX}{today.strftime('%y%m%d')}{current_nn:02d}"
        return {
            "total_count": total,
            "today_count": today_count,
            "next_po": next_po,
            "current_nn": current_nn,
        }

    def export_history_to_csv(self, file_path: str | Path, search: str = "") -> int:
        """Export history records to a CSV file (UTF-8 with BOM for Excel compatibility)."""
        import csv
        records = self.fetch_history(search=search, limit=100000)
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Thời gian tạo", "Số PO", "PO Chi tiết", "PO Phụ", "Số Box"])
            for r in records:
                writer.writerow([r["created_at"], r["po"], r["po_detail"], r["po_sub"], r["box"]])
        return len(records)

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()
