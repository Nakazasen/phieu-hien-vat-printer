from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import fitz
import openpyxl
import pytest
from PIL import Image
from pyzbar.pyzbar import decode
from reportlab.lib.pagesizes import A4

from core.po_registry import (
    FIXED_PO_DETAIL,
    FIXED_PO_SUB,
    DuplicateComboError,
    PORegistry,
)
from core.slip_printer_engine import (
    EDI_COLUMNS,
    EDI_ROWS,
    EDI_PER_A4_PAGE,
    EDI_LABEL_WIDTH,
    EDI_LABEL_HEIGHT,
    EDI_LEFT_MARGIN,
    EDI_TOP_MARGIN,
    EDI_COLUMN_GAP,
    EDI_ROW_GAP,
    EDI_TEMPLATE_CROP,
    START_ROW,
    SlipRecord,
    build_qr_payload,
    calculate_a4_page_count,
    calculate_total_qty,
    create_record,
    expand_box_sequence,
    generate_pdf_from_records,
    generate_preview_image,
    get_default_layout_config,
    load_layout_config,
    normalize_box,
    parse_qr_payload,
    read_records,
    validate_records,
)
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.qr_scan_dialog import QRScanDialog


# --------------------------------------------------------------------------
# Helper Fixtures & Builders
# --------------------------------------------------------------------------

@pytest.fixture
def template_path():
    path = Path("template.pdf")
    if not path.is_file():
        pytest.skip("template.pdf not found in project root")
    return path


def _build_test_records(count: int, po_prefix: str = "11260903") -> list[SlipRecord]:
    """Create N valid test SlipRecord objects with unique item codes and sequential boxes."""
    records = []
    for i in range(1, count + 1):
        records.append(
            create_record(
                row_number=i,
                item_code=f"3V2ND001{i:02d}",
                item_name=f"MODULE ASSY PART {i}",
                carton_qty="15",
                total_qty=str(15 * count),
                po=f"{po_prefix}{i:02d}",
                po_detail="00010",
                po_sub="+001",
                box=f"{i:03d}/{count:03d}",
                rev="01",
                lot=f"LOT{i:04d}",
            )
        )
    return records


def _decode_page_symbols(page) -> tuple[list, list]:
    """Decode barcodes and QR codes from a page by cropping each of the 6 slip slots."""
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    scale = 300 / 72.0
    barcodes = []
    qrcodes = []
    for slot in range(6):
        col = slot % EDI_COLUMNS
        row = slot // EDI_COLUMNS
        x0 = int((EDI_LEFT_MARGIN + col * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)) * scale)
        y0 = int((EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)) * scale)
        x1 = int(x0 + EDI_LABEL_WIDTH * scale)
        y1 = int(y0 + EDI_LABEL_HEIGHT * scale)
        slot_crop = img.crop((x0, y0, x1, y1))
        slot_symbols = decode(slot_crop)
        barcodes.extend([s for s in slot_symbols if s.type in ("CODE39", "CODE128")])
        qrcodes.extend([s for s in slot_symbols if s.type == "QRCODE"])
    return barcodes, qrcodes


# ==========================================================================
# TEST SUITE 1: End-to-End PDF Generation & Multi-Page Layout Stress
# ==========================================================================

