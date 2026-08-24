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
import time
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
        self._init_connection()

    def _setup_pragmas(self) -> None:
        self._conn.execute("PRAGMA busy_timeout=30000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        # Network shares (UNC) do not support shared-memory WAL safely across multiple machines
        is_network = self._db_path.startswith(r"\\") or self._db_path.startswith("//")
        if is_network:
            self._conn.execute("PRAGMA journal_mode=DELETE")
        else:
            try:
                self._conn.execute("PRAGMA journal_mode=WAL")
            except sqlite3.OperationalError:
                self._conn.execute("PRAGMA journal_mode=DELETE")

    def _init_connection(self) -> None:
        if self._db_path != ":memory:":
            try:
                Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass
        try:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30.0)
            self._setup_pragmas()
            # Quick check database integrity
            check = self._conn.execute("PRAGMA quick_check").fetchone()
            if check and check[0] != "ok":
                raise sqlite3.DatabaseError(f"Database corruption: {check[0]}")
            self._create_tables()
        except (sqlite3.DatabaseError, sqlite3.OperationalError) as exc:
            if self._db_path != ":memory:" and any(
                keyword in str(exc).lower()
                for keyword in ("malformed", "corrupt", "disk image", "not a database")
            ):
                self._recover_corrupted_database(exc)
            else:
                raise

    def _recover_corrupted_database(self, cause: Exception) -> None:
        """Safely backup a malformed database and rebuild a clean registry."""
        try:
            if hasattr(self, "_conn") and self._conn is not None:
                self._conn.close()
        except Exception:  # noqa: BLE001
            pass

        path = Path(self._db_path)
        if path.is_file():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = path.with_name(f"{path.stem}_corrupted_{timestamp}{path.suffix}.bak")
            try:
                path.rename(backup_path)
            except Exception:  # noqa: BLE001
                pass

            # Also cleanup stale WAL and SHM files
            wal = path.with_name(f"{path.name}-wal")
            shm = path.with_name(f"{path.name}-shm")
            try:
                if wal.exists():
                    wal.unlink(missing_ok=True)
                if shm.exists():
                    shm.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

        # Reopen fresh database
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=30.0)
        self._setup_pragmas()
        self._create_tables()

    def _execute_with_auto_recovery(self, func):
        """Execute a database function with retry on busy/locked and auto-healing on corruption."""
        max_retries = 5
        base_delay = 0.05
        for attempt in range(max_retries):
            try:
                return func()
            except sqlite3.OperationalError as exc:
                if "locked" in str(exc).lower() or "busy" in str(exc).lower():
                    if attempt < max_retries - 1:
                        time.sleep(base_delay * (2 ** attempt))
                        continue
                raise
            except sqlite3.DatabaseError as exc:
                if self._db_path != ":memory:" and any(
                    keyword in str(exc).lower()
                    for keyword in ("malformed", "corrupt", "disk image", "not a database")
                ):
                    self._recover_corrupted_database(exc)
                    return func()
                raise

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
        return self._execute_with_auto_recovery(lambda: self._generate_po_impl(target_date))

    def _generate_po_impl(self, target_date: date | None = None) -> str:
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
        return self._execute_with_auto_recovery(
            lambda: self._register_combo_impl(po, po_detail, po_sub, box)
        )

    def _register_combo_impl(
        self,
        po: str,
        po_detail: str,
        po_sub: str,
        box: str,
    ) -> None:
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
        return self._execute_with_auto_recovery(lambda: self._register_combos_impl(combos))

    def _register_combos_impl(
        self,
        combos: Sequence[tuple[str, str, str, str]],
    ) -> None:
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
        return self._execute_with_auto_recovery(
            lambda: self._conn.execute(
                "SELECT 1 FROM po_registry "
                "WHERE po = ? AND po_detail = ? AND po_sub = ? AND box = ?",
                (po, po_detail, po_sub, box),
            ).fetchone()
            is not None
        )

    def get_used_po_details(self, po: str) -> list[str]:
        """Return all po_detail values registered for a given PO."""
        return self._execute_with_auto_recovery(
            lambda: [
                r[0]
                for r in self._conn.execute(
                    "SELECT DISTINCT po_detail FROM po_registry WHERE po = ?",
                    (po,),
                ).fetchall()
            ]
        )

    def generate_split_po_detail(
        self,
        po: str,
        base_detail: str = "00010",
        exclude_details: Sequence[str] = (),
    ) -> str:
        """Generate a split detail by incrementing D1 and preserving D3-D5.

        The EDI detail has five digits: ``[D1][D2][D3D4D5]``.  Splitting
        resets D2 to ``0``, allocates the next available D1, and keeps the
        original item-detail suffix intact (for example ``00020`` becomes
        ``10020`` then ``20020``).

        Raises
        ------
        PORegistryError
            If all 9 split detail slots (10010 through 90010) have been exhausted for the given PO.
        """
        base_detail = self._normalize_operation_detail(base_detail)
        suffix = base_detail[2:]
        used = set(self.get_used_po_details(po)) | set(exclude_details)
        for d1 in range(1, 10):
            candidate = f"{d1}0{suffix}"
            if candidate not in used:
                return candidate
        raise PORegistryError(
            f"Đã đạt giới hạn tối đa 9 lần phân tách cho mã PO {po}, "
            f"mã chi tiết gốc {base_detail}."
        )

    def generate_return_po_detail(
        self,
        po: str,
        base_detail: str = "10010",
        exclude_details: Sequence[str] = (),
    ) -> str:
        """Generate a return detail by incrementing D2 on the scanned branch.

        Returning preserves D1 and D3-D5 from the scanned label.  Thus
        ``10010`` becomes ``11010``, ``20010`` becomes ``21010``, and a
        later return of ``11010`` becomes ``12010``.

        Raises
        ------
        PORegistryError
            If all 9 return detail slots (11010 through 91010) have been exhausted for the given PO.
        """
        base_detail = self._normalize_operation_detail(base_detail)
        d1 = base_detail[0]
        suffix = base_detail[2:]
        current_d2 = int(base_detail[1])
        used = set(self.get_used_po_details(po)) | set(exclude_details)
        for d2 in range(current_d2 + 1, 10):
            candidate = f"{d1}{d2}{suffix}"
            if candidate not in used:
                return candidate
        raise PORegistryError(
            f"Đã đạt giới hạn tối đa 9 lần hoàn kho cho nhánh mã chi tiết "
            f"{base_detail} của PO {po}."
        )

    @staticmethod
    def _normalize_operation_detail(base_detail: str) -> str:
        """Validate an EDI five-digit PO detail before deriving a new one."""
        detail = (base_detail or "00010").strip().zfill(5)
        if len(detail) != 5 or not detail.isdigit():
            raise PORegistryError(
                f"Mã PO chi tiết phải gồm đúng 5 chữ số, nhận được: {base_detail!r}."
            )
        return detail

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def count_registered(self) -> int:
        """Return the total number of registered combos."""
        return self._execute_with_auto_recovery(
            lambda: (self._conn.execute("SELECT COUNT(*) FROM po_registry").fetchone() or [0])[0]
        )

    def current_nn(self, target_date: date | None = None) -> int:
        """Return the current (next available) NN for *target_date*."""
        if target_date is None:
            target_date = datetime.now().date()
        date_key = target_date.strftime("%Y%m%d")
        return self._execute_with_auto_recovery(
            lambda: (
                self._conn.execute(
                    "SELECT next_nn FROM po_sequence WHERE date_key = ?",
                    (date_key,),
                ).fetchone()
                or [1]
            )[0]
        )

    def fetch_history(self, search: str = "", limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
        """Fetch history records from po_registry with optional search filter."""
        return self._execute_with_auto_recovery(
            lambda: self._fetch_history_impl(search, limit, offset)
        )

    def _fetch_history_impl(self, search: str = "", limit: int = 500, offset: int = 0) -> list[dict[str, Any]]:
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
