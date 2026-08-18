from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest

from core.runtime_paths import RuntimePaths
from updater.update_delivery import (
    UpdateCandidate,
    UpdateDeliveryError,
    _catalog,
    _version,
    current_release_version,
    discover_update,
    fetch_update,
    load_update_config,
    save_update_config,
    validate_update_config,
)
from updater.update_security import (
    MAX_ARTIFACT_BYTES,
    ArtifactVerificationError,
    canonical_json_bytes,
    read_package_manifest,
    safe_extract_package,
    safe_relative_path,
    sha256_file,
    validate_manifest,
    verify_manifest_files,
)


# ======================================================================
# Tests for updater.update_security
# ======================================================================

def test_canonical_json_bytes():
    data = {"b": 2, "a": 1, "nested": {"z": 10, "y": 20}}
    result = canonical_json_bytes(data)
    assert isinstance(result, bytes)
    assert result.endswith(b"\n")
    decoded = json.loads(result.decode("utf-8"))
    assert decoded == data
    # Ensure keys are sorted in output string
    assert result == b'{"a":1,"b":2,"nested":{"y":20,"z":10}}\n'


def test_sha256_file(tmp_path: Path):
    sample = tmp_path / "sample.txt"
    sample.write_bytes(b"hello world")
    digest = sha256_file(sample)
    # sha256 of "hello world" is b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    assert digest == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"


def test_safe_relative_path_valid():
    assert safe_relative_path("InPhieuHienVat.exe") == "InPhieuHienVat.exe"
    assert safe_relative_path("assets/template.pdf") == "assets/template.pdf"
    assert safe_relative_path(r"assets\sub\config.json") == "assets/sub/config.json"


@pytest.mark.parametrize(
    "invalid_path",
    [
        "",
        "/absolute/path.exe",
        "C:/Windows/notepad.exe",
        "../traversal.exe",
        "sub/../../escape.exe",
        ".hidden_file",
        "folder/.hidden",
        "./dot_start",
    ],
)
def test_safe_relative_path_invalid(invalid_path: str):
    with pytest.raises(ArtifactVerificationError):
        safe_relative_path(invalid_path)


def test_validate_manifest_valid():
    valid_manifest = {
        "schema": 1,
        "kind": "application",
        "id": "InPhieuHienVat",
        "version": "1.0.1",
        "min_app_version": "1.0.0",
        "entrypoint": "InPhieuHienVat.exe",
        "files": [
            {
                "path": "InPhieuHienVat.exe",
                "sha256": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
                "size": 11,
            },
            {
                "path": "template.pdf",
                "sha256": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
                "size": 11,
            },
        ],
    }
    validate_manifest(valid_manifest)


@pytest.mark.parametrize(
    "corrupt_manifest",
    [
        {},  # empty
        {"schema": 2},  # unsupported schema
        {  # wrong kind
            "schema": 1,
            "kind": "plugin",
            "id": "InPhieuHienVat",
            "version": "1.0.1",
            "min_app_version": "1.0.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [],
        },
        {  # wrong id
            "schema": 1,
            "kind": "application",
            "id": "OtherApp",
            "version": "1.0.1",
            "min_app_version": "1.0.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [],
        },
        {  # non-exe entrypoint
            "schema": 1,
            "kind": "application",
            "id": "InPhieuHienVat",
            "version": "1.0.1",
            "min_app_version": "1.0.0",
            "entrypoint": "start.bat",
            "files": [{"path": "start.bat", "sha256": "a" * 64, "size": 10}],
        },
        {  # entrypoint not in files
            "schema": 1,
            "kind": "application",
            "id": "InPhieuHienVat",
            "version": "1.0.1",
            "min_app_version": "1.0.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [{"path": "other.exe", "sha256": "a" * 64, "size": 10}],
        },
        {  # duplicate files
            "schema": 1,
            "kind": "application",
            "id": "InPhieuHienVat",
            "version": "1.0.1",
            "min_app_version": "1.0.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [
                {"path": "InPhieuHienVat.exe", "sha256": "a" * 64, "size": 10},
                {"path": "InPhieuHienVat.exe", "sha256": "a" * 64, "size": 10},
            ],
        },
    ],
)
def test_validate_manifest_invalid(corrupt_manifest: dict):
    with pytest.raises(ArtifactVerificationError):
        validate_manifest(corrupt_manifest)


def test_verify_manifest_files_and_extract(tmp_path: Path):
    staging = tmp_path / "staging"
    content = b"fake binary executable content"
    digest = sha256_file(tmp_path / "content.tmp" if (tmp_path / "content.tmp").write_bytes(content) else tmp_path / "content.tmp")
    
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "InPhieuHienVat",
        "version": "1.0.1",
        "min_app_version": "1.0.0",
        "entrypoint": "InPhieuHienVat.exe",
        "files": [
            {
                "path": "InPhieuHienVat.exe",
                "sha256": digest,
                "size": len(content),
            }
        ],
    }
    
    # Create zip package
    package_path = tmp_path / "test_package.phieuupdate"
    with zipfile.ZipFile(package_path, "w") as zf:
        zf.writestr("manifest.json", canonical_json_bytes(manifest))
        zf.writestr("InPhieuHienVat.exe", content)

    # Test read_package_manifest
    read_manifest = read_package_manifest(package_path)
    assert read_manifest["version"] == "1.0.1"

    # Test safe_extract_package
    safe_extract_package(package_path, staging)
    assert (staging / "InPhieuHienVat.exe").is_file()
    assert (staging / "manifest.json").is_file()

    # Test verify_manifest_files
    verify_manifest_files(manifest, staging)