class TestEndToEndPDFGenerationStress:
    """Adversarial stress-testing of PDF generation, pagination, and barcode/QR rendering."""

    def test_e2e_pdf_generation_6_slips(self, template_path, tmp_path):
        """Verify 6 slips generate exactly 1 portrait A4 page with 6 complete slips."""
        records = _build_test_records(6, po_prefix="11260910")
        out_pdf = tmp_path / "e2e_6_slips.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        assert out_pdf.is_file()
        doc = fitz.open(out_pdf)
        try:
            assert doc.page_count == 1, f"Expected 1 page for 6 slips, got {doc.page_count}"
            page = doc[0]
            assert page.rect.width == pytest.approx(A4[0], abs=0.1)
            assert page.rect.height == pytest.approx(A4[1], abs=0.1)

            drawings = page.get_drawings()
            # Verify exactly 6 slip slots populated with drawings
            for slot in range(6):
                col = slot % EDI_COLUMNS
                row = slot // EDI_COLUMNS
                x0 = EDI_LEFT_MARGIN + col * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
                y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
                rect = fitz.Rect(x0, y0, x0 + EDI_LABEL_WIDTH, y0 + EDI_LABEL_HEIGHT)
                slot_drawings = [d for d in drawings if rect.intersects(d["rect"])]
                assert len(slot_drawings) > 0, f"Slot {slot} on page 1 has no drawings"

            barcodes, qrcodes = _decode_page_symbols(page)
            assert len(barcodes) == 6, f"Expected 6 barcodes, decoded {len(barcodes)}"
            assert len(qrcodes) == 6, f"Expected 6 QR codes, decoded {len(qrcodes)}"

            # Verify barcode values match 10-char item codes
            decoded_bc_values = {b.data.decode("latin1").strip() for b in barcodes}
            expected_bc_values = {r.item_code[:10] for r in records}
            assert decoded_bc_values == expected_bc_values
        finally:
            doc.close()

    def test_e2e_pdf_generation_12_slips(self, template_path, tmp_path):
        """Verify 12 slips generate exactly 2 portrait A4 pages, 6 slips per page."""
        records = _build_test_records(12, po_prefix="11260920")
        out_pdf = tmp_path / "e2e_12_slips.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        assert out_pdf.is_file()
        doc = fitz.open(out_pdf)
        try:
            assert doc.page_count == 2, f"Expected 2 pages for 12 slips, got {doc.page_count}"

            # Verify both pages
            for pno in range(2):
                page = doc[pno]
                barcodes, qrcodes = _decode_page_symbols(page)

                assert len(barcodes) == 6, f"Page {pno + 1}: expected 6 barcodes, got {len(barcodes)}"
                assert len(qrcodes) == 6, f"Page {pno + 1}: expected 6 QR codes, got {len(qrcodes)}"

                page_records = records[pno * 6 : (pno + 1) * 6]
                decoded_bc_values = {b.data.decode("latin1").strip() for b in barcodes}
                expected_bc_values = {r.item_code[:10] for r in page_records}
                assert decoded_bc_values == expected_bc_values
        finally:
            doc.close()

    def test_e2e_pdf_generation_13_slips(self, template_path, tmp_path):
        """Verify 13 slips generate exactly 3 pages: 6 on P1, 6 on P2, 1 on P3 (slots 1-5 blank)."""
        records = _build_test_records(13, po_prefix="11260930")
        out_pdf = tmp_path / "e2e_13_slips.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        assert out_pdf.is_file()
        doc = fitz.open(out_pdf)
        try:
            assert doc.page_count == 3, f"Expected 3 pages for 13 slips, got {doc.page_count}"

            # Page 1: 6 slips
            b1, _ = _decode_page_symbols(doc[0])
            assert len(b1) == 6

            # Page 2: 6 slips
            b2, _ = _decode_page_symbols(doc[1])
            assert len(b2) == 6

            # Page 3: exactly 1 slip in slot 0, slots 1-5 must be completely empty
            p3 = doc[2]
            p3_drawings = p3.get_drawings()

            # Slot 0 (col=0, row=0) has drawings
            slot0_rect = fitz.Rect(
                EDI_LEFT_MARGIN,
                EDI_TOP_MARGIN,
                EDI_LEFT_MARGIN + EDI_LABEL_WIDTH,
                EDI_TOP_MARGIN + EDI_LABEL_HEIGHT,
            )
            slot0_drawings = [d for d in p3_drawings if slot0_rect.intersects(d["rect"])]
            assert len(slot0_drawings) > 0, "Page 3 Slot 0 must contain drawings"

            # Slots 1..5 must have 0 drawings
            for slot in range(1, 6):
                col = slot % EDI_COLUMNS
                row = slot // EDI_COLUMNS
                x0 = EDI_LEFT_MARGIN + col * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
                y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
                rect = fitz.Rect(x0 + 10, y0 + 10, x0 + EDI_LABEL_WIDTH - 10, y0 + EDI_LABEL_HEIGHT - 10)
                slot_drawings = [d for d in p3_drawings if rect.intersects(d["rect"])]
                assert len(slot_drawings) == 0, f"Page 3 Slot {slot} must be empty, found {len(slot_drawings)}"

            # Decode Page 3 symbols: exactly 1 barcode and 1 QR code
            p3_barcodes, p3_qrcodes = _decode_page_symbols(p3)

            assert len(p3_barcodes) == 1, f"Page 3 expected 1 barcode, got {len(p3_barcodes)}"
            assert len(p3_qrcodes) == 1, f"Page 3 expected 1 QR code, got {len(p3_qrcodes)}"
            assert p3_barcodes[0].data.decode("latin1").strip() == records[12].item_code[:10]
        finally:
            doc.close()

    def test_barcode_and_qr_distortion_free_aspect_ratio(self, template_path, tmp_path):
        """Verify barcode and QR codes are not distorted, retaining aspect ratios."""
        records = _build_test_records(1, po_prefix="11260940")
        out_pdf = tmp_path / "e2e_distortion_check.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        doc = fitz.open(out_pdf)
        try:
            page = doc[0]
            bc_symbols, qr_symbols = _decode_page_symbols(page)

            assert len(qr_symbols) >= 1
            qr = qr_symbols[0]
            # QR code must be square within a 5% margin (no stretching)
            qr_w, qr_h = qr.rect.width, qr.rect.height
            aspect = qr_w / qr_h
            assert 0.95 <= aspect <= 1.05, f"QR code aspect ratio distorted: {aspect} ({qr_w}x{qr_h})"

            # Barcode must be wider than tall
            assert len(bc_symbols) >= 1
            bc = bc_symbols[0]
            assert bc.rect.width > bc.rect.height, "Barcode should be horizontal"
        finally:
            doc.close()


