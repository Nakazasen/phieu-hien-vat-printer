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
    from datetime import timezone
    prefix = "11" + datetime.now(timezone.utc).strftime("%y%m%d")
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

