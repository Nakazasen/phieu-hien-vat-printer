from datetime import datetime

import pytest

from core.po_registry import PORegistry


@pytest.fixture
def temp_registry(tmp_path):
    db_path = tmp_path / "test_po_registry.db"
    registry = PORegistry(db_path)
    yield registry
    registry.close()

def test_po_generation(temp_registry):
    po1 = temp_registry.generate_po()
    po2 = temp_registry.generate_po()
    
    assert po1.startswith("11")
    assert po2.startswith("11")
    
    # Prefix is 11 + YY + MM + DD
    prefix = "11" + datetime.now().strftime("%y%m%d")
    assert po1.startswith(prefix)
    
    # Suffix should increment
    seq1 = int(po1[-2:])
    seq2 = int(po2[-2:])
    assert seq2 == seq1 + 1

def test_register_combos_success(temp_registry):
    combos = [("PO1", "00010", "+001", "001"), ("PO2", "00010", "+001", "001")]
    temp_registry.register_combos(combos)
    
    cursor = temp_registry._conn.cursor()
    cursor.execute("SELECT count(*) FROM po_registry")
    assert cursor.fetchone()[0] == 2

def test_register_combos_duplicate(temp_registry):
    from core.po_registry import DuplicateComboError
    combos = [("PO1", "00010", "+001", "001")]
    temp_registry.register_combos(combos)
    
    with pytest.raises(DuplicateComboError):
        temp_registry.register_combos(combos)

def test_fetch_history_and_statistics(temp_registry):
    combos = [
        ("PO100", "00010", "+001", "BOX1"),
        ("PO200", "00010", "+001", "BOX2"),
    ]
    temp_registry.register_combos(combos)

    stats = temp_registry.get_statistics()
    assert stats["total_count"] == 2
    assert stats["today_count"] == 2

    # Fetch all
    history = temp_registry.fetch_history()
    assert len(history) == 2

    # Search filter
    filtered = temp_registry.fetch_history(search="BOX1")
    assert len(filtered) == 1
    assert filtered[0]["po"] == "PO100"

def test_export_history_to_csv(temp_registry, tmp_path):
    combos = [("PO999", "00010", "+001", "BOX99")]
    temp_registry.register_combos(combos)

    export_path = tmp_path / "export_test.csv"
    count = temp_registry.export_history_to_csv(export_path)
    assert count == 1
    assert export_path.exists()
    content = export_path.read_text(encoding="utf-8-sig")
    assert "PO999" in content
    assert "BOX99" in content


def test_generate_split_po_detail_sequence(temp_registry):
    po = "1126081801"
    # First split detail should be 10010
    d1 = temp_registry.generate_split_po_detail(po)
    assert d1 == "10010"

    # Register combo with 10010
    temp_registry.register_combo(po, "10010", "+001", "001/001")

    # Next split detail should be 20010
    d2 = temp_registry.generate_split_po_detail(po)
    assert d2 == "20010"

    # Register combo with 20010
    temp_registry.register_combo(po, "20010", "+001", "001/001")

    # Next should be 30010
    d3 = temp_registry.generate_split_po_detail(po)
    assert d3 == "30010"

    # With exclude_details in memory
    d_excluded = temp_registry.generate_split_po_detail(po, exclude_details=["30010", "40010"])
    assert d_excluded == "50010"


def test_generate_return_po_detail_sequence(temp_registry):
    po = "1126081802"
    # First return detail should be 11010
    d1 = temp_registry.generate_return_po_detail(po, "10010")
    assert d1 == "11010"

    # Register combo with 11010
    temp_registry.register_combo(po, "11010", "+001", "001/001")

    # A second return of the same split branch increments D2.
    d2 = temp_registry.generate_return_po_detail(po, "10010")
    assert d2 == "12010"

    # With exclude_details
    d_excluded = temp_registry.generate_return_po_detail(
        po,
        "10010",
        exclude_details=["12010"],
    )
    assert d_excluded == "13010"


