"""Tests for Part Master (Master Linh Kiện) registry and validation."""

import pytest
from core.part_master import (
    PartMaster,
    PartMasterRegistry,
    PartMasterValidationError,
    validate_part_master,
)


def test_validate_part_master_success():
    code, name, rev = validate_part_master(" 3v2nd00160 ", " Cover Right ", "01")
    assert code == "3V2ND00160"
    assert name == "Cover Right"
    assert rev == "01"


@pytest.mark.parametrize("bad_code", ["", "   ", None])
def test_validate_part_master_empty_code(bad_code):
    with pytest.raises(PartMasterValidationError, match="Vui lòng nhập Mã linh kiện"):
        validate_part_master(bad_code, "Cover", "01")


@pytest.mark.parametrize("bad_name", ["", "   ", None])
def test_validate_part_master_empty_name(bad_name):
    with pytest.raises(PartMasterValidationError, match="Vui lòng nhập Tên linh kiện"):
        validate_part_master("ITEM01", bad_name, "01")


@pytest.mark.parametrize("bad_rev", ["", "   ", None])
def test_validate_part_master_empty_rev(bad_rev):
    with pytest.raises(PartMasterValidationError, match="Vui lòng nhập Rev linh kiện"):
        validate_part_master("ITEM01", "Cover", bad_rev)


@pytest.mark.parametrize("invalid_rev", ["1", "00", "001", "100", "A1", "9a", "-1"])
def test_validate_part_master_invalid_rev_format(invalid_rev):
    with pytest.raises(PartMasterValidationError, match="Rev bắt buộc phải là đúng 2 chữ số"):
        validate_part_master("ITEM01", "Cover", invalid_rev)


def test_part_master_registry_crud(tmp_path):
    db_file = tmp_path / "test_part_master.db"
    reg = PartMasterRegistry(db_file)
    try:
        assert reg.count() == 0
        assert reg.get("3V2ND00160") is None

        # Upsert new
        p1 = reg.upsert("3V2ND00160", "COVER RIGHT FUSER ASSY", "01")
        assert p1.item_code == "3V2ND00160"
        assert p1.item_name == "COVER RIGHT FUSER ASSY"
        assert p1.rev == "01"
        assert reg.count() == 1

        # Query by exact or lowercase
        found = reg.get("3v2nd00160")
        assert found is not None
        assert found.item_name == "COVER RIGHT FUSER ASSY"
        assert found.rev == "01"

        # Update existing
        p2 = reg.upsert("3v2nd00160", "COVER RIGHT FUSER ASSY UPDATED", "02")
        assert reg.count() == 1
        found2 = reg.get("3V2ND00160")
        assert found2.item_name == "COVER RIGHT FUSER ASSY UPDATED"
        assert found2.rev == "02"

        # Add second item
        reg.upsert("3V2ND25480", "GEAR ROLLER", "03")
        assert reg.count() == 2

        # Search list
        items = reg.list_all("fuser")
        assert len(items) == 1
        assert items[0].item_code == "3V2ND00160"

        all_items = reg.list_all()
        assert len(all_items) == 2

        # Delete
        assert reg.delete("3V2ND00160") is True
        assert reg.count() == 1
        assert reg.get("3V2ND00160") is None
        assert reg.delete("NON_EXISTING") is False
    finally:
        reg.close()
