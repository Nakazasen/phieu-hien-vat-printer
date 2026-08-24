from __future__ import annotations

import customtkinter as ctk
import pytest

from core.po_registry import FIXED_PO_DETAIL, FIXED_PO_SUB, PORegistry
from core.slip_printer_engine import (
    QRParsedData,
    SlipRecord,
    build_qr_payload,
    calculate_total_qty,
    create_record,
    expand_box_sequence,
    normalize_box,
    parse_qr_payload,
    validate_records,
)
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.qr_scan_dialog import QRScanDialog


@pytest.fixture
def memory_registry():
    registry = PORegistry(":memory:")
    yield registry
    registry.close()


# ======================================================================
# R1: Box Auto-Expansion & Multi-Box PO Association
# ======================================================================

def test_box_expansion_integer_3():
    boxes = expand_box_sequence(3)
    assert boxes == ["001/003", "002/003", "003/003"]


def test_box_expansion_integer_1():
    boxes = expand_box_sequence(1)
    assert boxes == ["001/001"]


def test_box_expansion_formatted_stays_single():
    boxes = expand_box_sequence("001/003")
    assert boxes == ["001/003"]
    boxes2 = expand_box_sequence("002/003")
    assert boxes2 == ["002/003"]


def test_box_total_qty_calculation_multiplied():
    # 20 carton_qty x 3 box -> total_qty = 60
    assert calculate_total_qty("20", "3") == "60"
    assert calculate_total_qty("20", "001/003") == "60"
    assert calculate_total_qty("20", "002/003") == "60"
    assert calculate_total_qty("20", "003/003") == "60"
    # 25 carton_qty x 1 -> 25
    assert calculate_total_qty("25", "1") == "25"
    assert calculate_total_qty("25", "001/001") == "25"


def test_add_record_expands_to_n_records_sharing_same_po(tk_root):
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        state.item_code_var.set("3W2ND25350")
        state.item_name_var.set("COVER REAR")
        state.carton_qty_var.set("20")
        state.box_var.set("3")  # Integer 3
        state.rev_var.set("01")
        state.po_var.set("")  # Auto-generate PO

        controller.add_record()

        # Should produce exactly 3 records
        assert len(state.records) == 3
        r1, r2, r3 = state.records

        # All share the same auto-generated PO
        assert r1.po.startswith("11")
        assert r1.po == r2.po == r3.po
        assert r1.po_detail == r2.po_detail == r3.po_detail == FIXED_PO_DETAIL
        assert r1.po_sub == r2.po_sub == r3.po_sub == FIXED_PO_SUB

        # Boxes are sequentially 001/003, 002/003, 003/003
        assert r1.box == "001/003"
        assert r2.box == "002/003"
        assert r3.box == "003/003"

        # Each record has total_qty = 60 (20 x 3)
        assert r1.total_qty == "60"
        assert r2.total_qty == "60"
        assert r3.total_qty == "60"
        assert r1.carton_qty == "20"
        assert r2.carton_qty == "20"
        assert r3.carton_qty == "20"

        # Each record QR payload is 129 chars
        assert len(r1.qr_payload) == 129
        assert len(r2.qr_payload) == 129
        assert len(r3.qr_payload) == 129
        assert r1.qr_payload.endswith("001/003")
        assert r2.qr_payload.endswith("002/003")
        assert r3.qr_payload.endswith("003/003")
    finally:
        state.po_registry.close()


# ======================================================================
# R2: Standardized 129-Character QR Code Verification
# ======================================================================

def test_qr_payload_exact_129_characters_and_122_prefix():
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

    payload = rec.qr_payload
    assert len(payload) == 129
    assert len(payload[:122]) == 122
    assert len(payload[122:]) == 7
    assert payload[122:] == "001/003"

    # Structure breakdown:
    # 0..19 (PO): 112602110100010+001 (19)
    assert payload[0:19] == "112602110100010+001"
    # 19..23 (Space 4): "    "
    assert payload[19:23] == "    "
    # 23..35 (Total Qty 12): 000000600000
    assert payload[23:35] == "000000600000"
    # 35..60 (Part & Rev 25): "3W2ND25350 01            "
    assert payload[35:60] == "3W2ND25350 01            "
    # 60..72 (Total Qty repeat 12): 000000600000
    assert payload[60:72] == "000000600000"
    # 72..98 (Lot 26): 26 spaces
    assert payload[72:98] == " " * 26
    # 98..122 (Space 24): 24 spaces
    assert payload[98:122] == " " * 24
    # 122..129 (Box 7): "001/003"
    assert payload[122:129] == "001/003"


