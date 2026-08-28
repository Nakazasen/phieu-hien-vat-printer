from __future__ import annotations

import json
import hashlib
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


def test_discovery_defers_package_hash_validation_until_download(mock_runtime_paths: RuntimePaths, tmp_path: Path):
    """Startup discovery remains fast; an invalid package is rejected before installation."""
    lan_folder = tmp_path / "lan_updates"
    lan_folder.mkdir()
    package_file = lan_folder / "InPhieuHienVat-1.1.0.phieuupdate"
    package_file.write_bytes(b"tampered update package")
    (lan_folder / "latest.json").write_text(
        json.dumps(
            {
                "schema": 1,
                "channel": "stable",
                "version": "1.1.0",
                "package": package_file.name,
                "sha256": "0" * 64,
                "size": package_file.stat().st_size,
                "notes": "Package integrity is checked during download.",
            }
        ),
        encoding="utf-8",
    )
    save_update_config(
        mock_runtime_paths,
        {
            "schema": 1,
            "startup_check": True,
            "sources": [{"type": "folder", "location": str(lan_folder), "enabled": True}],
        },
    )

    candidate = discover_update(mock_runtime_paths, current_version="1.0.0")

    assert candidate is not None
    with pytest.raises(UpdateDeliveryError, match="Hash hoặc kích thước"):
        fetch_update(mock_runtime_paths, candidate)


# ======================================================================
# Tests for updater.app_updates and update_launcher
# ======================================================================

from updater.app_updates import (
    ApplicationUpdateError,
    activate_staged_update,
    application_install_root,
    backup_runtime_state,
    inspect_update_package,
    install_update,
    rollback_update,
    stage_update,
)
from updater.update_launcher import (
    LauncherStateError,
    _safe_entrypoint,
    resolve_current_entrypoint,
)


def test_application_install_root():
    root = Path("C:/Users/test/AppData/Local/InPhieuHienVat")
    app_dir = root / "apps" / "0.1.1"
    assert application_install_root(app_dir) == root

    with pytest.raises(ApplicationUpdateError):
        application_install_root(root / "other_folder" / "0.1.1")

    with pytest.raises(ApplicationUpdateError):
        application_install_root(root / "apps" / "invalid_ver")


def _create_mock_update_package(output_path: Path, *, version: str, min_app_version: str = "0.1.0") -> Path:
    entrypoint_content = b"executable mock"
    manifest = {
        "schema": 1,
        "kind": "application",
        "id": "InPhieuHienVat",
        "version": version,
        "min_app_version": min_app_version,
        "entrypoint": "InPhieuHienVat.exe",
        "files": [
            {
                "path": "InPhieuHienVat.exe",
                "sha256": hashlib.sha256(entrypoint_content).hexdigest(),
                "size": len(entrypoint_content),
            }
        ],
    }
    with zipfile.ZipFile(output_path, "w") as zf:
        zf.writestr("manifest.json", canonical_json_bytes(manifest))
        zf.writestr("InPhieuHienVat.exe", entrypoint_content)
    return output_path


def test_inspect_and_stage_update(tmp_path: Path):
    app_root = tmp_path / "InPhieuHienVat"
    app_root.mkdir()
    (app_root / "apps" / "0.1.0").mkdir(parents=True)

    pkg = _create_mock_update_package(tmp_path / "InPhieuHienVat-0.1.1.phieuupdate", version="0.1.1")
    manifest = inspect_update_package(pkg, current_version="0.1.0")
    assert manifest["version"] == "0.1.1"

    # Stage update
    staged_dir = stage_update(pkg, app_root, current_version="0.1.0")
    assert staged_dir == app_root / "apps" / "0.1.1"
    assert (staged_dir / "InPhieuHienVat.exe").is_file()
    assert (staged_dir / "manifest.json").is_file()

    # Staging again with existing version should fail
    with pytest.raises(ApplicationUpdateError):
        stage_update(pkg, app_root, current_version="0.1.0")


def test_backup_runtime_state(mock_runtime_paths: RuntimePaths, tmp_path: Path):
    import sqlite3

    # Populate registry database with real SQLite tables
    conn = sqlite3.connect(mock_runtime_paths.registry_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, code TEXT)")
    conn.execute("INSERT INTO test (code) VALUES ('SAMPLE-001')")
    conn.commit()
    conn.close()

    backup_root = tmp_path / "backups"
    dest = backup_runtime_state(mock_runtime_paths, backup_root, target_version="0.1.2")
    assert dest.is_dir()
    assert (dest / "po_registry.db").is_file()
    assert (dest / "layout_config.json").is_file()
    assert (dest / "backup.json").is_file()

    # Verify backup DB content matches
    b_conn = sqlite3.connect(dest / "po_registry.db")
    cur = b_conn.cursor()
    cur.execute("SELECT code FROM test")
    rows = cur.fetchall()
    assert rows == [("SAMPLE-001",)]
    b_conn.close()


