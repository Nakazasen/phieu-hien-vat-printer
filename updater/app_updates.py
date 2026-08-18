"""Stage, verify, activate, and roll back versioned application updates."""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from core.runtime_paths import RuntimePaths
from updater.update_security import (
    ArtifactVerificationError,
    canonical_json_bytes,
    read_package_manifest,
    safe_extract_package,
    sha256_file,
    verify_manifest_files,
)

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class ApplicationUpdateError(ArtifactVerificationError):
    """Raised when an application update cannot be safely activated."""


def _version(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(str(value))
    if not match:
        raise ApplicationUpdateError(f"Version không hợp lệ: {value}")
    return tuple(int(part) for part in match.groups())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationUpdateError(f"Không đọc được file trạng thái: {path}") from exc
    if not isinstance(value, dict):
        raise ApplicationUpdateError(f"File trạng thái không hợp lệ: {path}")
    return value


def _write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(canonical_json_bytes(value))
    os.replace(temporary, path)


def application_install_root(application_dir: str | os.PathLike[str]) -> Path:
    """Resolve ``<install>/apps/<version>`` to the stable launcher root."""
    version_dir = Path(application_dir).resolve()
    if version_dir.parent.name.casefold() != "apps" or not SEMVER.fullmatch(version_dir.name):
        raise ApplicationUpdateError("Auto-update chỉ chạy từ bản cài versioned qua launcher")
    return version_dir.parent.parent


def inspect_update_package(package_path: str | os.PathLike[str], *, current_version: str) -> dict[str, Any]:
    manifest = read_package_manifest(package_path)
    if _version(manifest["version"]) <= _version(current_version):
        raise ApplicationUpdateError("Package update phải mới hơn version đang chạy")
    if _version(current_version) < _version(manifest["min_app_version"]):
        raise ApplicationUpdateError("Package update yêu cầu version cũ mới hơn")
    return manifest


def stage_update(package_path: str | os.PathLike[str], app_root: str | os.PathLike[str], *, current_version: str) -> Path:
    manifest = inspect_update_package(package_path, current_version=current_version)
    root = Path(app_root).resolve()
    destination = root / "apps" / manifest["version"]
    if destination.exists():
        raise ApplicationUpdateError(f"Version đã tồn tại: {manifest['version']}")
    staging_root = root / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="update-", dir=staging_root))
    staged = temporary / "app"
    try:
        safe_extract_package(package_path, staged)
        destination.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    shutil.rmtree(temporary, ignore_errors=True)
    return destination


def _run_health_check(version_dir: Path, manifest: dict[str, Any], paths: RuntimePaths) -> None:
    executable = (version_dir / manifest["entrypoint"]).resolve()
    if version_dir.resolve() not in executable.parents or not executable.is_file():
        raise ApplicationUpdateError("Không tìm thấy executable để health-check")
    environment = os.environ.copy()
    environment["INPHIEUHIENVAT_DATA_DIR"] = str(paths.data_dir)
    environment["INPHIEUHIENVAT_OUTPUT_DIR"] = str(paths.output_dir)
    try:
        subprocess.run([str(executable), "--health-check"], check=True, cwd=str(version_dir), env=environment, timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ApplicationUpdateError("Version mới không vượt qua health-check") from exc


def backup_runtime_state(paths: RuntimePaths, backup_root: Path, *, target_version: str) -> Path:
    destination = backup_root / f"before-{target_version}"
    if destination.exists():
        raise ApplicationUpdateError(f"Backup đã tồn tại: {destination}")
    destination.mkdir(parents=True)
    copied: list[dict[str, Any]] = []
    try:
        if paths.registry_path.is_file():
            target_db = destination / "po_registry.db"
            source_db: sqlite3.Connection | None = None
            target_db_connection: sqlite3.Connection | None = None
            try:
                source_db = sqlite3.connect(paths.registry_path)
                target_db_connection = sqlite3.connect(target_db)
                source_db.backup(target_db_connection)
            finally:
                if target_db_connection is not None:
                    target_db_connection.close()
                if source_db is not None:
                    source_db.close()
            copied.append({"path": target_db.name, "sha256": sha256_file(target_db), "size": target_db.stat().st_size})
        for source in (paths.layout_path,):
            if source.is_file():
                target = destination / source.name
                shutil.copy2(source, target)
                copied.append({"path": target.name, "sha256": sha256_file(target), "size": target.stat().st_size})
        (destination / "backup.json").write_bytes(canonical_json_bytes({"schema": 1, "target_version": target_version, "files": copied}))
        return destination
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise


def activate_staged_update(app_root: str | os.PathLike[str], version: str, paths: RuntimePaths) -> dict[str, Any]:
    root = Path(app_root).resolve()
    version_dir = root / "apps" / version
    manifest = _read_json(version_dir / "manifest.json")
    if manifest.get("version") != version:
        raise ApplicationUpdateError("Manifest không khớp version staging")
    verify_manifest_files(manifest, version_dir)
    _run_health_check(version_dir, manifest, paths)
    backup_runtime_state(paths, root / "backups", target_version=version)
    current_path = root / "current.json"
    if current_path.is_file():
        _write_json_atomic(root / "previous.json", _read_json(current_path))
    state = {
        "schema": 1,
        "version": version,
        "entrypoint": manifest["entrypoint"],
        "manifest_sha256": sha256_file(version_dir / "manifest.json"),
    }
    _write_json_atomic(current_path, state)
    return state


def install_update(package_path: str | os.PathLike[str], app_root: str | os.PathLike[str], paths: RuntimePaths, *, current_version: str) -> dict[str, Any]:
    staged: Path | None = None
    try:
        staged = stage_update(package_path, app_root, current_version=current_version)
        return activate_staged_update(app_root, staged.name, paths)
    except Exception as exc:
        if staged is not None:
            shutil.rmtree(staged, ignore_errors=True)
        if isinstance(exc, ApplicationUpdateError):
            raise
        raise ApplicationUpdateError("Cài update không thành công") from exc


def rollback_update(app_root: str | os.PathLike[str]) -> dict[str, Any]:
    root = Path(app_root).resolve()
    current = _read_json(root / "current.json")
    previous = _read_json(root / "previous.json")
    version_dir = root / "apps" / str(previous.get("version", ""))
    entrypoint = (version_dir / str(previous.get("entrypoint", ""))).resolve()
    if version_dir.resolve() not in entrypoint.parents or not entrypoint.is_file():
        raise ApplicationUpdateError("Version trước đó không còn executable để rollback")
    _write_json_atomic(root / "current.json", previous)
    _write_json_atomic(root / "previous.json", current)
    return previous


def launch_activated_update(app_root: str | os.PathLike[str], *, current_pid: int | None = None) -> Path:
    """Start the active version after the current process exits."""
    root = Path(app_root).resolve()
    state = _read_json(root / "current.json")
    version_dir = root / "apps" / str(state.get("version", ""))
    entrypoint = (version_dir / str(state.get("entrypoint", ""))).resolve()
    if version_dir.resolve() not in entrypoint.parents or not entrypoint.is_file():
        raise ApplicationUpdateError("Không tìm thấy executable version mới để khởi động")
    pid = int(current_pid if current_pid is not None else os.getpid())
    if pid <= 0:
        raise ApplicationUpdateError("PID hiện tại không hợp lệ")
    try:
        subprocess.Popen([str(entrypoint), "--wait-for-pid", str(pid)], cwd=str(entrypoint.parent), close_fds=True)
    except OSError as exc:
        raise ApplicationUpdateError("Không thể khởi động version mới") from exc
    return entrypoint