def test_qr_decode_roundtrip_accuracy():
    sample_qr = (
        "112602110100010+001    0000006000003W2ND25350 01            000000600000"
        "LOT12345                  "
        "                        "
        "002/003"
    )
    assert len(sample_qr) == 129

    parsed = parse_qr_payload(sample_qr)
    assert parsed.po == "1126021101"
    assert parsed.po_detail == "00010"
    assert parsed.po_sub == "+001"
    assert parsed.total_qty == "60"
    assert parsed.item_code == "3W2ND25350"
    assert parsed.rev == "01"
    assert parsed.lot == "LOT12345"
    assert parsed.box == "002/003"
    assert parsed.carton_qty == "20"


# ======================================================================
# R3: QR Scan Dialog with Split (分割) and Return (戻入) Operations
# ======================================================================

def test_split_operation_generates_10010_and_20010(memory_registry):
    po = "1126081801"
    # First split for this PO generates 10010
    d1 = memory_registry.generate_split_po_detail(po)
    assert d1 == "10010"

    memory_registry.register_combo(po, "10010", "+001", "001/001")

    # Second split for the same PO generates 20010
    d2 = memory_registry.generate_split_po_detail(po)
    assert d2 == "20010"

    memory_registry.register_combo(po, "20010", "+001", "001/001")

    # Third split generates 30010
    d3 = memory_registry.generate_split_po_detail(po)
    assert d3 == "30010"


def test_return_operation_increments_d2_on_the_scanned_branch(memory_registry):
    po = "1126081802"
    # First return for this PO generates 11010
    d1 = memory_registry.generate_return_po_detail(po, "10010")
    assert d1 == "11010"

    memory_registry.register_combo(po, "11010", "+001", "001/001")

    # A second return of the same branch generates 12010.
    d2 = memory_registry.generate_return_po_detail(po, "10010")
    assert d2 == "12010"

    # A different split branch must keep its first digit.
    assert memory_registry.generate_return_po_detail(po, "20010") == "21010"


def test_qr_scan_dialog_split_workflow(tk_root):
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        dialog = QRScanDialog(root, controller)

        # 1. Simulate gun scan with a reference 129-char QR code
        sample_qr = (
            "112602110100010+001    0000006000003W2ND25350 01            000000600000"
            "                          "
            "                        "
            "001/003"
        )
        dialog.scan_input_var.set(sample_qr)
        dialog.process_scanned_code()

        # Mode defaults to Split (分割)
        assert dialog.mode_var.get() == QRScanDialog.MODE_SPLIT
        assert dialog.item_code_var.get() == "3W2ND25350"
        assert dialog.item_name_var.get() == ""
        assert dialog.rev_var.get() == "01"
        assert dialog.po_var.get() == "1126021101"
        # Auto-generated PO detail for split must be 10010
        assert dialog.po_detail_var.get() == "10010"

        # 2. Operator adjusts split quantity to 1 box of 20
        dialog.item_name_var.set("COVER REAR")
        dialog.carton_qty_var.set("20")
        dialog.box_var.set("1")  # Split 1 box -> 001/001

        # 3. Confirm and add records to print list
        dialog.confirm_and_add_records()

        assert len(state.records) == 1
        record = state.records[0]
        assert record.item_code == "3W2ND25350"
        assert record.po == "1126021101"
        assert record.po_detail == "10010"
        assert record.box == "001/001"
        assert record.carton_qty == "20"
        assert record.total_qty == "20"
        assert len(record.qr_payload) == 129
        assert record.qr_payload.startswith("112602110110010+001")

        # 4. The dialog is ready for the next split without a second scan.
        assert dialog.po_detail_var.get() == "20010"

        dialog.carton_qty_var.set("180")
        dialog.confirm_and_add_records()
        assert len(state.records) == 2
        assert state.records[1].po_detail == "20010"

        dialog.destroy()
    finally:
        state.po_registry.close()


