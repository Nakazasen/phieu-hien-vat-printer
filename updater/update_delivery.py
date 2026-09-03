"""Discover and cache hash-checked updates from configured LAN folders."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.runtime_paths import RuntimePaths
from updater.update_security import MAX_ARTIFACT_BYTES, sha256_file

CONFIG_SCHEMA = 1
CATALOG_SCHEMA = 1
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
PACKAGE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.phieuupdate$", re.IGNORECASE)
SOURCE_DISCOVERY_TIMEOUT_SECONDS = 2.0


class UpdateDeliveryError(ValueError):
    """Raised when an update source or its catalog is invalid."""


@dataclass(frozen=True)
class UpdateCandidate:
    version: str
    package_path: Path
    size: int
    sha256: str
    notes: str


def _version(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(str(value))
    if not match:
        raise UpdateDeliveryError(f"Version catalog không hợp lệ: {value}")
    return tuple(int(part) for part in match.groups())


def _read_json(path: Path, *, max_bytes: int = 256 * 1024) -> Any:
    try:
        if path.stat().st_size > max_bytes:
            raise UpdateDeliveryError(f"File cấu hình quá lớn: {path}")
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UpdateDeliveryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise UpdateDeliveryError(f"Không đọc được JSON: {path}") from exc


def validate_update_config(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema", "startup_check", "sources"}:
        raise UpdateDeliveryError("Cấu hình nguồn update không đúng schema")
    if value["schema"] != CONFIG_SCHEMA or not isinstance(value["startup_check"], bool) or not isinstance(value["sources"], list):
        raise UpdateDeliveryError("Cấu hình nguồn update không hợp lệ")
    sources: list[dict[str, object]] = []
    for item in value["sources"]:
        if not isinstance(item, dict) or set(item) != {"type", "location", "enabled"}:
            raise UpdateDeliveryError("Nguồn update không đúng schema")
        if item["type"] != "folder" or not isinstance(item["location"], str) or not item["location"].strip() or not isinstance(item["enabled"], bool):
            raise UpdateDeliveryError("Chỉ hỗ trợ nguồn update folder hợp lệ")
        sources.append({"type": "folder", "location": item["location"].strip(), "enabled": item["enabled"]})
    return {"schema": CONFIG_SCHEMA, "startup_check": value["startup_check"], "sources": sources}


def company_policy_config_path() -> Path:
    program_data = os.environ.get("PROGRAMDATA", "").strip()
    if program_data:
        return Path(program_data) / "InPhieuHienVat" / "update_sources.json"
    return Path(r"C:\ProgramData\InPhieuHienVat\update_sources.json")


def load_update_config(paths: RuntimePaths) -> dict[str, Any]:
    default_path = paths.bundle_dir / "update_sources.default.json"
    selected = validate_update_config(_read_json(default_path))
    override = paths.data_dir / "update_sources.json"
    if override.is_file():
        selected = validate_update_config(_read_json(override))
    policy = company_policy_config_path()
    if policy.is_file():
        selected = validate_update_config(_read_json(policy))
    return selected



def current_release_version(paths: RuntimePaths) -> str:
    metadata = _read_json(paths.bundle_dir / "release.json")
    version = str(metadata.get("version", ""))
    _version(version)
    return version


def save_update_config(paths: RuntimePaths, value: Any) -> Path:
    config = validate_update_config(value)
    destination = paths.data_dir / "update_sources.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return destination


def _catalog(value: Any) -> tuple[str, str, int, str, str]:
    required = {"schema", "channel", "version", "package", "sha256", "size", "notes"}
    if not isinstance(value, dict) or set(value) != required or value["schema"] != CATALOG_SCHEMA:
        raise UpdateDeliveryError("latest.json không đúng schema")
    package = value["package"]
    version = str(value["version"])
    digest = value["sha256"]
    size = value["size"]
    notes = value["notes"]
    _version(version)
    if not isinstance(package, str) or not PACKAGE_NAME.fullmatch(package):
        raise UpdateDeliveryError("Tên package trong latest.json không an toàn")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest.casefold()):
        raise UpdateDeliveryError("SHA-256 trong latest.json không hợp lệ")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_ARTIFACT_BYTES:
        raise UpdateDeliveryError("Kích thước package trong latest.json không hợp lệ")
    if not isinstance(value["channel"], str) or not isinstance(notes, str) or len(notes) > 2000:
        raise UpdateDeliveryError("Channel hoặc release note không hợp lệ")
    return package, version, size, digest.casefold(), notes


def _discover_from_folder(folder: Path, current_version: str) -> UpdateCandidate | None:
    """Return a newer catalog candidate without hashing its full package.

    Discovery runs every time the application starts.  Hashing a large update
    package over a LAN share here can exceed the probe timeout and hide a real
    update.  ``fetch_update`` performs the full SHA-256 comparison after the
    user accepts the update and before any staging or activation can occur.
    """
    package_name, version, size, digest, notes = _catalog(_read_json(folder / "latest.json"))
    package = folder / package_name
    if package.is_file() and package.stat().st_size == size and _version(version) > _version(current_version):
        return UpdateCandidate(version=version, package_path=package, size=size, sha256=digest, notes=notes)
    return None


def _discover_from_folder_with_timeout(folder: Path, current_version: str) -> UpdateCandidate | None:
    """Bound a potentially stalled UNC probe without blocking the UI worker."""
    result: list[UpdateCandidate | None] = []
    completed = threading.Event()

    def probe() -> None:
        try:
            result.append(_discover_from_folder(folder, current_version))
        except (OSError, UpdateDeliveryError):
            result.append(None)
        finally:
            completed.set()

    threading.Thread(target=probe, daemon=True, name="inphieuhienvat-update-probe").start()
    if not completed.wait(SOURCE_DISCOVERY_TIMEOUT_SECONDS):
        return None
    return result[0] if result else None


def discover_update(paths: RuntimePaths, *, current_version: str) -> UpdateCandidate | None:
    config = load_update_config(paths)
    candidates: list[UpdateCandidate] = []
    for source in config["sources"]:
        if not source["enabled"]:
            continue
        candidate = _discover_from_folder_with_timeout(
            Path(str(source["location"])).expanduser(),
            current_version,
        )
        if candidate is not None:
            candidates.append(candidate)
    return max(candidates, key=lambda item: _version(item.version), default=None)


def fetch_update(paths: RuntimePaths, candidate: UpdateCandidate) -> Path:
    cache = paths.data_dir / ".updates" / "downloads"
    cache.mkdir(parents=True, exist_ok=True)
    destination = cache / f"InPhieuHienVat-{candidate.version}.phieuupdate"
    descriptor, temporary_name = tempfile.mkstemp(prefix="download-", suffix=".tmp", dir=cache)
    os.close(descriptor)
    temporary = Path(temporary_name)
    copied = 0
    try:
        with candidate.package_path.open("rb") as source, temporary.open("wb") as target:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                copied += len(block)
                if copied > MAX_ARTIFACT_BYTES:
                    raise UpdateDeliveryError("Package tải về vượt giới hạn dung lượng")
                target.write(block)
        if copied != candidate.size or sha256_file(temporary) != candidate.sha256:
            raise UpdateDeliveryError("Hash hoặc kích thước package tải về không khớp latest.json")
        os.replace(temporary, destination)
        return destination
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