def test_safe_extract_package_fails_on_extra_files(tmp_path: Path):
    staging = tmp_path / "staging"
    content = b"content"
    digest = sha256_file(tmp_path / "c.tmp" if (tmp_path / "c.tmp").write_bytes(content) else tmp_path / "c.tmp")
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "InPhieuHienVat",
        "version": "1.0.1",
        "min_app_version": "1.0.0",
        "entrypoint": "InPhieuHienVat.exe",
        "files": [{"path": "InPhieuHienVat.exe", "sha256": digest, "size": len(content)}],
    }
    
    # Create zip with an unexpected file not in manifest
    package_path = tmp_path / "bad_package.phieuupdate"
    with zipfile.ZipFile(package_path, "w") as zf:
        zf.writestr("manifest.json", canonical_json_bytes(manifest))
        zf.writestr("InPhieuHienVat.exe", content)
        zf.writestr("extra_payload.exe", b"malicious")

    with pytest.raises(ArtifactVerificationError):
        safe_extract_package(package_path, staging)
    assert not staging.exists()  # Staging must be cleaned up on failure


# ======================================================================
# Tests for updater.update_delivery
# ======================================================================

def test_semver_parsing():
    assert _version("1.0.0") == (1, 0, 0)
    assert _version("2.15.3") == (2, 15, 3)
    assert _version("1.0.1") > _version("1.0.0")
    
    with pytest.raises(UpdateDeliveryError):
        _version("1.0")
    with pytest.raises(UpdateDeliveryError):
        _version("v1.0.0")
    with pytest.raises(UpdateDeliveryError):
        _version("1.0.0-beta")


def test_validate_update_config():
    valid_cfg = {
        "schema": 1,
        "startup_check": True,
        "sources": [
            {"type": "folder", "location": r"\\lan-server\updates", "enabled": True}
        ],
    }
    validated = validate_update_config(valid_cfg)
    assert validated["startup_check"] is True
    assert len(validated["sources"]) == 1

    with pytest.raises(UpdateDeliveryError):
        validate_update_config({"schema": 2})
    with pytest.raises(UpdateDeliveryError):
        validate_update_config({"schema": 1, "startup_check": True, "sources": [{"type": "http"}]})


@pytest.fixture
def mock_runtime_paths(tmp_path: Path) -> RuntimePaths:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    install = tmp_path / "install"
    install.mkdir()
    data = tmp_path / "data"
    data.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    # Create default config in bundle
    default_cfg = {
        "schema": 1,
        "startup_check": True,
        "sources": [{"type": "folder", "location": str(tmp_path / "lan_updates"), "enabled": True}],
    }
    (bundle / "update_sources.default.json").write_text(json.dumps(default_cfg), encoding="utf-8")

    # Create release metadata
    (bundle / "release.json").write_text(json.dumps({"version": "1.0.0", "name": "InPhieuHienVat"}), encoding="utf-8")

    template = bundle / "template.pdf"
    template.write_bytes(b"%PDF-1.4 test")

    layout = data / "layout_config.json"
    layout.write_text("{}", encoding="utf-8")

    registry = data / "po_registry.db"

    return RuntimePaths(
        bundle_dir=bundle,
        installation_dir=install,
        data_dir=data,
        output_dir=output,
        template_path=template,
        layout_path=layout,
        registry_path=registry,
    )


def test_load_and_save_update_config(mock_runtime_paths: RuntimePaths):
    # Initial load from bundle default
    cfg = load_update_config(mock_runtime_paths)
    assert cfg["startup_check"] is True
    assert len(cfg["sources"]) == 1

    # Save override to data_dir
    new_cfg = {
        "schema": 1,
        "startup_check": False,
        "sources": [{"type": "folder", "location": "D:/Shared/Updates", "enabled": False}],
    }
    save_update_config(mock_runtime_paths, new_cfg)

    # Load again should reflect override
    loaded = load_update_config(mock_runtime_paths)
    assert loaded["startup_check"] is False
    assert loaded["sources"][0]["enabled"] is False


def test_current_release_version(mock_runtime_paths: RuntimePaths):
    assert current_release_version(mock_runtime_paths) == "1.0.0"


def test_discover_and_fetch_update(mock_runtime_paths: RuntimePaths, tmp_path: Path):
    lan_folder = tmp_path / "lan_updates"
    lan_folder.mkdir()

    # Create a valid update package
    package_content = b"fake update zip bytes"
    package_file = lan_folder / "InPhieuHienVat-1.1.0.phieuupdate"
    package_file.write_bytes(package_content)
    digest = sha256_file(package_file)

    # Create latest.json in LAN folder
    catalog_data = {
        "schema": 1,
        "channel": "stable",
        "version": "1.1.0",
        "package": "InPhieuHienVat-1.1.0.phieuupdate",
        "sha256": digest,
        "size": len(package_content),
        "notes": "Update to 1.1.0 with fixes",
    }
    (lan_folder / "latest.json").write_text(json.dumps(catalog_data), encoding="utf-8")

    # Discover update when running version 1.0.0
    candidate = discover_update(mock_runtime_paths, current_version="1.0.0")
    assert candidate is not None
    assert candidate.version == "1.1.0"
    assert candidate.sha256 == digest

    # Discover update when already running version 1.1.0 (should return None)
    no_candidate = discover_update(mock_runtime_paths, current_version="1.1.0")
    assert no_candidate is None

    # Fetch update to download cache
    downloaded = fetch_update(mock_runtime_paths, candidate)
    assert downloaded.is_file()
    assert downloaded.stat().st_size == len(package_content)
    assert sha256_file(downloaded) == digest