def test_rollback_update(tmp_path: Path):
    app_root = tmp_path / "InPhieuHienVat"
    app_root.mkdir()
    (app_root / "apps" / "0.1.0").mkdir(parents=True)
    (app_root / "apps" / "0.1.0" / "InPhieuHienVat.exe").write_bytes(b"v0.1.0")
    (app_root / "apps" / "0.1.1").mkdir(parents=True)
    (app_root / "apps" / "0.1.1" / "InPhieuHienVat.exe").write_bytes(b"v0.1.1")

    current_state = {"schema": 1, "version": "0.1.1", "entrypoint": "InPhieuHienVat.exe"}
    prev_state = {"schema": 1, "version": "0.1.0", "entrypoint": "InPhieuHienVat.exe"}

    (app_root / "current.json").write_text(json.dumps(current_state), encoding="utf-8")
    (app_root / "previous.json").write_text(json.dumps(prev_state), encoding="utf-8")

    rolled = rollback_update(app_root)
    assert rolled["version"] == "0.1.0"
    assert json.loads((app_root / "current.json").read_text(encoding="utf-8"))["version"] == "0.1.0"
    assert json.loads((app_root / "previous.json").read_text(encoding="utf-8"))["version"] == "0.1.1"


def test_resolve_current_entrypoint(tmp_path: Path):
    app_root = tmp_path / "InPhieuHienVat"
    app_root.mkdir()
    version_dir = app_root / "apps" / "0.1.1"
    version_dir.mkdir(parents=True)
    exe_file = version_dir / "InPhieuHienVat.exe"
    exe_file.write_bytes(b"mock exe content")
    manifest_file = version_dir / "manifest.json"
    manifest_file.write_text("{}", encoding="utf-8")
    manifest_hash = sha256_file(manifest_file)

    current_data = {
        "schema": 1,
        "version": "0.1.1",
        "entrypoint": "InPhieuHienVat.exe",
        "manifest_sha256": manifest_hash,
    }
    (app_root / "current.json").write_text(json.dumps(current_data), encoding="utf-8")

    resolved = resolve_current_entrypoint(app_root)
    assert resolved == exe_file

    # Manifest hash mismatch should raise error
    current_data["manifest_sha256"] = "0" * 64
    (app_root / "current.json").write_text(json.dumps(current_data), encoding="utf-8")
    with pytest.raises(LauncherStateError):
        resolve_current_entrypoint(app_root)


def test_safe_entrypoint():
    assert _safe_entrypoint("InPhieuHienVat.exe") == "InPhieuHienVat.exe"
    with pytest.raises(LauncherStateError):
        _safe_entrypoint("../outside.exe")
    with pytest.raises(LauncherStateError):
        _safe_entrypoint("script.bat")


def test_inno_setup_iss_and_language_files():
    project_root = Path(__file__).resolve().parent.parent
    iss_file = project_root / "installer" / "InPhieuHienVat.iss"
    assert iss_file.is_file(), "installer/InPhieuHienVat.iss must exist"
    iss_content = iss_file.read_text(encoding="utf-8")

    release_file = project_root / "release.json"
    assert release_file.is_file(), "release.json must exist"
    release_data = json.loads(release_file.read_text(encoding="utf-8"))
    version = release_data["version"]

    # Check AppVersion matches release.json
    assert f'#define AppVersion "{version}"' in iss_content
    # Check AppId
    assert 'AppId="{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}"' in iss_content or '#define AppId "{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}"' in iss_content
    # Check DefaultDirName
    assert "{localappdata}\\InPhieuHienVat" in iss_content
    # Check PrivilegesRequired
    assert "PrivilegesRequired=lowest" in iss_content
    # Check Vietnamese language file is referenced and exists
    assert 'MessagesFile: "languages\\Vietnamese.isl"' in iss_content
    isl_file = project_root / "installer" / "languages" / "Vietnamese.isl"
    assert isl_file.is_file(), "installer/languages/Vietnamese.isl must exist"
    assert "Tiếng Việt" in isl_file.read_text(encoding="utf-8", errors="replace")