def test_operation_details_preserve_scanned_suffix_and_return_branch(temp_registry):
    po = "1126081805"

    assert temp_registry.generate_split_po_detail(po, "00020") == "10020"
    temp_registry.register_combo(po, "10020", "+001", "001/001")
    assert temp_registry.generate_split_po_detail(po, "00020") == "20020"

    assert temp_registry.generate_return_po_detail(po, "10020") == "11020"
    assert temp_registry.generate_return_po_detail(po, "20020") == "21020"
    temp_registry.register_combo(po, "11020", "+001", "001/001")
    assert temp_registry.generate_return_po_detail(po, "11020") == "12020"


def test_generate_split_po_detail_exhaustion_raises(temp_registry):
    from core.po_registry import PORegistryError
    po = "1126081803"
    # Register 9 splits: 10010 through 90010
    for i in range(1, 10):
        detail = temp_registry.generate_split_po_detail(po)
        assert detail == f"{i}0010"
        temp_registry.register_combo(po, detail, "+001", "001/001")

    # 10th split must raise PORegistryError rather than producing a 6-digit candidate
    with pytest.raises(PORegistryError, match="giới hạn tối đa 9 lần phân tách"):
        temp_registry.generate_split_po_detail(po)


def test_generate_return_po_detail_exhaustion_raises(temp_registry):
    from core.po_registry import PORegistryError
    po = "1126081804"
    # Register 9 returns for the same split branch: 11010 through 19010.
    for i in range(1, 10):
        detail = temp_registry.generate_return_po_detail(po, "10010")
        assert detail == f"1{i}010"
        temp_registry.register_combo(po, detail, "+001", "001/001")

    # 10th return must raise PORegistryError rather than producing a 6-digit candidate
    with pytest.raises(PORegistryError, match="9"):
        temp_registry.generate_return_po_detail(po, "10010")


def test_database_corruption_auto_recovery(tmp_path):
    """Verify that PORegistry automatically recovers and rebuilds cleanly from corrupted/malformed database files."""
    db_file = tmp_path / "corrupted_test_registry.db"
    
    # 1. Create a valid DB with 1 registered record
    reg1 = PORegistry(db_file)
    po = reg1.generate_po()
    reg1.register_combo(po, "00010", "+001", "001/001")
    assert reg1.count_registered() == 1
    reg1.close()

    # 2. Corrupt the database file by overwriting header with garbage bytes
    with open(db_file, "r+b") as f:
        f.seek(0)
        f.write(b"CORRUPTED_GARBAGE_BYTES_SQLITE_MALFORMED_HEADER_TEST")

    # 3. Open PORegistry on the corrupted file -> it should self-heal without crashing
    reg2 = PORegistry(db_file)
    try:
        # Should cleanly generate PO and register combos
        new_po = reg2.generate_po()
        assert new_po.startswith("11")
        reg2.register_combo(new_po, "00010", "+001", "001/001")
        assert reg2.count_registered() == 1

        # Check that backup was created
        backups = list(tmp_path.glob("*_corrupted_*.bak"))
        assert len(backups) >= 1
    finally:
        reg2.close()


def test_po_registry_shared_db_pragmas_and_journal_mode(tmp_path):
    """Requirement R1: Verify pragma configurations for network paths vs local paths."""
    local_db = tmp_path / "local.db"
    reg_local = PORegistry(local_db)
    try:
        jmode = reg_local._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert jmode.lower() in ("wal", "delete")
        fkeys = reg_local._conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fkeys == 1
    finally:
        reg_local.close()

    # Network UNC path simulation
    reg_unc = PORegistry(":memory:")
    try:
        reg_unc._db_path = r"\\mockserver\share\test.db"
        reg_unc._setup_pragmas()
        jmode = reg_unc._conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert jmode.lower() in ("delete", "memory", "wal")
    finally:
        reg_unc.close()


def test_po_registry_busy_retry_with_auto_recovery(tmp_path):
    """Requirement R1: Verify busy/locked retry loop with auto-recovery."""
    import sqlite3
    db_file = tmp_path / "busy_test.db"
    reg = PORegistry(db_file)
    try:
        attempts = 0
        def busy_op():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise sqlite3.OperationalError("database is locked")
            return "success"

        res = reg._execute_with_auto_recovery(busy_op)
        assert res == "success"
        assert attempts == 3
    finally:
        reg.close()




