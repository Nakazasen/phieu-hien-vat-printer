"""Shared integrity checks for In Phiếu Hiện Vật update packages."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

MANIFEST_SCHEMA = 1
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_ARTIFACT_BYTES = 512 * 1024 * 1024


class ArtifactVerificationError(ValueError):
    """Raised when an update artifact is malformed, incomplete, or unsafe."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative_path(raw_path: str) -> str:
    normalized = str(raw_path).replace("\\", "/")
    if not normalized or normalized.startswith("./") or normalized.startswith("."):
        raise ArtifactVerificationError(f"Đường dẫn package không hợp lệ: {raw_path}")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ":" in pure.parts[0] or ".." in pure.parts:
        raise ArtifactVerificationError(f"Đường dẫn package không an toàn: {raw_path}")
    segments = normalized.split("/")
    if any(seg in {"", "."} or seg.startswith(".") for seg in segments):
        raise ArtifactVerificationError(f"Đường dẫn package không hợp lệ: {raw_path}")
    if any(part in {"", "."} or part.startswith(".") for part in pure.parts):
        raise ArtifactVerificationError(f"Đường dẫn package không hợp lệ: {raw_path}")
    return pure.as_posix()


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {"schema", "kind", "id", "version", "min_app_version", "entrypoint", "files"}
    if not isinstance(manifest, dict) or set(manifest) != required or manifest.get("schema") != MANIFEST_SCHEMA:
        raise ArtifactVerificationError("Manifest update không đúng schema")
    if manifest.get("kind") != "application" or manifest.get("id") != "InPhieuHienVat":
        raise ArtifactVerificationError("Manifest không phải package In Phiếu Hiện Vật")
    if not all(isinstance(manifest.get(key), str) and manifest[key].strip() for key in ("version", "min_app_version", "entrypoint")):
        raise ArtifactVerificationError("Manifest thiếu version hoặc entrypoint")
    entrypoint = safe_relative_path(manifest["entrypoint"])
    if not entrypoint.casefold().endswith(".exe"):
        raise ArtifactVerificationError("Entrypoint update phải là .exe")
    files = manifest["files"]
    if not isinstance(files, list) or not files:
        raise ArtifactVerificationError("Manifest phải có danh sách file")
    paths: set[str] = set()
    total_size = 0
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size"}:
            raise ArtifactVerificationError("Mỗi file manifest phải có path, sha256 và size")
        path = safe_relative_path(item["path"])
        if path in paths:
            raise ArtifactVerificationError(f"Manifest có file trùng: {path}")
        paths.add(path)
        digest = item["sha256"]
        size = item["size"]
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest.casefold()):
            raise ArtifactVerificationError(f"SHA-256 không hợp lệ: {path}")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0 or size > MAX_ARTIFACT_BYTES:
            raise ArtifactVerificationError(f"Kích thước không hợp lệ: {path}")
        total_size += size
        if total_size > MAX_ARTIFACT_BYTES:
            raise ArtifactVerificationError("Package update vượt giới hạn dung lượng")
    if entrypoint not in paths:
        raise ArtifactVerificationError("Entrypoint không nằm trong danh sách file manifest")


def verify_manifest_files(manifest: dict[str, Any], root: str | os.PathLike[str]) -> None:
    validate_manifest(manifest)
    base = Path(root).resolve()
    for item in manifest["files"]:
        relative = safe_relative_path(item["path"])
        path = (base / Path(relative)).resolve()
        if base not in path.parents or not path.is_file():
            raise ArtifactVerificationError(f"Thiếu file được manifest khai báo: {relative}")
        if path.stat().st_size != item["size"] or sha256_file(path) != item["sha256"].casefold():
            raise ArtifactVerificationError(f"Hash hoặc kích thước không khớp: {relative}")


def read_package_manifest(package_path: str | os.PathLike[str]) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(package_path) as archive:
            info = archive.getinfo("manifest.json")
            if info.file_size > MAX_MANIFEST_BYTES:
                raise ArtifactVerificationError("manifest.json vượt giới hạn")
            manifest = json.loads(archive.read(info).decode("utf-8-sig"))
            if not isinstance(manifest, dict):
                raise ArtifactVerificationError("manifest.json không phải object")
            validate_manifest(manifest)
            expected = {"manifest.json", *(safe_relative_path(item["path"]) for item in manifest["files"])}
            actual = {info.filename.replace("\\", "/") for info in archive.infolist() if not info.is_dir()}
            if actual != expected:
                raise ArtifactVerificationError("Package có file thừa hoặc thiếu so với manifest")
            return manifest
    except ArtifactVerificationError:
        raise
    except (OSError, KeyError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise ArtifactVerificationError("Không đọc được package update hợp lệ") from exc


def safe_extract_package(package_path: str | os.PathLike[str], destination: str | os.PathLike[str]) -> None:
    manifest = read_package_manifest(package_path)
    target = Path(destination).resolve()
    target.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(package_path) as archive:
            total_size = 0
            for item in manifest["files"]:
                relative = safe_relative_path(item["path"])
                info = archive.getinfo(relative)
                total_size += info.file_size
                if info.file_size != item["size"] or total_size > MAX_ARTIFACT_BYTES:
                    raise ArtifactVerificationError("Kích thước package không hợp lệ")
                output = (target / Path(relative)).resolve()
                if target not in output.parents:
                    raise ArtifactVerificationError(f"File update vượt ngoài staging: {relative}")
                output.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output.open("xb") as handle:
                    shutil.copyfileobj(source, handle, length=1024 * 1024)
        (target / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        verify_manifest_files(manifest, target)
    except Exception:
        shutil.rmtree(target, ignore_errors=True)
        raise
