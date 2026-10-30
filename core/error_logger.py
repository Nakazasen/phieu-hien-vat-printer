"""Centralized error and diagnostic logger for In Phiếu Hiện Vật.

Writes detailed diagnostic logs to:
1. LAN shared error_log directory:
   \\\\fstvn01\\Data\\00_KDTVN Common(KDTVN共通)\\⑤Production Engineering(製造技術)\\Hang muc can luu\\Vinh\\PMintemEDI\\error_log
2. Local fallback directory (%LOCALAPPDATA%\\InPhieuHienVat\\error_log)
"""

from __future__ import annotations

from datetime import datetime
import getpass
import json
import os
from pathlib import Path
import re
import socket
import threading
import time
import traceback
from typing import Any

DEFAULT_LAN_ERROR_LOG_DIR = (
    r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)"
    r"\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\error_log"
)
ENV_ERROR_LOG_DIR = "INPHIEUHIENVAT_ERROR_LOG_DIR"
ENV_MAX_LOG_DIR_BYTES = "INPHIEUHIENVAT_MAX_LOG_DIR_BYTES"
DEFAULT_MAX_LOG_DIR_BYTES = 500 * 1024 * 1024  # 500 MB

_LOG_LOCK = threading.Lock()
_RECENT_EVENTS: dict[tuple[str, str, str], float] = {}
_DEDUP_WINDOW_SECONDS = 2.0
_LAST_QUOTA_CHECK_BY_DIR: dict[str, float] = {}
_QUOTA_CHECK_INTERVAL_SECONDS = 30.0
_FILENAME_DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2}|20\d{2}-\d{2})")


def _is_unconfigured_pytest_run() -> bool:
    """Return True if running inside pytest without an explicit test log directory override."""
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    env_dir = os.environ.get(ENV_ERROR_LOG_DIR, "").strip()
    return not bool(env_dir)


def get_lan_error_log_dir() -> Path:
    """Return the configured LAN error_log directory path."""
    env_dir = os.environ.get(ENV_ERROR_LOG_DIR, "").strip().strip('"').strip("'")
    if env_dir:
        return Path(env_dir)
    return Path(DEFAULT_LAN_ERROR_LOG_DIR)


def get_local_fallback_log_dir() -> Path:
    """Return local fallback error_log directory inside LOCALAPPDATA."""
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / "InPhieuHienVat" / "error_log"
    return Path.home() / ".inphieuhienvat" / "error_log"


def _format_readable_entry(record: dict[str, Any]) -> str:
    lines = [
        "=" * 88,
        f"[{record.get('timestamp', '')}] [{record.get('event_type', 'ERROR')}] "
        f"Host={record.get('hostname', '')} | User={record.get('username', '')} | "
        f"AppVer={record.get('app_version', '')}",
        f"Message: {record.get('message', '')}",
    ]
    if record.get("item_code"):
        lines.append(f"Item Code: {record.get('item_code')}")
    if record.get("csv_path"):
        lines.append(f"CSV Path : {record.get('csv_path')}")
    if record.get("diagnostics"):
        try:
            diag_str = json.dumps(record["diagnostics"], ensure_ascii=False, indent=2)
        except Exception:
            diag_str = str(record["diagnostics"])
        lines.append(f"Diagnostics:\n{diag_str}")
    if record.get("traceback"):
        lines.append(f"Traceback:\n{record['traceback'].rstrip()}")
    lines.append("=" * 88 + "\n")
    return "\n".join(lines)


def _resolve_effective_max_log_bytes(max_bytes: int | None = None) -> int:
    if max_bytes is not None and max_bytes > 0:
        return int(max_bytes)
    raw_env = os.environ.get(ENV_MAX_LOG_DIR_BYTES, "").strip()
    if raw_env:
        try:
            parsed = int(raw_env)
            if parsed > 0:
                return parsed
        except ValueError:
            pass
    return DEFAULT_MAX_LOG_DIR_BYTES


def _extract_file_date_tag(file_path: Path, mtime: float) -> str:
    """Return a YYYY-MM-DD date tag for a log file based on its filename or modification time."""
    match = _FILENAME_DATE_RE.search(file_path.name)
    if match:
        token = match.group(1)
        if len(token) == 7:
            return f"{token}-01"
        return token
    try:
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return datetime.now().strftime("%Y-%m-%d")