# ==========================================================================
# TEST SUITE 2: Full Core Workflow Regression Stress
# ==========================================================================

class TestCoreWorkflowRegressionStress:
    """Stress-test QR scanning workflows, Auto PO generation, Excel import, and Live Preview."""

    # ----------------------------------------------------------------------
    # A. QR Scan Workflows (Split, Return, Decode)
    # ----------------------------------------------------------------------

    def test_qr_scan_split_workflow_10010_to_20010_sequence(self, tmp_path):
        """Verify split mode produces 10010 -> 20010 -> 30010 sequence."""
        db_path = tmp_path / "test_split.db"
        registry = PORegistry(db_path)
        try:
            po = "1126091801"
            # 1. First split generates 10010
            d1 = registry.generate_split_po_detail(po)
            assert d1 == "10010"
            registry.register_combo(po, d1, "+001", "001/001")

            # 2. Second split generates 20010
            d2 = registry.generate_split_po_detail(po)
            assert d2 == "20010"
            registry.register_combo(po, d2, "+001", "001/001")

            # 3. Third split generates 30010
            d3 = registry.generate_split_po_detail(po)
            assert d3 == "30010"

            # 4. In-memory exclusions skip already generated/staged details
            d_skip = registry.generate_split_po_detail(po, exclude_details=["30010", "40010"])
            assert d_skip == "50010"
        finally:
            registry.close()

    def test_qr_scan_return_workflow_10010_to_11010_sequence(self, tmp_path):
        """Verify return mode produces 10010 -> 11010 on branch 1 and 20010 -> 21010 on branch 2."""
        db_path = tmp_path / "test_return.db"
        registry = PORegistry(db_path)
        try:
            po = "1126091802"
            # 1. Return of split 10010 generates 11010
            r1 = registry.generate_return_po_detail(po, "10010")
            assert r1 == "11010"
            registry.register_combo(po, r1, "+001", "001/001")

            # 2. Second return of branch 1 generates 12010
            r2 = registry.generate_return_po_detail(po, "10010")
            assert r2 == "12010"

            # 3. Return of split 20010 generates 21010
            r_branch2 = registry.generate_return_po_detail(po, "20010")
            assert r_branch2 == "21010"
        finally:
            registry.close()

    def test_qr_decode_mode_122_and_129_payloads(self):
        """Verify payload decoding for 122-char legacy and 129-char full payloads."""
        # 122-char legacy payload
        payload_122 = (
            "112608188800010+001    000000050000ITEM-LEGACY 03           000000050000"
            "                          "
            "                        "
        )
        assert len(payload_122) == 122
        parsed_122 = parse_qr_payload(payload_122)
        assert parsed_122.po == "1126081888"
        assert parsed_122.po_detail == "00010"
        assert parsed_122.po_sub == "+001"
        assert parsed_122.item_code == "ITEM-LEGACY"
        assert parsed_122.carton_qty == "50"
        assert parsed_122.total_qty == "50"
        assert parsed_122.box == "001/001"  # Default fallback

        # 129-char full payload
        payload_129 = (
            "112608189910010+001    0000000600003W2ND25350 01            000000020000"
            "LOT-XYZ                   "
            "                        "
            "002/003"
        )
        assert len(payload_129) == 129
        parsed_129 = parse_qr_payload(payload_129)
        assert parsed_129.po == "1126081899"
        assert parsed_129.po_detail == "10010"
        assert parsed_129.item_code == "3W2ND25350"
        assert parsed_129.box == "002/003"
        assert parsed_129.carton_qty == "20"
        assert parsed_129.total_qty == "60"
        assert parsed_129.lot == "LOT-XYZ"

        # Scanner line endings handling (\r\n and \n)
        parsed_crlf = parse_qr_payload(payload_129 + "\r\n")
        assert parsed_crlf.box == "002/003"
        assert parsed_crlf.item_code == "3W2ND25350"

        # Round-trip verification
        rec = create_record(
            row_number=1,
            item_code="3W2ND25350",
            item_name="COVER",
            carton_qty="20",
            total_qty="60",
            po="1126081899",
            po_detail="10010",
            po_sub="+001",
            box="002/003",
            rev="01",
            lot="LOT-XYZ",
        )
        built_payload = build_qr_payload(rec)
        assert len(built_payload) == 129
        parsed_back = parse_qr_payload(built_payload)
        assert parsed_back.item_code == rec.item_code
        assert parsed_back.po == rec.po
        assert parsed_back.po_detail == rec.po_detail
        assert parsed_back.box == rec.box

    # ----------------------------------------------------------------------
    # B. Auto PO Generation & Concurrency Locking / Auto-Recovery
    # ----------------------------------------------------------------------

    def test_auto_po_generation_sequence(self, tmp_path):
        """Verify Auto PO generates strict 11YYMMDDNN format and increments sequentially."""
        db_path = tmp_path / "test_auto_po.db"
        registry = PORegistry(db_path)
        try:
            today_prefix = "11" + datetime.now().strftime("%y%m%d")
            po1 = registry.generate_po()
            po2 = registry.generate_po()
            po3 = registry.generate_po()

            assert po1.startswith(today_prefix)
            assert len(po1) == 10
            assert po1[-2:] == "01"
            assert po2[-2:] == "02"
            assert po3[-2:] == "03"
        finally:
            registry.close()

    def test_auto_po_concurrency_locking(self, tmp_path):
        """Adversarially test multi-threaded PO generation to verify zero duplicates."""
        db_path = tmp_path / "concurrent_po.db"
        registry = PORegistry(db_path)
        generated_pos: list[str] = []
        lock = threading.Lock()
        errors: list[Exception] = []

        def worker():
            try:
                # Open separate connection per thread to simulate network LAN concurrency
                thread_reg = PORegistry(db_path)
                for _ in range(5):
                    po = thread_reg.generate_po()
                    with lock:
                        generated_pos.append(po)
                thread_reg.close()
            except Exception as exc:
                with lock:
                    errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        registry.close()

        assert len(errors) == 0, f"Concurrency errors occurred: {errors}"
        assert len(generated_pos) == 30
        # Absolutely zero duplicates
        assert len(set(generated_pos)) == 30, "Duplicate PO generated during concurrent access!"

    def test_database_auto_recovery_from_corruption(self, tmp_path):
        """Verify database auto-recovery rescues application when SQLite file is corrupted."""
        db_path = tmp_path / "corrupted_reg.db"
        # 1. Initialize valid DB
        reg = PORegistry(db_path)
        po1 = reg.generate_po()
        assert po1.endswith("01")
        reg.close()

        # 2. Intentionally corrupt the file with garbage bytes
        with open(db_path, "wb") as f:
            f.write(b"CORRUPTED_GARBAGE_DATA_NOT_A_VALID_SQLITE_HEADER\x00\xff\xfe\x00")

        # 3. PORegistry should detect corruption, backup corrupted file, and re-initialize
        reg2 = PORegistry(db_path)
        try:
            # Operation must succeed via _execute_with_auto_recovery
            po_new = reg2.generate_po()
            assert po_new.startswith("11")
            assert len(po_new) == 10
            # Corruption backup file must exist
            backup_files = list(tmp_path.glob("*_corrupted_*.bak"))
            assert len(backup_files) >= 1, "Expected corruption backup file to be created"
        finally:
            reg2.close()

    # ----------------------------------------------------------------------
    # C. Excel Import: Sequence Expansion & Duplicate Combo Rejection
    # ----------------------------------------------------------------------

    def test_excel_import_sequence_expansion(self, tmp_path):
        """Verify integer box count expands into sequential multi-box records."""
        # 1. Test expand_box_sequence directly on integer and string representations
        boxes = expand_box_sequence(3)
        assert boxes == ["001/003", "002/003", "003/003"]
        assert expand_box_sequence("3") == ["001/003", "002/003", "003/003"]
        assert expand_box_sequence("1") == ["001/001"]

        # 2. Test reading from Excel file and verifying structure
        excel_path = tmp_path / "expand_test.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        # Write 1 record with box="3"
        ws.cell(row=START_ROW, column=1, value="3W2ND25350")
        ws.cell(row=START_ROW, column=2, value="COVER REAR")
        ws.cell(row=START_ROW, column=3, value="")  # total_qty empty -> to be calculated
        ws.cell(row=START_ROW, column=4, value="20")  # carton_qty = 20
        ws.cell(row=START_ROW, column=5, value="1126090101")
        ws.cell(row=START_ROW, column=6, value="00010")
        ws.cell(row=START_ROW, column=7, value="+001")
        ws.cell(row=START_ROW, column=8, value="3")  # Integer 3
        ws.cell(row=START_ROW, column=9, value="01")
        ws.cell(row=START_ROW, column=10, value="LOT99")
        wb.save(excel_path)
        wb.close()

        raw_records = read_records(excel_path)
        assert len(raw_records) == 1
        raw = raw_records[0]

        # In application workflow (add_record / batch expansion), integer box 3 produces 3 records
        expanded_boxes = expand_box_sequence(3)
        expanded = []
        for b in expanded_boxes:
            t_qty = calculate_total_qty(raw.carton_qty, b)
            expanded.append(create_record(
                row_number=raw.row_number,
                item_code=raw.item_code,
                item_name=raw.item_name,
                carton_qty=raw.carton_qty,
                total_qty=t_qty,
                po=raw.po,
                po_detail=raw.po_detail,
                po_sub=raw.po_sub,
                box=b,
                rev=raw.rev,
                lot=raw.lot,
            ))

        assert len(expanded) == 3
        assert [r.box for r in expanded] == ["001/003", "002/003", "003/003"]
        assert all(r.total_qty == "60" for r in expanded)
        assert all(r.po == "1126090101" for r in expanded)

    def test_duplicate_combo_rejection_in_validation(self, tmp_path):
        """Verify DuplicateComboError is raised when importing/validating duplicate EDI combos."""
        db_path = tmp_path / "dup_check.db"
        registry = PORegistry(db_path)
        try:
            # Register an existing combo
            registry.register_combo("PO_EXISTS_01", "00010", "+001", "001/001")

            record = create_record(
                row_number=1,
                item_code="3W2ND25350",
                item_name="COVER",
                carton_qty="20",
                total_qty="20",
                po="PO_EXISTS_01",
                po_detail="00010",
                po_sub="+001",
                box="001/001",
                rev="01",
                lot="",
            )

            # Validating with registry MUST raise DuplicateComboError
            with pytest.raises(DuplicateComboError) as exc_info:
                validate_records([record], registry=registry)
            assert "PO_EXISTS_01" in str(exc_info.value)
        finally:
            registry.close()

    # ----------------------------------------------------------------------
    # D. Live Preview Rendering
    # ----------------------------------------------------------------------

    def test_live_preview_rendering_robustness(self, template_path):
        """Verify generate_preview_image produces clean PIL Image across diverse inputs."""
        config = get_default_layout_config()

        test_records = [
            # Standard record
            create_record(
                row_number=1,
                item_code="3V2ND00160",
                item_name="COVER RIGHT FUSER",
                carton_qty="20",
                total_qty="60",
                po="1126090302",
                po_detail="00010",
                po_sub="+001",
                box="001/003",
                rev="01",
                lot="",
            ),
            # Empty lot and unicode in item name
            create_record(
                row_number=2,
                item_code="ITEM-SHORT",
                item_name="NAME WITH UNICODE ĐỒNG HỒ",
                carton_qty="5",
                total_qty="5",
                po="1126090303",
                po_detail="00010",
                po_sub="+001",
                box="001/001",
                rev="01",
                lot="",
            ),
            # Long item code (>10 chars, sliced for barcode)
            create_record(
                row_number=3,
                item_code="LONGITEMCODE123456",
                item_name="LONG NAME TEST",
                carton_qty="100",
                total_qty="500",
                po="1126090304",
                po_detail="10010",
                po_sub="+001",
                box="002/005",
                rev="99",
                lot="LOT-998877",
            ),
        ]

        for record in test_records:
            img = generate_preview_image(record, template_path, config)
            assert isinstance(img, Image.Image)
            assert img.mode == "RGB"
            assert img.width > 200
            assert img.height > 200

            # Verify toggling options doesn't crash preview
            config_options = dict(config)
            config_options["options"] = {
                "hide_total_qty_on_slip": False,
                "hide_package_qty_box": False,
            }
            img_toggled = generate_preview_image(record, template_path, config_options)
            assert isinstance(img_toggled, Image.Image)
