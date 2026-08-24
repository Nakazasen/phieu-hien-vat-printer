"""Adversarial stress testing and empirical verification of auto-update engine.

Covers:
1. Corrupt package download (SHA-256 mismatch, size mismatch, temp file cleanup)
2. Malicious zip directory traversal (anti-zip-slip, safe_relative_path, cleanup on abort)
3. Version downgrade rejection (discover, inspect, and staging gates)
4. Live SQLite database backup integrity (online backup API, PRAGMA integrity_check, metadata)
5. Offline / unreachable network share non-blocking fallback (UNC paths, corrupt catalogs, queue dispatch)
"""

from __future__ import annotations

import json
import os
import queue
import sqlite3
import tempfile
import threading
import zipfile
from pathlib import Path
from typing import Any

import pytest

from core.runtime_paths import RuntimePaths
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
from updater.update_launcher import (
    LauncherStateError,
    _safe_entrypoint,
    resolve_current_entrypoint,
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


# =============================================================================
# FIXTURES & HELPERS
# =============================================================================

@pytest.fixture
def mock_runtime(tmp_path: Path) -> RuntimePaths:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    install = tmp_path / "install" / "apps" / "0.1.0"
    install.mkdir(parents=True)
    data = tmp_path / "data"
    data.mkdir()
    output = tmp_path / "output"
    output.mkdir()

    default_cfg = {
        "schema": 1,
        "startup_check": True,
        "sources": [
            {"type": "folder", "location": str(tmp_path / "lan_share"), "enabled": True}
        ],
    }
    (bundle / "update_sources.default.json").write_text(json.dumps(default_cfg), encoding="utf-8")
    (bundle / "release.json").write_text(json.dumps({"version": "0.1.0", "name": "InPhieuHienVat"}), encoding="utf-8")

    template = bundle / "template.pdf"
    template.write_bytes(b"%PDF-1.4 mock template")

    layout = data / "layout_config.json"
    layout.write_text("{}", encoding="utf-8")

    registry = data / "po_registry.db"
    conn = sqlite3.connect(registry)
    conn.execute("CREATE TABLE po_records (id INTEGER PRIMARY KEY, po_code TEXT, box TEXT)")
    conn.execute("INSERT INTO po_records (po_code, box) VALUES ('PO-1126000001', '001/001')")
    conn.commit()
    conn.close()

    return RuntimePaths(
        bundle_dir=bundle,
        installation_dir=install,
        data_dir=data,
        output_dir=output,
        template_path=template,
        layout_path=layout,
        registry_path=registry,
    )


def _build_zip_package(
    destination: Path,
    manifest: dict[str, Any],
    file_payloads: dict[str, bytes],
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w") as zf:
        zf.writestr("manifest.json", canonical_json_bytes(manifest))
        for rel_path, payload in file_payloads.items():
            zf.writestr(rel_path, payload)
    return destination


def _make_valid_manifest(version: str = "0.1.1", min_app_version: str = "0.1.0", files: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if files is None:
        exe_bytes = b"MZ\x90\x00_MOCK_EXE_PAYLOAD_"
        digest = "6b36a188f6c99c855a7ee4bfa95f32ebf1d93b3f2f81155986fc743b5932ef2f"  # sha256 of exe_bytes
        files = [
            {"path": "InPhieuHienVat.exe", "sha256": digest, "size": len(exe_bytes)},
        ]
    return {
        "schema": 1,
        "kind": "application",
        "id": "InPhieuHienVat",
        "version": version,
        "min_app_version": min_app_version,
        "entrypoint": "InPhieuHienVat.exe",
        "files": files,
    }


# =============================================================================
# 1. CORRUPT PACKAGE DOWNLOAD & CLEANUP OF TEMP FILES
# =============================================================================

class TestCorruptPackageDownload:
    def test_sha256_checksum_mismatch_rejection_and_temp_cleanup(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify fetch_update detects corrupted SHA-256, rejects it, and cleans up temp files."""
        downloads_dir = mock_runtime.data_dir / ".updates" / "downloads"

        # Create a package with specific bytes
        real_content = b"actual_package_content_12345"
        real_pkg = tmp_path / "InPhieuHienVat-0.1.1.phieuupdate"
        real_pkg.write_bytes(real_content)

        # Intentionally provide a forged/mismatched SHA-256 in the candidate
        tampered_candidate = UpdateCandidate(
            version="0.1.1",
            package_path=real_pkg,
            size=len(real_content),
            sha256="0000000000000000000000000000000000000000000000000000000000000000",
            notes="Corrupt package test",
        )

        with pytest.raises(UpdateDeliveryError, match="Hash hoặc kích thước package tải về không khớp"):
            fetch_update(mock_runtime, tampered_candidate)

        # Verify no .tmp files remain in downloads directory
        if downloads_dir.exists():
            remaining_tmp_files = list(downloads_dir.glob("*.tmp"))
            assert len(remaining_tmp_files) == 0, f"Found leaked temp files: {remaining_tmp_files}"
            final_target = downloads_dir / "InPhieuHienVat-0.1.1.phieuupdate"
            assert not final_target.exists(), "Final target package should not exist on failure"

    def test_size_mismatch_rejection_and_temp_cleanup(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify fetch_update detects size discrepancy (e.g. truncated download), rejects and cleans up."""
        downloads_dir = mock_runtime.data_dir / ".updates" / "downloads"

        real_content = b"short"
        real_pkg = tmp_path / "InPhieuHienVat-0.1.1.phieuupdate"
        real_pkg.write_bytes(real_content)
        actual_hash = sha256_file(real_pkg)

        # Claim size is 1000 bytes when real is 5 bytes
        size_mismatch_candidate = UpdateCandidate(
            version="0.1.1",
            package_path=real_pkg,
            size=1000,
            sha256=actual_hash,
            notes="Size mismatch test",
        )

        with pytest.raises(UpdateDeliveryError, match="Hash hoặc kích thước package tải về không khớp"):
            fetch_update(mock_runtime, size_mismatch_candidate)

        if downloads_dir.exists():
            assert len(list(downloads_dir.glob("*.tmp"))) == 0

    def test_source_read_failure_temp_cleanup(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify fetch_update cleans up temporary file when source file vanishes during download."""
        downloads_dir = mock_runtime.data_dir / ".updates" / "downloads"
        ghost_pkg = tmp_path / "non_existent_package.phieuupdate"

        candidate = UpdateCandidate(
            version="0.1.1",
            package_path=ghost_pkg,
            size=100,
            sha256="a" * 64,
            notes="Missing source test",
        )

        with pytest.raises(Exception):
            fetch_update(mock_runtime, candidate)

        if downloads_dir.exists():
            assert len(list(downloads_dir.glob("*.tmp"))) == 0


# =============================================================================
# 2. MALICIOUS ZIP PACKAGE DIRECTORY TRAVERSAL (ANTI-ZIP-SLIP)
# =============================================================================

class TestZipDirectoryTraversalSecurity:
    @pytest.mark.parametrize(
        "malicious_path",
        [
            "../../malicious.txt",
            "../escape.exe",
            "assets/../../escape.txt",
            "sub/nested/../../../system32/cmd.exe",
            "/absolute/root.exe",
            "C:/Windows/system32/calc.exe",
            "D:\\danger\\payload.exe",
            "\\\\network_share\\exploit.exe",
            ".git/config",
            ".env",
            "folder/.secret",
            "./dot_prefixed.txt",
        ],
    )
    def test_safe_relative_path_rejects_adversarial_patterns(self, malicious_path: str):
        """Verify safe_relative_path rejects all traversal and path escape vectors."""
        with pytest.raises(ArtifactVerificationError):
            safe_relative_path(malicious_path)

    def test_safe_extract_package_rejects_zip_slip_and_cleans_destination(self, tmp_path: Path):
        """Verify safe_extract_package rejects archive with directory traversal and cleans up destination."""
        staging_dest = tmp_path / "staging_target"
        package_path = tmp_path / "malicious_slip.phieuupdate"

        exe_bytes = b"MZ\x90\x00_MOCK_EXE_PAYLOAD_"
        digest = sha256_file(tmp_path / "m.tmp" if (tmp_path / "m.tmp").write_bytes(exe_bytes) else tmp_path / "m.tmp")

        manifest = {
            "schema": 1,
            "kind": "application",
            "id": "InPhieuHienVat",
            "version": "0.1.1",
            "min_app_version": "0.1.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [
                {"path": "InPhieuHienVat.exe", "sha256": digest, "size": len(exe_bytes)},
            ],
        }

        # Craft malicious zip with zip-slip entry
        with zipfile.ZipFile(package_path, "w") as zf:
            zf.writestr("manifest.json", canonical_json_bytes(manifest))
            zf.writestr("InPhieuHienVat.exe", exe_bytes)
            zf.writestr("../../malicious.txt", b"EVIL PAYLOAD OUTSIDE DESTINATION")

        # Extraction must fail and clean up staging_dest
        with pytest.raises(ArtifactVerificationError):
            safe_extract_package(package_path, staging_dest)

        assert not staging_dest.exists(), "Staging destination must be cleaned up on failure"
        assert not (tmp_path.parent / "malicious.txt").exists(), "Malicious file must not have been created"

    def test_safe_extract_package_rejects_unlisted_files(self, tmp_path: Path):
        """Verify safe_extract_package rejects archives containing unlisted surprise files."""
        staging_dest = tmp_path / "staging_unlisted"
        package_path = tmp_path / "unlisted.phieuupdate"

        exe_bytes = b"MZ\x90\x00_MOCK_EXE_PAYLOAD_"
        digest = sha256_file(tmp_path / "m2.tmp" if (tmp_path / "m2.tmp").write_bytes(exe_bytes) else tmp_path / "m2.tmp")

        manifest = {
            "schema": 1,
            "kind": "application",
            "id": "InPhieuHienVat",
            "version": "0.1.1",
            "min_app_version": "0.1.0",
            "entrypoint": "InPhieuHienVat.exe",
            "files": [
                {"path": "InPhieuHienVat.exe", "sha256": digest, "size": len(exe_bytes)},
            ],
        }

        with zipfile.ZipFile(package_path, "w") as zf:
            zf.writestr("manifest.json", canonical_json_bytes(manifest))
            zf.writestr("InPhieuHienVat.exe", exe_bytes)
            zf.writestr("backdoor.dll", b"unauthorized dll")

        with pytest.raises(ArtifactVerificationError, match="Package có file thừa hoặc thiếu"):
            safe_extract_package(package_path, staging_dest)

        assert not staging_dest.exists()


# =============================================================================
# 3. DOWNGRADE ATTEMPT REJECTION
# =============================================================================

class TestDowngradeAttemptRejection:
    def test_discover_update_ignores_older_or_equal_versions(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify discover_update strictly ignores catalogs offering equal or older versions."""
        lan_share = tmp_path / "lan_share"
        lan_share.mkdir(parents=True, exist_ok=True)

        package_path = lan_share / "InPhieuHienVat-0.1.0.phieuupdate"
        package_path.write_bytes(b"mock_pkg_bytes")
        pkg_hash = sha256_file(package_path)

        # 1. Catalog offers 0.1.0 (same as running 0.1.0)
        catalog_same = {
            "schema": 1,
            "channel": "pilot",
            "version": "0.1.0",
            "package": "InPhieuHienVat-0.1.0.phieuupdate",
            "sha256": pkg_hash,
            "size": package_path.stat().st_size,
            "notes": "Same version",
        }
        (lan_share / "latest.json").write_text(json.dumps(catalog_same), encoding="utf-8")
        assert discover_update(mock_runtime, current_version="0.1.0") is None

        # 2. Catalog offers 0.0.9 (downgrade when running 0.1.0)
        pkg_down = lan_share / "InPhieuHienVat-0.0.9.phieuupdate"
        pkg_down.write_bytes(b"older_pkg_bytes")
        catalog_down = {
            "schema": 1,
            "channel": "pilot",
            "version": "0.0.9",
            "package": "InPhieuHienVat-0.0.9.phieuupdate",
            "sha256": sha256_file(pkg_down),
            "size": pkg_down.stat().st_size,
            "notes": "Downgrade version",
        }
        (lan_share / "latest.json").write_text(json.dumps(catalog_down), encoding="utf-8")
        assert discover_update(mock_runtime, current_version="0.1.0") is None

    def test_inspect_update_package_blocks_downgrade(self, tmp_path: Path):
        """Verify inspect_update_package raises ApplicationUpdateError on downgrade attempts."""
        exe_bytes = b"MZ\x90\x00_MOCK_EXE_PAYLOAD_"
        digest = sha256_file(tmp_path / "e.tmp" if (tmp_path / "e.tmp").write_bytes(exe_bytes) else tmp_path / "e.tmp")

        # Create package with version 0.1.0
        manifest_010 = _make_valid_manifest(version="0.1.0", min_app_version="0.0.1")
        manifest_010["files"][0]["sha256"] = digest
        manifest_010["files"][0]["size"] = len(exe_bytes)

        pkg_path = tmp_path / "InPhieuHienVat-0.1.0.phieuupdate"
        _build_zip_package(pkg_path, manifest_010, {"InPhieuHienVat.exe": exe_bytes})

        # When current running version is 0.1.1, inspect must raise ApplicationUpdateError
        with pytest.raises(ApplicationUpdateError, match="Package update phải mới hơn version đang chạy"):
            inspect_update_package(pkg_path, current_version="0.1.1")

        # When current running version is 0.1.0 (equal), inspect must raise ApplicationUpdateError
        with pytest.raises(ApplicationUpdateError, match="Package update phải mới hơn version đang chạy"):
            inspect_update_package(pkg_path, current_version="0.1.0")

    def test_inspect_update_package_blocks_unmet_min_app_version(self, tmp_path: Path):
        """Verify inspect_update_package blocks upgrade if current version < min_app_version."""
        exe_bytes = b"MZ\x90\x00_MOCK_EXE_PAYLOAD_"
        digest = sha256_file(tmp_path / "e2.tmp" if (tmp_path / "e2.tmp").write_bytes(exe_bytes) else tmp_path / "e2.tmp")

        # Package version 0.2.0 requires min_app_version 0.1.5
        manifest_020 = _make_valid_manifest(version="0.2.0", min_app_version="0.1.5")
        manifest_020["files"][0]["sha256"] = digest
        manifest_020["files"][0]["size"] = len(exe_bytes)

        pkg_path = tmp_path / "InPhieuHienVat-0.2.0.phieuupdate"
        _build_zip_package(pkg_path, manifest_020, {"InPhieuHienVat.exe": exe_bytes})

        # Running version 0.1.0 < min_app_version 0.1.5
        with pytest.raises(ApplicationUpdateError, match="Package update yêu cầu version cũ mới hơn"):
            inspect_update_package(pkg_path, current_version="0.1.0")


# =============================================================================
# 4. LIVE SQLITE DATABASE BACKUP INTEGRITY
# =============================================================================

class TestLiveDatabaseBackupIntegrity:
    def test_live_sqlite_backup_during_update_staging(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify backup_runtime_state produces an uncorrupted, valid SQLite backup with metadata."""
        # Open live write connection and write records
        live_conn = sqlite3.connect(mock_runtime.registry_path)
        live_conn.execute("CREATE TABLE IF NOT EXISTS stress_test (id INTEGER PRIMARY KEY, item_code TEXT, val REAL)")
        for i in range(100):
            live_conn.execute("INSERT INTO stress_test (item_code, val) VALUES (?, ?)", (f"ITEM_{i:04d}", i * 1.5))
        live_conn.commit()

        backup_root = tmp_path / "backups"
        target_version = "0.1.2"

        # Perform backup while live connection is open
        backup_dir = backup_runtime_state(mock_runtime, backup_root, target_version=target_version)

        assert backup_dir == backup_root / f"before-{target_version}"
        assert backup_dir.is_dir()

        backed_db = backup_dir / "po_registry.db"
        assert backed_db.is_file()
        assert backed_db.stat().st_size > 0

        # Verify SQLite integrity via PRAGMA integrity_check
        backup_conn = sqlite3.connect(backed_db)
        integrity_result = backup_conn.execute("PRAGMA integrity_check").fetchall()
        assert integrity_result == [("ok",)], f"Integrity check failed: {integrity_result}"

        # Verify exact data in backup
        rows = backup_conn.execute("SELECT COUNT(*), SUM(val) FROM stress_test").fetchone()
        assert rows[0] == 100
        assert rows[1] == sum(i * 1.5 for i in range(100))

        backup_conn.close()
        live_conn.close()

        # Verify backup.json metadata
        backup_meta_file = backup_dir / "backup.json"
        assert backup_meta_file.is_file()
        meta = json.loads(backup_meta_file.read_text(encoding="utf-8"))
        assert meta["schema"] == 1
        assert meta["target_version"] == target_version
        assert any(item["path"] == "po_registry.db" and item["sha256"] == sha256_file(backed_db) for item in meta["files"])

    def test_backup_fails_closed_if_backup_directory_already_exists(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify backup_runtime_state refuses to overwrite existing backup directory."""
        backup_root = tmp_path / "backups"
        target_version = "0.1.2"
        existing = backup_root / f"before-{target_version}"
        existing.mkdir(parents=True)

        with pytest.raises(ApplicationUpdateError, match="Backup đã tồn tại"):
            backup_runtime_state(mock_runtime, backup_root, target_version=target_version)


# =============================================================================
# 5. OFFLINE / UNREACHABLE NETWORK SHARE GRACEFUL FALLBACK
# =============================================================================

class TestOfflineNetworkShareFallback:
    def test_discover_update_handles_unreachable_unc_share(self, mock_runtime: RuntimePaths):
        """Verify discover_update returns None smoothly when LAN share is unreachable."""
        offline_config = {
            "schema": 1,
            "startup_check": True,
            "sources": [
                {"type": "folder", "location": r"\\fstvn01\NonExistentShare\PMintemEDI\release_update", "enabled": True},
                {"type": "folder", "location": r"Z:\UnmappedDrive\updates", "enabled": True},
            ],
        }
        save_update_config(mock_runtime, offline_config)

        # discover_update must not crash, raise unhandled exception, or hang
        candidate = discover_update(mock_runtime, current_version="0.1.0")
        assert candidate is None

    def test_discover_update_handles_corrupt_or_malformed_catalog(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify discover_update ignores malformed latest.json files gracefully."""
        bad_share = tmp_path / "bad_share"
        bad_share.mkdir()

        # 1. Invalid JSON
        (bad_share / "latest.json").write_text("{invalid_json: true", encoding="utf-8")
        save_update_config(mock_runtime, {
            "schema": 1,
            "startup_check": True,
            "sources": [{"type": "folder", "location": str(bad_share), "enabled": True}],
        })
        assert discover_update(mock_runtime, current_version="0.1.0") is None

        # 2. Schema mismatch
        (bad_share / "latest.json").write_text(json.dumps({"schema": 999}), encoding="utf-8")
        assert discover_update(mock_runtime, current_version="0.1.0") is None

        # 3. Non-semver version
        (bad_share / "latest.json").write_text(json.dumps({
            "schema": 1, "channel": "pilot", "version": "v1.2.0-beta", "package": "App.phieuupdate",
            "sha256": "0" * 64, "size": 100, "notes": "bad"
        }), encoding="utf-8")
        assert discover_update(mock_runtime, current_version="0.1.0") is None

    def test_multi_source_discovery_with_offline_and_online_shares(self, mock_runtime: RuntimePaths, tmp_path: Path):
        """Verify discover_update skips offline shares and discovers from active share."""
        online_share = tmp_path / "online_share"
        online_share.mkdir()

        pkg = online_share / "InPhieuHienVat-0.1.5.phieuupdate"
        pkg.write_bytes(b"valid_online_package")
        pkg_hash = sha256_file(pkg)

        (online_share / "latest.json").write_text(json.dumps({
            "schema": 1,
            "channel": "pilot",
            "version": "0.1.5",
            "package": "InPhieuHienVat-0.1.5.phieuupdate",
            "sha256": pkg_hash,
            "size": pkg.stat().st_size,
            "notes": "Multi-source discovery success",
        }), encoding="utf-8")

        config = {
            "schema": 1,
            "startup_check": True,
            "sources": [
                {"type": "folder", "location": r"\\dead_host\missing_folder", "enabled": True},
                {"type": "folder", "location": str(online_share), "enabled": True},
                {"type": "folder", "location": str(tmp_path / "disabled_folder"), "enabled": False},
            ],
        }
        save_update_config(mock_runtime, config)

        candidate = discover_update(mock_runtime, current_version="0.1.0")
        assert candidate is not None
        assert candidate.version == "0.1.5"
        assert candidate.sha256 == pkg_hash

    def test_background_thread_worker_queue_dispatch_simulation(self, mock_runtime: RuntimePaths):
        """Simulate background update thread and verify event queue contract under offline condition."""
        event_queue: queue.Queue[tuple[str, Any]] = queue.Queue()

        offline_config = {
            "schema": 1,
            "startup_check": True,
            "sources": [{"type": "folder", "location": r"\\offline_server\share", "enabled": True}],
        }
        save_update_config(mock_runtime, offline_config)

        def worker_thread(automatic: bool = True):
            try:
                candidate = discover_update(mock_runtime, current_version="0.1.0")
                event_queue.put(("update_available", (candidate, Path("C:/mock/app_root"), automatic)))
            except Exception as exc:
                event_queue.put(("update_error", (str(exc), automatic)))

        t = threading.Thread(target=worker_thread, kwargs={"automatic": True}, daemon=True)
        t.start()
        t.join(timeout=5.0)

        assert not t.is_alive()
        event_type, payload = event_queue.get_nowait()
        assert event_type == "update_available"
        candidate, app_root, automatic = payload
        assert candidate is None
        assert automatic is True