def _enforce_log_dir_quota_unlocked(
    log_dir: Path,
    max_bytes: int | None = None,
) -> dict[str, Any] | None:
    """Enforce directory size quota by deleting oldest daily log files when total size exceeds max_bytes."""
    effective_max = _resolve_effective_max_log_bytes(max_bytes)
    try:
        if not log_dir.is_dir():
            return None
        entries: list[tuple[Path, int, float, str]] = []
        total_bytes = 0
        for child in log_dir.iterdir():
            if not child.is_file():
                continue
            if child.suffix.lower() not in (".jsonl", ".log"):
                continue
            try:
                st = child.stat()
            except OSError:
                continue
            f_size = int(st.st_size)
            f_mtime = float(st.st_mtime)
            f_date = _extract_file_date_tag(child, f_mtime)
            entries.append((child, f_size, f_mtime, f_date))
            total_bytes += f_size
    except OSError:
        return None

    if total_bytes <= effective_max:
        return None

    target_bytes = int(effective_max * 0.85) if effective_max >= 4096 else effective_max
    today_tag = datetime.now().strftime("%Y-%m-%d")

    # Prioritize deleting dated files older than today first, sorted oldest-first by (date_tag, mtime, name)
    def _sort_key(item: tuple[Path, int, float, str]) -> tuple[int, str, float, str]:
        p, _sz, mt, dt = item
        is_rolling_main = 1 if p.name == "error_log_readable.log" else 0
        is_today = 1 if dt == today_tag else 0
        return (is_rolling_main, is_today, dt, mt, p.name)

    entries.sort(key=_sort_key)

    deleted_names: list[str] = []
    deleted_dates: list[str] = []
    freed_bytes = 0
    current_bytes = total_bytes

    for file_path, f_size, _f_mtime, f_date in entries:
        if current_bytes <= target_bytes:
            break
        if file_path.name == "error_log_readable.log":
            # Truncate rolling readable log to keep newest tail if it alone forces directory over quota
            keep_tail = max(1024, target_bytes // 2)
            if f_size > keep_tail:
                try:
                    raw = file_path.read_bytes()
                    trimmed = raw[-keep_tail:]
                    nl_pos = trimmed.find(b"\n")
                    if nl_pos != -1 and nl_pos + 1 < len(trimmed):
                        trimmed = trimmed[nl_pos + 1 :]
                    file_path.write_bytes(trimmed)
                    saved = max(0, f_size - len(trimmed))
                    freed_bytes += saved
                    current_bytes -= saved
                    deleted_names.append(f"{file_path.name} (trimmed)")
                    deleted_dates.append(f_date)
                except OSError:
                    pass
            continue
        try:
            file_path.unlink()
            deleted_names.append(file_path.name)
            deleted_dates.append(f_date)
            freed_bytes += f_size
            current_bytes -= f_size
        except OSError:
            continue

    if not deleted_names:
        return None

    start_date = min(deleted_dates) if deleted_dates else today_tag
    end_date = max(deleted_dates) if deleted_dates else today_tag
    freed_mb = freed_bytes / (1024 * 1024)
    max_mb = effective_max / (1024 * 1024)

    summary: dict[str, Any] = {
        "deleted_files": deleted_names,
        "deleted_count": len(deleted_names),
        "freed_bytes": freed_bytes,
        "start_date": start_date,
        "end_date": end_date,
        "remaining_bytes": max(0, current_bytes),
        "max_bytes": effective_max,
    }

    cleanup_record: dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": "LOG_QUOTA_CLEANUP",
        "hostname": socket.gethostname(),
        "username": getpass.getuser(),
        "app_version": "",
        "item_code": "",
        "csv_path": "",
        "message": (
            f"Đã tự động dọn dẹp {len(deleted_names)} tệp log cũ "
            f"(từ ngày {start_date} đến ngày {end_date}), "
            f"giải phóng {freed_mb:.2f} MB (ngưỡng tối đa: {max_mb:.2f} MB)."
        ),
        "diagnostics": summary,
        "traceback": "",
    }
    try:
        cleanup_jsonl = json.dumps(cleanup_record, ensure_ascii=False) + "\n"
        cleanup_txt = _format_readable_entry(cleanup_record)
        with (log_dir / f"error_log_{today_tag}.jsonl").open("a", encoding="utf-8") as f_j:
            f_j.write(cleanup_jsonl)
        with (log_dir / f"error_log_readable_{today_tag}.log").open("a", encoding="utf-8") as f_t:
            f_t.write(cleanup_txt)
        with (log_dir / "error_log_readable.log").open("a", encoding="utf-8") as f_r:
            f_r.write(cleanup_txt)
    except Exception:  # noqa: BLE001
        pass

    return summary


def enforce_log_dir_quota(
    log_dir: Path | str | None = None,
    max_bytes: int | None = None,
) -> dict[str, Any] | None:
    """Public helper to check and enforce the log directory size quota (default 500 MB)."""
    target_dir = Path(log_dir) if log_dir is not None else get_lan_error_log_dir()
    with _LOG_LOCK:
        return _enforce_log_dir_quota_unlocked(target_dir, max_bytes=max_bytes)