def test_qr_scan_dialog_return_workflow(tk_root):
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        dialog = QRScanDialog(root, controller)

        # Switch mode to Return (Hoàn kho / 戻入)
        dialog._on_mode_button_changed("Hoàn kho (戻入)")
        assert dialog.mode_var.get() == QRScanDialog.MODE_RETURN

        # Scan code
        sample_qr = (
            "112608189910010+001    0000004000003V2ND00160 02            000000400000"
            "LOT-RETURN                "
            "                        "
            "001/002"
        )
        dialog.scan_input_var.set(sample_qr)
        dialog.process_scanned_code()

        # Should generate return detail 11010
        assert dialog.po_detail_var.get() == "11010"
        assert dialog.item_code_var.get() == "3V2ND00160"
        assert dialog.rev_var.get() == "02"
        assert dialog.lot_var.get() == "LOT-RETURN"
        assert dialog.item_name_var.get() == ""

        # Confirm and add
        dialog.item_name_var.set("RETURN PART")
        dialog.confirm_and_add_records()

        assert len(state.records) >= 1
        rec = state.records[-1]
        assert rec.po_detail == "11010"
        assert rec.po == "1126081899"
        assert len(rec.qr_payload) == 129
        assert rec.qr_payload.startswith("112608189911010+001")

        dialog.destroy()
    finally:
        state.po_registry.close()


def test_parse_qr_payload_122_character_legacy():
    # 122-char QR (prefix without 7-char box suffix)
    legacy_qr = (
        "112608188800010+001    000000500000ITEM-LEGACY 03           000000500000"
        "                          "
        "                        "
    )
    assert len(legacy_qr) == 122
    parsed = parse_qr_payload(legacy_qr)
    assert parsed.po == "1126081888"
    assert parsed.po_detail == "00010"
    assert parsed.po_sub == "+001"
    assert parsed.total_qty == "50"
    assert parsed.carton_qty == "50"
    assert parsed.item_code == "ITEM-LEGACY"
    assert parsed.rev == "03"
    assert parsed.box == "001/001"


def test_parse_qr_payload_scanner_crlf_and_lf():
    raw_129 = (
        "112608180100010+001    0000008000003W2ND25350 01            000000800000"
        "LOT999                    "
        "                        "
        "002/004"
    )
    # With \r\n
    parsed_crlf = parse_qr_payload(raw_129 + "\r\n")
    assert parsed_crlf.box == "002/004"
    assert parsed_crlf.total_qty == "80"
    assert parsed_crlf.carton_qty == "20"
    assert parsed_crlf.lot == "LOT999"

    # With \n
    parsed_lf = parse_qr_payload(raw_129 + "\n")
    assert parsed_lf.box == "002/004"
    assert parsed_lf.carton_qty == "20"


def test_parse_qr_payload_corrupted_short_raises():
    with pytest.raises(ValueError, match="122 ký tự"):
        parse_qr_payload("CORRUPTED_SHORT_QR_STRING")

    with pytest.raises(ValueError, match="122 ký tự"):
        parse_qr_payload("A" * 121)


def test_qr_scan_dialog_apply_to_main_form(tk_root):
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        dialog = QRScanDialog(root, controller)
        dialog._on_mode_button_changed("Phân tách (分割)")

        sample_qr = (
            "112608185500010+001    0000004000003V2ND00160 01            000000400000"
            "LOT-SPLIT                 "
            "                        "
            "001/002"
        )
        dialog.scan_input_var.set(sample_qr)
        dialog.process_scanned_code()
        assert dialog.item_name_var.get() == ""
        dialog.item_name_var.set("SPLIT PART")

        # Apply to main form
        dialog.apply_to_main_form()

        assert state.item_code_var.get() == "3V2ND00160"
        assert state.item_name_var.get() == "SPLIT PART"
        assert state.po_var.get() == "1126081855"
        assert state.po_detail_var.get() == "10010"
        assert state.rev_var.get() == "01"
        assert state.lot_var.get() == "LOT-SPLIT"
        dialog.destroy()
    finally:
        state.po_registry.close()


