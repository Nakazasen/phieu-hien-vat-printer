"""Empirical verification script for victory auditor."""

import sys
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.slip_printer_engine import (
    create_record,
    expand_box_sequence,
    calculate_total_qty,
    normalize_box,
    build_qr_payload,
    parse_qr_payload,
    FIXED_PO_DETAIL,
    FIXED_PO_SUB,
)
from core.po_registry import PORegistry

def audit_r1():
    print("=== AUDIT R1: Box sequence & total qty ===")
    # 1. Box = 3
    boxes_3 = expand_box_sequence(3)
    assert boxes_3 == ["001/003", "002/003", "003/003"], f"Failed boxes_3: {boxes_3}"
    print(f"  [PASS] expand_box_sequence(3) -> {boxes_3}")

    # 2. Box = 1
    boxes_1 = expand_box_sequence(1)
    assert boxes_1 == ["001/001"], f"Failed boxes_1: {boxes_1}"
    print(f"  [PASS] expand_box_sequence(1) -> {boxes_1}")

    # 3. Box = "001/003"
    boxes_fmt = expand_box_sequence("001/003")
    assert boxes_fmt == ["001/003"], f"Failed boxes_fmt: {boxes_fmt}"
    print(f"  [PASS] expand_box_sequence('001/003') -> {boxes_fmt}")

    # 4. Total qty calculation: carton 20 x 3 box -> 60
    tq3 = calculate_total_qty("20", "3")
    assert tq3 == "60", f"Failed tq3: {tq3}"
    tq_fmt = calculate_total_qty("20", "001/003")
    assert tq_fmt == "60", f"Failed tq_fmt: {tq_fmt}"
    print(f"  [PASS] calculate_total_qty('20', '3') -> {tq3}")
    print(f"  [PASS] calculate_total_qty('20', '001/003') -> {tq_fmt}")

def audit_r2():
    print("=== AUDIT R2: Standardized 129-char QR code ===")
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
    print(f"  Generated payload: '{payload}'")
    print(f"  Length: {len(payload)}")
    assert len(payload) == 129, f"QR payload length {len(payload)} != 129"
    assert len(payload[:122]) == 122, f"Prefix length {len(payload[:122])} != 122"
    assert payload[122:] == "001/003", f"Suffix '{payload[122:]}' != '001/003'"
    assert payload[0:19] == "112602110100010+001"
    assert payload[19:23] == "    "
    assert payload[23:35] == "000000600000"
    assert payload[35:60] == "3W2ND25350 01            "
    assert payload[60:72] == "000000600000"
    assert payload[72:98] == " " * 26
    assert payload[98:122] == " " * 24
    print("  [PASS] 129-character payload field breakdown verified exact to spec.")

    # Roundtrip decode
    parsed = parse_qr_payload(payload)
    assert parsed.po == "1126021101"
    assert parsed.po_detail == "00010"
    assert parsed.po_sub == "+001"
    assert parsed.total_qty == "60"
    assert parsed.item_code == "3W2ND25350"
    assert parsed.rev == "01"
    assert parsed.box == "001/003"
    assert parsed.carton_qty == "20"
    print("  [PASS] QR payload decoded back into structured fields correctly.")

def audit_r3():
    print("=== AUDIT R3: Split (分割) & Return (戻入) PO generation ===")
    reg = PORegistry(":memory:")
    po = "1126081801"

    # Split sequence 10010 -> 20010 -> ... -> 90010
    splits = []
    for i in range(1, 10):
        d = reg.generate_split_po_detail(po)
        splits.append(d)
        reg.register_combo(po, d, "+001", "001/001")
    expected_splits = [f"{i}0010" for i in range(1, 10)]
    assert splits == expected_splits, f"Splits {splits} != {expected_splits}"
    print(f"  [PASS] Split PO detail sequence (10010..90010): {splits}")

    # Return sequence 11010 -> 21010 -> ... -> 91010
    returns = []
    for i in range(1, 10):
        d = reg.generate_return_po_detail(po)
        returns.append(d)
        reg.register_combo(po, d, "+001", "001/001")
    expected_returns = [f"{i}1010" for i in range(1, 10)]
    assert returns == expected_returns, f"Returns {returns} != {expected_returns}"
    print(f"  [PASS] Return PO detail sequence (11010..91010): {returns}")
    reg.close()

if __name__ == "__main__":
    audit_r1()
    audit_r2()
    audit_r3()
    print("\nALL EMPIRICAL AUDIT CHECKS PASSED.")