def _write_log_sync(record: dict[str, Any]) -> None:
    if _is_unconfigured_pytest_run():
        return

    ts_str = str(record.get("timestamp", "")).strip()
    if len(ts_str) >= 10 and ts_str[4:5] == "-" and ts_str[7:8] == "-":
        date_tag = ts_str[:10]
    else:
        date_tag = datetime.now().strftime("%Y-%m-%d")
    month_tag = date_tag[:7]
    jsonl_line = json.dumps(record, ensure_ascii=False) + "\n"
    readable_block = _format_readable_entry(record)

    env_override = os.environ.get(ENV_ERROR_LOG_DIR, "").strip()
    if env_override and os.environ.get("PYTEST_CURRENT_TEST"):
        target_dirs = [get_lan_error_log_dir()]
    else:
        target_dirs = [get_lan_error_log_dir(), get_local_fallback_log_dir()]

    now_mono = time.monotonic()
    force_quota_check = bool(os.environ.get(ENV_MAX_LOG_DIR_BYTES, "").strip())

    with _LOG_LOCK:
        for log_dir in target_dirs:
            try:
                log_dir.mkdir(parents=True, exist_ok=True)
                daily_jsonl = log_dir / f"error_log_{date_tag}.jsonl"
                daily_readable = log_dir / f"error_log_readable_{date_tag}.log"
                monthly_jsonl = log_dir / f"error_log_{month_tag}.jsonl"
                rolling_readable = log_dir / "error_log_readable.log"

                with daily_jsonl.open("a", encoding="utf-8") as f_dj:
                    f_dj.write(jsonl_line)
                with daily_readable.open("a", encoding="utf-8") as f_dr:
                    f_dr.write(readable_block)
                with monthly_jsonl.open("a", encoding="utf-8") as f_mj:
                    f_mj.write(jsonl_line)
                with rolling_readable.open("a", encoding="utf-8") as f_rr:
                    f_rr.write(readable_block)

                dir_key = str(log_dir)
                last_check = _LAST_QUOTA_CHECK_BY_DIR.get(dir_key, 0.0)
                if force_quota_check or (now_mono - last_check) >= _QUOTA_CHECK_INTERVAL_SECONDS:
                    _LAST_QUOTA_CHECK_BY_DIR[dir_key] = now_mono
                    _enforce_log_dir_quota_unlocked(log_dir)
            except Exception:  # noqa: BLE001
                continue


def log_error_event(
    event_type: str,
    message: str,
    *,
    item_code: str = "",
    csv_path: str | Path | None = None,
    diagnostics: dict[str, Any] | None = None,
    error: BaseException | None = None,
    app_version: str = "",
    async_write: bool = True,
) -> None:
    """Record a diagnostic/error event to the centralized LAN error_log folder and local fallback."""
    if _is_unconfigured_pytest_run():
        return

    clean_item = str(item_code or "").strip().upper()
    clean_msg = str(message or "")
    dedup_key = (str(event_type or ""), clean_item, clean_msg)
    now_mono = time.monotonic()

    with _LOG_LOCK:
        last_seen = _RECENT_EVENTS.get(dedup_key)
        if last_seen is not None and (now_mono - last_seen) < _DEDUP_WINDOW_SECONDS:
            return
        _RECENT_EVENTS[dedup_key] = now_mono
        if len(_RECENT_EVENTS) > 256:
            cutoff = now_mono - (_DEDUP_WINDOW_SECONDS * 2)
            stale_keys = [k for k, ts in _RECENT_EVENTS.items() if ts < cutoff]
            for k in stale_keys:
                _RECENT_EVENTS.pop(k, None)

    try:
        hostname = socket.gethostname()
    except Exception:  # noqa: BLE001
        hostname = "unknown-host"

    try:
        username = getpass.getuser()
    except Exception:  # noqa: BLE001
        username = "unknown-user"

    tb_text = ""
    if error is not None:
        try:
            tb_text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        except Exception:  # noqa: BLE001
            tb_text = repr(error)

    record: dict[str, Any] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event_type": event_type,
        "hostname": hostname,
        "username": username,
        "app_version": app_version,
        "item_code": str(item_code or ""),
        "csv_path": str(csv_path) if csv_path is not None else "",
        "message": str(message or ""),
        "diagnostics": diagnostics or {},
        "traceback": tb_text,
    }

    if async_write:
        threading.Thread(target=_write_log_sync, args=(record,), daemon=True).start()
    else:
        _write_log_sync(record)
