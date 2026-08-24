from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from core.runtime_paths import (
    ENV_DATA_ROOT,
    ENV_OUTPUT_ROOT,
    _copy_if_missing,
    _documents_output,
    _local_app_data,
    _migrate_registry_if_needed,
    bundle_dir,
    installation_dir,
    prepare_runtime_paths,
)


def test_bundle_and_installation_dir():
    # In source / development mode, both point to project root
    b_dir = bundle_dir()
    i_dir = installation_dir()
    assert b_dir.is_dir()
    assert i_dir.is_dir()
    assert (b_dir / "slip_printer_app.py").is_file()
    assert (i_dir / "slip_printer_app.py").is_file()


def test_local_app_data_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    custom_data = tmp_path / "custom_data_dir"
    monkeypatch.setenv(ENV_DATA_ROOT, str(custom_data))
    resolved = _local_app_data()
    assert resolved == custom_data.resolve()


def test_documents_output_env_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    custom_output = tmp_path / "custom_output_dir"
    monkeypatch.setenv(ENV_OUTPUT_ROOT, str(custom_output))
    resolved = _documents_output()
    assert resolved == custom_output.resolve()


def test_copy_if_missing(tmp_path: Path):
    source = tmp_path / "source.txt"
    dest = tmp_path / "nested" / "dest.txt"

    # Source does not exist -> no-op
    _copy_if_missing(source, dest)
    assert not dest.exists()

    # Source exists -> copies to destination
    source.write_text("hello copy", encoding="utf-8")
    _copy_if_missing(source, dest)
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == "hello copy"

    # Destination already exists -> does not overwrite
    source.write_text("updated source", encoding="utf-8")
    _copy_if_missing(source, dest)
    assert dest.read_text(encoding="utf-8") == "hello copy"


def test_migrate_registry_if_needed(tmp_path: Path):
    legacy_db = tmp_path / "legacy.db"
    new_db = tmp_path / "migrated" / "po_registry.db"

    # Create a table and rows in legacy_db
    conn = sqlite3.connect(legacy_db)
    conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
    conn.execute("INSERT INTO test_table (name) VALUES ('item1'), ('item2')")
    conn.commit()
    conn.close()

    # Perform migration
    _migrate_registry_if_needed(legacy_db, new_db)
    assert new_db.is_file()

    # Verify data migrated properly
    conn2 = sqlite3.connect(new_db)
    rows = conn2.execute("SELECT name FROM test_table ORDER BY id").fetchall()
    conn2.close()
    assert rows == [("item1",), ("item2",)]

    # Calling again on existing destination does nothing
    _migrate_registry_if_needed(legacy_db, new_db)


def test_prepare_runtime_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    custom_data = tmp_path / "data"
    custom_output = tmp_path / "output"
    monkeypatch.setenv(ENV_DATA_ROOT, str(custom_data))
    monkeypatch.setenv(ENV_OUTPUT_ROOT, str(custom_output))

    paths = prepare_runtime_paths()
    assert paths.data_dir.is_dir()
    assert paths.output_dir.is_dir()
    assert paths.template_path.is_file()
    assert paths.layout_path.name == "layout_config.json"
    assert paths.registry_path.name == "po_registry.db"


def test_prepare_runtime_paths_missing_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    custom_data = tmp_path / "data"
    custom_output = tmp_path / "output"
    empty_bundle = tmp_path / "empty_bundle"
    empty_bundle.mkdir()

    monkeypatch.setenv(ENV_DATA_ROOT, str(custom_data))
    monkeypatch.setenv(ENV_OUTPUT_ROOT, str(custom_output))
    monkeypatch.setattr("core.runtime_paths.bundle_dir", lambda: empty_bundle)

    with pytest.raises(FileNotFoundError, match="Không tìm thấy template.pdf"):
        prepare_runtime_paths()


def test_resolve_registry_path_priorities(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Requirement R1: Verify priority order of registry path resolution."""
    from core.runtime_paths import ENV_REGISTRY_PATH, _resolve_registry_path

    data_dir = tmp_path / "local_data"
    data_dir.mkdir()

    # 1. Explicit registry file override
    explicit_file = tmp_path / "explicit_reg.db"
    monkeypatch.setenv(ENV_REGISTRY_PATH, str(explicit_file))
    assert _resolve_registry_path(data_dir) == explicit_file.resolve()

    # 2. Test data dir override
    monkeypatch.delenv(ENV_REGISTRY_PATH)
    monkeypatch.setenv(ENV_DATA_ROOT, str(data_dir))
    assert _resolve_registry_path(data_dir) == data_dir / "po_registry.db"

    # 3. Unreachable shared network fallback to local app data
    monkeypatch.delenv(ENV_DATA_ROOT)
    monkeypatch.setattr("core.runtime_paths.SHARED_REGISTRY_DIR", r"\\unreachable_host_999\share\dir")
    resolved = _resolve_registry_path(data_dir)
    assert resolved == data_dir / "po_registry.db"