def test_auto_fill_po_multi_box_series_grouping(memory_registry):
    from core.slip_printer_engine import auto_fill_po

    records = [
        # Series 1: 3 boxes of ITEM-A
        create_record(
            row_number=1, item_code="ITEM-A", item_name="Item A",
            carton_qty="10", total_qty="30", po="", po_detail="", po_sub="",
            box="001/003", rev="01", lot=None
        ),
        create_record(
            row_number=2, item_code="ITEM-A", item_name="Item A",
            carton_qty="10", total_qty="30", po="", po_detail="", po_sub="",
            box="002/003", rev="01", lot=None
        ),
        create_record(
            row_number=3, item_code="ITEM-A", item_name="Item A",
            carton_qty="10", total_qty="30", po="", po_detail="", po_sub="",
            box="003/003", rev="01", lot=None
        ),
        # Single box: ITEM-B
        create_record(
            row_number=4, item_code="ITEM-B", item_name="Item B",
            carton_qty="50", total_qty="50", po="", po_detail="", po_sub="",
            box="001/001", rev="02", lot=None
        ),
    ]

    filled = auto_fill_po(records, memory_registry)
    assert len(filled) == 4

    # Rows 1, 2, 3 should share the exact same PO
    po_series_1 = filled[0].po
    assert po_series_1.startswith("11")
    assert filled[1].po == po_series_1
    assert filled[2].po == po_series_1

    # Row 4 should get the NEXT PO
    po_series_2 = filled[3].po
    assert po_series_2.startswith("11")
    assert po_series_2 != po_series_1
    assert int(po_series_2[-2:]) == int(po_series_1[-2:]) + 1


def test_parse_qr_payload_non_numeric_revision_fallback():
    # Construct QR with invalid/non-numeric rev "XX" and "00"
    base_122 = (
        "112608180100010+001    000000200000PART-ABC-99 XX           000000200000"
        + " " * 26
        + " " * 24
    )
    parsed = parse_qr_payload(base_122 + "001/001")
    assert parsed.rev == "01"
    assert parsed.item_code == "PART-ABC-99"

    # Rev "00" (invalid) falls back to "01"
    base_zero_rev = (
        "112608180100010+001    000000200000PART-ABC-99 00           000000200000"
        + " " * 26
        + " " * 24
    )
    parsed_zero = parse_qr_payload(base_zero_rev + "001/001")
    assert parsed_zero.rev == "01"


def test_parse_qr_payload_malformed_box_fallback():
    base_122 = (
        "112608180100010+001    000000200000PART-ABC-99 02           000000200000"
        + " " * 26
        + " " * 24
    )
    # Box segment with non-numeric text
    parsed_bad_text = parse_qr_payload(base_122 + "INVALID")
    assert parsed_bad_text.box == "001/001"
    assert parsed_bad_text.carton_qty == "20"

    # Box segment with curr > total (e.g. 5/2)
    parsed_invalid_range = parse_qr_payload(base_122 + "005/002")
    assert parsed_invalid_range.box == "001/001"


def test_po_detail_sequence_collision_skipping(memory_registry):
    po = "1126081801"
    # Initially, split should be 10010
    detail_1 = memory_registry.generate_split_po_detail(po)
    assert detail_1 == "10010"
    memory_registry.register_combo(po, "10010", "+001", "001/001")

    # Second split should skip 10010 and produce 20010
    detail_2 = memory_registry.generate_split_po_detail(po)
    assert detail_2 == "20010"
    memory_registry.register_combo(po, "20010", "+001", "001/001")

    # Third split should produce 30010
    detail_3 = memory_registry.generate_split_po_detail(po)
    assert detail_3 == "30010"

    # Return follows the branch carried by the scanned detail.
    ret_1 = memory_registry.generate_return_po_detail(po, "10010")
    assert ret_1 == "11010"
    memory_registry.register_combo(po, "11010", "+001", "001/001")

    # Second return of the same branch should skip 11010 and produce 12010.
    ret_2 = memory_registry.generate_return_po_detail(po, "10010")
    assert ret_2 == "12010"
    assert memory_registry.generate_return_po_detail(po, "20010") == "21010"


def test_qr_scan_dialog_split_limit_graceful_handling(tk_root):
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        dialog = QRScanDialog(root, controller)
        dialog._on_mode_button_changed("Phân tách (分割)")

        po = "1126081888"
        # Pre-register 9 splits in memory registry
        for i in range(1, 10):
            state.po_registry.register_combo(po, f"{i}0010", "+001", "001/001")

        # Now simulate scanning QR with this PO
        sample_qr = (
            f"{po:<10}00010+001    000000200000PART-ABC-99 01           000000200000"
            + " " * 26
            + " " * 24
            + "001/001"
        )
        dialog.scan_input_var.set(sample_qr)
        dialog.process_scanned_code()

        # Dialog should catch the limit error and notify gracefully without crashing
        assert "⚠️" in dialog.status_msg_var.get() or "giới hạn" in dialog.status_msg_var.get()
        assert dialog.po_detail_var.get() == "00010"

        dialog.destroy()
    finally:
        state.po_registry.close()
