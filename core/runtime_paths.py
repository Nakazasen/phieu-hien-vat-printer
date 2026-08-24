"""Runtime paths and data migration for In Phiếu Hiện Vật.

Application binaries are disposable release assets.  User state lives outside
the executable directory so an installer or a versioned updater can replace
the app without overwriting PO history, layout changes, or generated PDFs.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

APP_FOLDER_NAME = "InPhieuHienVat"
DATA_FOLDER_NAME = "InPhieuHienVatData"
ENV_DATA_ROOT = "INPHIEUHIENVAT_DATA_DIR"
ENV_OUTPUT_ROOT = "INPHIEUHIENVAT_OUTPUT_DIR"
ENV_REGISTRY_PATH = "INPHIEUHIENVAT_REGISTRY_PATH"
SHARED_REGISTRY_DIR = r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\db"


@dataclass(frozen=True)
class RuntimePaths:
    """Resolved immutable application assets and mutable user-data paths."""

    bundle_dir: Path
    installation_dir: Path
    data_dir: Path
    output_dir: Path
    template_path: Path
    layout_path: Path
    registry_path: Path


AppPaths = RuntimePaths



def bundle_dir() -> Path:
    """Return the directory holding immutable assets for the running app."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def installation_dir() -> Path:
    """Return the executable directory, or the project directory in source mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _local_app_data() -> Path:
    configured = os.environ.get(ENV_DATA_ROOT, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data).expanduser() / DATA_FOLDER_NAME
    return Path.home() / "AppData" / "Local" / DATA_FOLDER_NAME


def _documents_output() -> Path:
    configured = os.environ.get(ENV_OUTPUT_ROOT, "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / "Documents" / APP_FOLDER_NAME / "output"


def _copy_if_missing(source: Path, destination: Path) -> None:
    if destination.exists() or not source.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _migrate_registry_if_needed(source: Path, destination: Path) -> None:
    """Copy a legacy SQLite database using SQLite's backup API.

    The registry uses WAL mode.  Copying only the main database file can omit
    committed pages still stored in ``-wal``; ``Connection.backup`` produces a
    consistent snapshot instead.
    """
    if destination.exists() or not source.is_file() or source.resolve() == destination.resolve():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    legacy: sqlite3.Connection | None = None
    migrated: sqlite3.Connection | None = None
    try:
        legacy = sqlite3.connect(source)
        migrated = sqlite3.connect(destination)
        legacy.backup(migrated)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        if migrated is not None:
            migrated.close()
        if legacy is not None:
            legacy.close()


def _resolve_registry_path(data_dir: Path) -> Path:
    """Resolve PO registry path with env overrides and safe network share fallback.

    Priority:
    1. INPHIEUHIENVAT_REGISTRY_PATH environment variable (explicit file path).
    2. INPHIEUHIENVAT_DATA_DIR environment variable (isolated test data dir).
    3. Shared network directory (\\\\fstvn01\\Data\\...).
    4. Local application data directory (fallback when network share is unreachable).
    """
    configured_file = os.environ.get(ENV_REGISTRY_PATH, "").strip()
    if configured_file:
        return Path(configured_file).expanduser().resolve()

    configured_data_dir = os.environ.get(ENV_DATA_ROOT, "").strip()
    if configured_data_dir:
        return data_dir / "po_registry.db"

    shared_dir = Path(SHARED_REGISTRY_DIR)
    try:
        shared_dir.mkdir(parents=True, exist_ok=True)
        return shared_dir / "po_registry.db"
    except (OSError, PermissionError):
        return data_dir / "po_registry.db"


def prepare_runtime_paths() -> RuntimePaths:
    """Create user-data locations and migrate legacy portable state once."""
    assets = bundle_dir()
    install = installation_dir()
    data = _local_app_data()
    output = _documents_output()
    data.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)

    template = assets / "template.pdf"
    if not template.is_file():
        raise FileNotFoundError(f"Không tìm thấy template.pdf trong bundle: {template}")

    layout = data / "layout_config.json"
    _copy_if_missing(install / "layout_config.json", layout)
    _copy_if_missing(assets / "layout_config.json", layout)

    registry = _resolve_registry_path(data)
    _migrate_registry_if_needed(install / "po_registry.db", registry)

    return RuntimePaths(
        bundle_dir=assets,
        installation_dir=install,
        data_dir=data,
        output_dir=output,
        template_path=template,
        layout_path=layout,
        registry_path=registry,
    )
