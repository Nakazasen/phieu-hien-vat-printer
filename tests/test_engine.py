import pytest

from core.slip_printer_engine import (
    calculate_total_qty,
    format_string_qty,
    normalize_lot,
    validate_revision,
)


def test_calculate_total_qty():
    assert calculate_total_qty("10", "001/003") == "30"
    assert calculate_total_qty("10.5", "002/002") == "21"
    assert calculate_total_qty("5", "004") == "20"
    
    with pytest.raises(ValueError):
        calculate_total_qty("-5", "002")
        
    with pytest.raises(ValueError):
        calculate_total_qty("abc", "002")

def test_validate_revision():
    assert validate_revision("01") == "01"
    assert validate_revision("99") == "99"
    
    with pytest.raises(ValueError):
        validate_revision("1")
        
    with pytest.raises(ValueError):
        validate_revision("00")
        
    with pytest.raises(ValueError):
        validate_revision("100")

def test_format_string_qty():
    assert format_string_qty(1) == "000000010000"
    assert format_string_qty(180) == "000001800000"
    assert format_string_qty("25") == "000000250000"

def test_normalize_lot():
    assert normalize_lot(None) == "          "
    assert normalize_lot("") == "          "
    assert normalize_lot("Lot123") == "Lot123"


def test_normalize_box():
    from core.slip_printer_engine import normalize_box
    assert normalize_box("1") == "001/001"
    assert normalize_box(1) == "001/001"
    assert normalize_box("3") == "001/003"
    assert normalize_box("001/003") == "001/003"
    assert normalize_box("002/003") == "002/003"
    assert normalize_box("1/3") == "001/003"
    assert normalize_box("2/5") == "002/005"


def test_expand_box_sequence():
    from core.slip_printer_engine import expand_box_sequence
    # N = 3 -> 3 records
    assert expand_box_sequence(3) == ["001/003", "002/003", "003/003"]
    assert expand_box_sequence("3") == ["001/003", "002/003", "003/003"]
    assert expand_box_sequence("003") == ["001/003", "002/003", "003/003"]
    
    # N = 1 -> 001/001
    assert expand_box_sequence(1) == ["001/001"]
    assert expand_box_sequence("1") == ["001/001"]
    
    # Pre-formatted 001/003 -> unchanged single
    assert expand_box_sequence("001/003") == ["001/003"]
    assert expand_box_sequence("002/003") == ["002/003"]
    assert expand_box_sequence("003/003") == ["003/003"]

    with pytest.raises(ValueError, match="lớn hơn 0"):
        expand_box_sequence(0)
    with pytest.raises(ValueError, match="lớn hơn 0"):
        expand_box_sequence("-2")
    with pytest.raises(ValueError, match="không được lớn hơn"):
        expand_box_sequence("5/3")
    with pytest.raises(ValueError, match="không được để trống"):
        expand_box_sequence("")
    with pytest.raises(ValueError, match="không được để trống"):
        expand_box_sequence("   ")
    with pytest.raises(ValueError, match="lớn hơn 0"):
        expand_box_sequence("0/3")
    with pytest.raises(ValueError, match="lớn hơn 0"):
        expand_box_sequence("1/0")
    with pytest.raises(ValueError):
        expand_box_sequence("invalid")
    with pytest.raises(ValueError):
        expand_box_sequence("abc/def")



def test_qr_payload_129_standard_compliance():
    from core.slip_printer_engine import build_qr_payload, create_record

    rec = create_record(
        row_number=1,
        item_code="3W2ND25350",
        item_name="COVER REAR",
        carton_qty="20",
        total_qty="60",
        po="1126021101",
        po_detail="00010",
        po_sub="+001",
        box="001/003",
        rev="01",
        lot=" " * 10,
    )

    payload = build_qr_payload(rec)
    assert len(payload) == 129, f"QR payload length must be 129, got {len(payload)}"
    prefix = payload[:122]
    suffix = payload[122:]
    assert len(prefix) == 122
    assert len(suffix) == 7
    assert suffix == "001/003"
    assert prefix.startswith("112602110100010+001    0000006000003W2ND25350 01            000000600000")


def test_qr_payload_roundtrip_parsing():
    from core.slip_printer_engine import build_qr_payload, create_record, parse_qr_payload

    original_rec = create_record(
        row_number=1,
        item_code="3V2ND00160",
        item_name="COVER RIGHT FUSER ASSY",
        carton_qty="20",
        total_qty="60",
        po="1126081801",
        po_detail="10010",
        po_sub="+001",
        box="002/003",
        rev="02",
        lot="LOT2026-X",
    )

    qr_str = build_qr_payload(original_rec)
    assert len(qr_str) == 129

    parsed = parse_qr_payload(qr_str)
    assert parsed.po == "1126081801"
    assert parsed.po_detail == "10010"
    assert parsed.po_sub == "+001"
    assert parsed.item_code == "3V2ND00160"
    assert parsed.rev == "02"
    assert parsed.total_qty == "60"
    assert parsed.box == "002/003"
    assert parsed.carton_qty == "20"
    assert parsed.lot == "LOT2026-X"


def test_qr_payload_single_box_129():
    from core.slip_printer_engine import build_qr_payload, create_record, parse_qr_payload

    # Box = 1 -> normalized to 001/001 -> total 129 chars
    rec = create_record(
        row_number=1,
        item_code="ITEM99",
        item_name="SINGLE BOX ITEM",
        carton_qty="50",
        total_qty="50",
        po="1126081899",
        po_detail="00010",
        po_sub="+001",
        box="1",
        rev="05",
        lot=None,
    )

    assert rec.box == "001/001"
    payload = build_qr_payload(rec)
    assert len(payload) == 129
    assert payload.endswith("001/001")

    parsed = parse_qr_payload(payload)
    assert parsed.box == "001/001"
    assert parsed.carton_qty == "50"
    assert parsed.total_qty == "50"


def test_create_record_default_lot():
    from core.slip_printer_engine import DEFAULT_LOT_TEXT, create_record

    # 1. lot omitted entirely
    rec_omitted = create_record(
        row_number=1,
        item_code="ITEM01",
        item_name="Part 1",
        carton_qty="10",
        total_qty="10",
        po="PO123",
        po_detail="00010",
        po_sub="+001",
        box="1",
        rev="01",
    )
    assert rec_omitted.lot == DEFAULT_LOT_TEXT
    assert rec_omitted.box == "001/001"

    # 2. lot=None
    rec_none = create_record(
        row_number=2,
        item_code="ITEM02",
        item_name="Part 2",
        carton_qty="10",
        total_qty="10",
        po="PO123",
        po_detail="00010",
        po_sub="+001",
        box="001/001",
        rev="01",
        lot=None,
    )
    assert rec_none.lot == DEFAULT_LOT_TEXT

    # 3. lot=""
    rec_empty = create_record(
        row_number=3,
        item_code="ITEM03",
        item_name="Part 3",
        carton_qty="10",
        total_qty="10",
        po="PO123",
        po_detail="00010",
        po_sub="+001",
        box="001/001",
        rev="01",
        lot="",
    )
    assert rec_empty.lot == DEFAULT_LOT_TEXT

    # 4. lot provided
    rec_with_lot = create_record(
        row_number=4,
        item_code="ITEM04",
        item_name="Part 4",
        carton_qty="10",
        total_qty="10",
        po="PO123",
        po_detail="00010",
        po_sub="+001",
        box="001/001",
        rev="01",
        lot="2026-08-19",
    )
    assert rec_with_lot.lot == "2026-08-19"


