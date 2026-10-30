from __future__ import annotations

import json
import tempfile
from pathlib import Path
from copy import deepcopy

import fitz
import pytest
from PIL import Image
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode import code128, code39
from reportlab.graphics.barcode import code39
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.pagesizes import A4, landscape, letter

from core.po_registry import PORegistry
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
    DEFAULT_LAYOUT_CONFIG,
    PaperLayout,
    calculate_a4_page_count,
    create_overlay_pdf,
    create_record,
    generate_pdf_from_records,
    generate_preview_image,
    get_default_layout_config,
    get_paper_layout,
    list_layout_items,
    load_layout_config,
    update_layout_item,
    validate_code39_text,
    VALID_CODE39_CHARS,
)
from ui.app_controller import AppController
from ui.app_state import AppState


@pytest.fixture
def sample_record():
    return create_record(
        row_number=1,
        item_code="3V2ND00160",
        item_name="COVER RIGHT FUSER ASSY",
        carton_qty="20",
        total_qty="60",
        po="1126090302",
        po_detail="00010",
        po_sub="+001",
        box="001/003",
        rev="01",
        lot="",
    )


# --------------------------------------------------------------------------
# 1. 1D Barcode Code128 Generation Tests
# 1. 1D Barcode Code 39 Generation Tests
# 1. 1D Barcode Code 39 Generation & Character Validation Tests
# --------------------------------------------------------------------------


def test_barcode_1d_content_10_chars_slicing():
    """Verify Code128 encodes exactly the first 10 characters with whitespace trimming."""
    """Verify Code 39 encodes exactly the first 10 characters with whitespace trimming."""
    test_cases = [
        ("3W2ND25350", "3W2ND25350"),
        ("3V2ND00160-CUSTOM-SUFFIX", "3V2ND00160"),
        ("ITEM01", "ITEM01"),
        ("  3W2ND25350  ", "3W2ND25350"),
        ("1234567890EXTRA", "1234567890"),
    ]

    for raw_code, expected_encoded in test_cases:
        encoded_text = raw_code.strip()[:10]
        assert encoded_text == expected_encoded

        bc = code39.Standard39(encoded_text, checksum=0, barWidth=0.65, barHeight=28.0, humanReadable=False)
        assert bc.value == expected_encoded
        assert bc.barWidth == 0.65
        assert bc.barHeight == 28.0
        assert bc.humanReadable is False


def test_barcode_1d_empty_or_none_handling():
    """Verify empty or None item codes are normalized without causing exceptions."""
    for empty_val in ("", "   ", None):
        code_text = (empty_val or "").strip()[:10]
        code_text = validate_code39_text(empty_val or "")
        assert code_text == ""
        # Code128 on empty string executes safely
        bc = code128.Code128(code_text, barWidth=0.7, barHeight=20.0, humanReadable=False)
        assert bc.humanReadable is False
        # Empty string handling in application logic returns empty
        assert len(code_text) == 0


def test_code39_character_validation_rejects_unsupported_chars():
    """Verify validate_code39_text rejects characters unsupported by Code 39 (e.g., '_', '@', Unicode)."""
    invalid_cases = [
        ("AB_CD12345", "_"),
        ("ITEM@123", "@"),
        ("PART#99", "#"),
        ("TEST!", "!"),
        ("ĐỒNG HỒ", "Đ"),
    ]
    for raw_code, forbidden_char in invalid_cases:
        with pytest.raises(ValueError) as exc_info:
            validate_code39_text(raw_code)
        assert "không hợp lệ đối với mã vạch 1D Code 39" in str(exc_info.value)
        assert forbidden_char in str(exc_info.value)


def test_code39_character_validation_accepts_valid_chars():
    """Verify validate_code39_text accepts all valid Code 39 characters and normalizes lowercase."""
    valid_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-. $/+%"
    for c in valid_chars.replace(" ", ""):
        assert validate_code39_text(c) == c

    # Space inside text is preserved
    assert validate_code39_text("ITEM A") == "ITEM A"

    # Lowercase conversion
    assert validate_code39_text("abc-123") == "ABC-123"

    # Truncation to 10 chars
    assert validate_code39_text("3V2ND00160-EXTRA") == "3V2ND00160"


def test_barcode_1d_human_readable_disabled_in_overlay(sample_record):
    """Verify barcode drawn on overlay PDF does not emit visible human-readable digits under the bars."""
    config = get_default_layout_config()
    buf = create_overlay_pdf([sample_record], config)
    doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    page = doc[0]

    # In overlay PDF, item_code "3V2ND00160" appears in text_positions (item_code_left_1, item_code_right_1, etc.)
    # but not as an extra standalone string directly underneath the barcode position Y=162 (ReportLab height - 162)
    text_instances = page.get_text("words")
    # Barcode position in landscape A4 (height=595.28): Y_fitz = 162.0 - 20.0 = 142.0 to 162.0
    # No text block should have Y coordinate in [162, 170] corresponding to barcode label
    barcode_text_underneath = [
        w for w in text_instances
        if 700 <= w[0] <= 830 and 160 <= w[1] <= 170
    ]
    assert len(barcode_text_underneath) == 0, f"Found unexpected text under barcode: {barcode_text_underneath}"


# --------------------------------------------------------------------------
# 2. Layout Configuration & D-Pad Integration Tests
# --------------------------------------------------------------------------


def test_barcode_1d_in_default_layout_config():
    """Verify barcode_positions exists in DEFAULT_LAYOUT_CONFIG with standard parameters."""
    config = get_default_layout_config()
    assert "barcode_positions" in config
    assert "barcode_item_code" in config["barcode_positions"]

    bc_cfg = config["barcode_positions"]["barcode_item_code"]
    assert bc_cfg["label"] == "Mã vạch 1D linh kiện (Code 39)"
    assert bc_cfg["field"] == "item_code"
    assert bc_cfg["x"] == 711
    assert bc_cfg["y"] == 162
    assert bc_cfg["width"] == 0.65
    assert bc_cfg["height"] == 28.0
    assert bc_cfg["barWidth"] == 0.65
    assert bc_cfg["barHeight"] == 28.0
    assert bc_cfg["checksum"] == 0
    assert bc_cfg["humanReadable"] is False


def test_barcode_1d_in_layout_config_json():
    """Verify layout_config.json on disk includes barcode_positions section."""
    layout_file = Path("layout_config.json")
    assert layout_file.is_file(), "layout_config.json must exist on disk"

    content = json.loads(layout_file.read_text(encoding="utf-8"))
    assert "barcode_positions" in content
    assert "barcode_item_code" in content["barcode_positions"]

    bc_disk = content["barcode_positions"]["barcode_item_code"]
    assert bc_disk["x"] == 711
    assert bc_disk["y"] == 162
    assert bc_disk["barWidth"] == 0.65
    assert bc_disk["barHeight"] == 28.0
    assert bc_disk["checksum"] == 0


def test_list_layout_items_includes_barcode():
    """Verify list_layout_items() enumerates barcode items with kind='barcode'."""
    config = get_default_layout_config()
    items = list_layout_items(config)

    barcode_items = [item for item in items if item["kind"] == "barcode"]
    assert len(barcode_items) == 1

    item = barcode_items[0]
    assert item["id"] == "barcode_item_code"
    assert item["label"] == "Mã vạch 1D linh kiện (Code 39)"
    assert item["field"] == "item_code"
    assert item["x"] == 711
    assert item["y"] == 162
    assert item["width"] == 0.65
    assert item["height"] == 28.0


def test_update_layout_item_modifies_barcode_positions():
    """Verify update_layout_item() modifies barcode_positions coordinates and dimensions."""
    config = get_default_layout_config()

    updated = update_layout_item(
        config,
        "barcode_item_code",
        x=715.0,
        y=165.0,
        width=0.70,
        height=30.0,
    )

    bc = updated["barcode_positions"]["barcode_item_code"]
    assert bc["x"] == 715.0
    assert bc["y"] == 165.0
    assert bc["width"] == 0.70
    assert bc["barWidth"] == 0.70
    assert bc["height"] == 30.0
    assert bc["barHeight"] == 30.0

    # Original config remains untouched (immutability check)
    orig_bc = config["barcode_positions"]["barcode_item_code"]
    assert orig_bc["x"] == 711
    assert orig_bc["barWidth"] == 0.65


def test_resize_layout_controller_barcode_handling(tk_root):
    """Verify controller.resize_layout() uses 0.05 step and minimum 0.1 for barcode items."""
    state = AppState(tk_root)
    controller = AppController(state)

    state.layout_choice_var.set("barcode_item_code")
    state.x_var.set("711")
    state.y_var.set("162")
    state.width_var.set("0.65")
    state.height_var.set("28.0")

    # Increase width (+1.0 direction -> 0.05 step for barcode)
    controller.resize_layout(1.0, 0.0)
    assert float(state.width_var.get()) == pytest.approx(0.70, abs=0.001)

    # Decrease width (-1.0 direction -> -0.05 step for barcode)
    controller.resize_layout(-1.0, 0.0)
    assert float(state.width_var.get()) == pytest.approx(0.65, abs=0.001)

    # Test lower bound clamping (cannot shrink below 0.1 pt)
    state.width_var.set("0.12")
    controller.resize_layout(-1.0, 0.0)
    assert float(state.width_var.get()) >= 0.1


# --------------------------------------------------------------------------
# 3. Live Canvas Preview with 1D Barcode
# --------------------------------------------------------------------------


def test_live_canvas_preview_renders_with_barcode(sample_record):
    """Verify generate_preview_image() renders 1D barcode successfully without layout breakage."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf phôi chuẩn not found in project root")

    config = get_default_layout_config()
    img = generate_preview_image(sample_record, template_path, config)

    assert isinstance(img, Image.Image)
    assert img.width > 200
    assert img.height > 200
    assert img.mode == "RGB"


# --------------------------------------------------------------------------
# 4. 6 Slips per A4 Page Layout & Pagination Tests
# --------------------------------------------------------------------------


def test_calculate_a4_page_count_ceil_formula():
    """Verify ceiling page count calculation (N + 5) // 6 for various batch sizes."""
    assert calculate_a4_page_count(0) == 0
    assert calculate_a4_page_count(-5) == 0

    # 1 to 6 slips -> 1 page
    for n in range(1, 7):
        assert calculate_a4_page_count(n) == 1, f"Expected 1 page for {n} slips"

    # 7 to 12 slips -> 2 pages
    for n in range(7, 13):
        assert calculate_a4_page_count(n) == 2, f"Expected 2 pages for {n} slips"

    # 13 to 18 slips -> 3 pages
    for n in range(13, 19):
        assert calculate_a4_page_count(n) == 3, f"Expected 3 pages for {n} slips"

    # 19 to 24 slips -> 4 pages
    for n in range(19, 25):
        assert calculate_a4_page_count(n) == 4, f"Expected 4 pages for {n} slips"


def _create_dummy_records(count: int) -> list:
    return [
        create_record(
            row_number=i,
            item_code=f"3V2ND001{i:02d}",
            item_name=f"PART NAME {i}",
            carton_qty="10",
            total_qty="100",
            po=f"1126090{i:03d}",
            po_detail="00010",
            po_sub="+001",
            box=f"{i:03d}/{count:03d}",
            rev="01",
            lot="",
        )
        for i in range(1, count + 1)
    ]


def test_6_slips_pagination_single_page(tmp_path):
    """Verify generating 1..6 slips outputs exactly 1 portrait A4 page."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf not found in project root")

    for slip_count in (1, 2, 4, 6):
        records = _create_dummy_records(slip_count)
        out_pdf = tmp_path / f"test_page_count_{slip_count}.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        doc = fitz.open(out_pdf)
        assert doc.page_count == 1, f"Expected exactly 1 page for {slip_count} slips, got {doc.page_count}"
        doc.close()


def test_6_slips_pagination_two_pages(tmp_path):
    """Verify generating 7..12 slips outputs exactly 2 portrait A4 pages."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf not found in project root")

    for slip_count in (7, 10, 12):
        records = _create_dummy_records(slip_count)
        out_pdf = tmp_path / f"test_page_count_{slip_count}.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        doc = fitz.open(out_pdf)
        assert doc.page_count == 2, f"Expected exactly 2 pages for {slip_count} slips, got {doc.page_count}"
        doc.close()


def test_6_slips_pagination_three_pages(tmp_path):
    """Verify generating 13 slips outputs exactly 3 portrait A4 pages."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf not found in project root")

    records = _create_dummy_records(13)
    out_pdf = tmp_path / "test_page_count_13.pdf"
    generate_pdf_from_records(records, template_path, out_pdf)

    doc = fitz.open(out_pdf)
    assert doc.page_count == 3, f"Expected exactly 3 pages for 13 slips, got {doc.page_count}"
    doc.close()


# --------------------------------------------------------------------------
# 5. Destination Box Geometry & Midline Alignment Tests
# --------------------------------------------------------------------------


def test_destination_box_geometry_and_margins():
    """Verify 2x3 grid destination rectangles on A4 portrait satisfy factory cutting & folding requirements."""
    assert EDI_COLUMNS == 2
    assert EDI_ROWS == 3
    assert EDI_PER_A4_PAGE == 6

    # Verify destination box dimensions (100% scale)
    assert EDI_LABEL_WIDTH == pytest.approx(273.12, abs=0.01)
    assert EDI_LABEL_HEIGHT == pytest.approx(276.24, abs=0.01)

    # Verify aspect ratio preservation
    original_aspect_ratio = EDI_TEMPLATE_CROP.width / EDI_TEMPLATE_CROP.height
    dest_aspect_ratio = EDI_LABEL_WIDTH / EDI_LABEL_HEIGHT
    assert dest_aspect_ratio == pytest.approx(original_aspect_ratio, rel=1e-4)

    # Verify margins and gaps (17.30 mm blade cut clearance gap between columns, 2.32 mm between rows with margin = 0)
    assert EDI_COLUMN_GAP == pytest.approx(49.035, abs=0.01)  # 17.30 mm
    assert EDI_ROW_GAP == pytest.approx(6.584, abs=0.01)     # 2.32 mm
    assert EDI_TOP_MARGIN == pytest.approx(0.0, abs=0.01)
    assert EDI_LEFT_MARGIN == pytest.approx(0.0, abs=0.01)

    # Verify horizontal symmetry and vertical cut gutter alignment with A4 midline (X = 297.64 pt)
    a4_w, a4_h = A4
    col0_right = EDI_LEFT_MARGIN + EDI_LABEL_WIDTH
    col1_left = col0_right + EDI_COLUMN_GAP
    cut_center_x = (col0_right + col1_left) / 2.0
    assert cut_center_x == pytest.approx(a4_w / 2.0, abs=0.05), "Cut gutter must align with A4 vertical midline"

    # Right margin must match left margin symmetrically
    col1_right = col1_left + EDI_LABEL_WIDTH
    right_margin = a4_w - col1_right
    assert right_margin == pytest.approx(EDI_LEFT_MARGIN, abs=0.05)

    # Vertical symmetry: bottom margin must match top margin symmetrically
    total_grid_height = 3 * EDI_LABEL_HEIGHT + 2 * EDI_ROW_GAP
    row2_bottom = EDI_TOP_MARGIN + total_grid_height
    bottom_margin = a4_h - row2_bottom
    assert bottom_margin == pytest.approx(EDI_TOP_MARGIN, abs=0.05)

    # All 6 slip slots must strictly fit inside the A4 portrait boundaries
    for pos in range(6):
        col = pos % EDI_COLUMNS
        row = pos // EDI_COLUMNS
        x0 = EDI_LEFT_MARGIN + col * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
        y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
        x1 = x0 + EDI_LABEL_WIDTH
        y1 = y0 + EDI_LABEL_HEIGHT

        assert 0 <= x0 < x1 <= a4_w + 1e-4
        assert 0 <= y0 < y1 <= a4_h + 1e-4


def test_letter_layout_geometry_and_margins():
    """Verify Letter paper layout provides 4 slips/page at 100% unscaled scale with 5.0 mm gaps."""
    layout = get_paper_layout("Letter")
    assert layout.name == "Letter"
    assert layout.columns == 2
    assert layout.rows == 2
    assert layout.per_page == 4

    # 100% unscaled dimensions
    assert layout.label_width == pytest.approx(EDI_LABEL_WIDTH, abs=0.01)
    assert layout.label_height == pytest.approx(EDI_LABEL_HEIGHT, abs=0.01)

    # 5.0 mm blade cut clearance gaps
    assert layout.column_gap == pytest.approx(14.17, abs=0.01)  # 5.0 mm
    assert layout.row_gap == pytest.approx(14.17, abs=0.01)     # 5.0 mm

    let_w, let_h = letter
    assert layout.page_width == pytest.approx(let_w, abs=0.01)
    assert layout.page_height == pytest.approx(let_h, abs=0.01)

    # Midline alignment (centered on Letter width: 612 / 2 = 306.0 pt)
    assert layout.midline_x == pytest.approx(let_w / 2.0, abs=0.05)

    # Symmetrical horizontal margins
    grid_w = 2 * layout.label_width + layout.column_gap
    right_margin = let_w - (layout.left_margin + grid_w)
    assert right_margin == pytest.approx(layout.left_margin, abs=0.05)

    # Symmetrical vertical margins
    grid_h = 2 * layout.label_height + layout.row_gap
    bottom_margin = let_h - (layout.top_margin + grid_h)
    assert bottom_margin == pytest.approx(layout.top_margin, abs=0.05)

    # All 4 slots strictly fit within Letter boundaries
    for pos in range(4):
        col = pos % layout.columns
        row = pos // layout.columns
        x0 = layout.left_margin + col * (layout.label_width + layout.column_gap)
        y0 = layout.top_margin + row * (layout.label_height + layout.row_gap)
        x1 = x0 + layout.label_width
        y1 = y0 + layout.label_height

        assert 0 <= x0 < x1 <= let_w
        assert 0 <= y0 < y1 <= let_h


def test_calculate_page_count_dual_paper_sizes():
    """Verify page count formula for A4 (ceil(N/6)) and Letter (ceil(N/4))."""
    # A4 checks
    assert calculate_a4_page_count(0, paper_size="A4") == 0
    assert calculate_a4_page_count(6, paper_size="A4") == 1
    assert calculate_a4_page_count(7, paper_size="A4") == 2
    assert calculate_a4_page_count(12, paper_size="A4") == 2
    assert calculate_a4_page_count(13, paper_size="A4") == 3

    # Letter checks (ceil(N/4))
    assert calculate_a4_page_count(0, paper_size="Letter") == 0
    assert calculate_a4_page_count(-1, paper_size="Letter") == 0
    assert calculate_a4_page_count(1, paper_size="Letter") == 1
    assert calculate_a4_page_count(4, paper_size="Letter") == 1
    assert calculate_a4_page_count(5, paper_size="Letter") == 2
    assert calculate_a4_page_count(8, paper_size="Letter") == 2
    assert calculate_a4_page_count(9, paper_size="Letter") == 3
    assert calculate_a4_page_count(12, paper_size="Letter") == 3
    assert calculate_a4_page_count(13, paper_size="Letter") == 4


def test_letter_pdf_generation_4_slips_per_page(tmp_path):
    """Verify generating PDF with paper_size='Letter' outputs letter-sized pages with 4 slips/page."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf not found in project root")

    # 4 slips on Letter -> exactly 1 page
    records_4 = _create_dummy_records(4)
    out_4 = tmp_path / "test_letter_4.pdf"
    generate_pdf_from_records(records_4, template_path, out_4, paper_size="Letter")

    doc = fitz.open(out_4)
    assert doc.page_count == 1
    page = doc[0]
    assert page.rect.width == pytest.approx(letter[0], abs=0.5)
    assert page.rect.height == pytest.approx(letter[1], abs=0.5)
    doc.close()

    # 5 slips on Letter -> exactly 2 pages
    records_5 = _create_dummy_records(5)
    out_5 = tmp_path / "test_letter_5.pdf"
    generate_pdf_from_records(records_5, template_path, out_5, paper_size="Letter")

    doc2 = fitz.open(out_5)
    assert doc2.page_count == 2
    for p in doc2:
        assert p.rect.width == pytest.approx(letter[0], abs=0.5)
        assert p.rect.height == pytest.approx(letter[1], abs=0.5)
    doc2.close()


def test_letter_warning_dialog_import_and_structure():
    """Verify LetterWarningDialog class can be imported and initialized without errors."""
    from ui.components.letter_warning_dialog import LetterWarningDialog
    assert callable(LetterWarningDialog)


def test_controller_paper_size_switch_workflow(tk_root):
    """Verify AppController correctly updates paper_size_var and settings when switched."""
    state = AppState(tk_root)
    controller = AppController(state)

    # Initial state is A4
    assert state.paper_size_var.get() == "A4"

    # Switch to Letter without view (headless fallback invokes confirm directly)
    controller.on_paper_size_changed("Letter")
    assert state.paper_size_var.get() == "Letter"

    # Switch back to A4
    controller.on_paper_size_changed("A4")
    assert state.paper_size_var.get() == "A4"


def test_rendered_pdf_page_size_is_a4_portrait(tmp_path):
    """Verify all output pages in generated PDF conform to standard A4 portrait (595.28 x 841.89 pt)."""
    template_path = Path("template.pdf")
    if not template_path.is_file():
        pytest.skip("template.pdf not found in project root")

    records = _create_dummy_records(8)  # 2 pages
    out_pdf = tmp_path / "test_a4_size.pdf"
    generate_pdf_from_records(records, template_path, out_pdf)

    doc = fitz.open(out_pdf)
    assert doc.page_count == 2
    for page in doc:
        rect = page.rect
        assert rect.width == pytest.approx(595.28, abs=0.1)
        assert rect.height == pytest.approx(841.89, abs=0.1)
    doc.close()


def test_generate_pdf_from_records_rejects_invalid_code39_before_registry_mutation(tmp_path):
    """Verify that if a record contains invalid Code 39 characters, generate_pdf_from_records
    raises ValueError BEFORE registering the PO combination in PORegistry.
    The registry record count must remain 0 (no leaked/poisoned combinations).
    """
    db_path = tmp_path / "test_po_registry.db"
    registry = PORegistry(db_path)
    try:
        record_with_invalid_barcode = create_record(
            row_number=1,
            item_code="AB_CD12345",
            item_name="INVALID BARCODE ITEM",
            carton_qty="10",
            total_qty="10",
            po="1126090501",
            po_detail="00010",
            po_sub="+001",
            box="001/001",
            rev="01",
            lot="",
        )

        template_path = Path("template.pdf")
        out_pdf = tmp_path / "should_not_exist.pdf"

        with pytest.raises(ValueError) as exc_info:
            generate_pdf_from_records(
                [record_with_invalid_barcode],
                template_path,
                out_pdf,
                registry=registry,
            )

        assert "AB_CD12345" in str(exc_info.value)
        assert "_" in str(exc_info.value)
        assert not out_pdf.exists()

        # CRITICAL P1 ASSERTION: Registry must NOT have registered this combo
        row = registry._conn.execute("SELECT COUNT(*) FROM po_registry").fetchone()
        count_after = row[0]
        assert count_after == 0, (
            f"Registry combination count increased to {count_after} "
            f"despite PDF generation failure!"
        )
        assert registry.count_registered() == 0
        assert not registry.is_registered("1126090501", "00010", "+001", "001/001")
    finally:
        registry.close()


def test_add_record_prevents_po_leak_after_selecting_existing_row(tk_root, tmp_path):
    """Verify that selecting an existing row does not leak its PO when adding a new record."""
    db_path = tmp_path / "po_leak_test.db"
    state = AppState(tk_root)
    state.po_registry = PORegistry(db_path)
    controller = AppController(state)

    try:
        # Step 1: Add first record (auto-generates PO 1)
        state.item_code_var.set("ITEM-ONE")
        state.item_name_var.set("Item One")
        state.carton_qty_var.set("10")
        state.box_var.set("001/001")
        state.rev_var.set("01")
        controller.add_record()

        assert len(state.records) == 1
        po1 = state.records[0].po
        assert po1.startswith("11")

        # Step 2: Add second record with different item_code (auto-generates PO 2)
        state.item_code_var.set("ITEM-TWO")
        controller.add_record()
        assert len(state.records) == 2
        po2 = state.records[1].po
        assert po2.startswith("11")
        assert po2 != po1

        # Step 3: Simulate user selecting Row 0 in the UI (loads PO1 into form fields)
        selected_record = state.records[0]
        state.item_code_var.set(selected_record.item_code)
        state.item_name_var.set(selected_record.item_name)
        state.po_var.set(selected_record.po)  # po1 loaded into form
        state.po_detail_var.set(selected_record.po_detail)
        state.po_sub_var.set(selected_record.po_sub)
        state.box_var.set(selected_record.box)
        state.rev_var.set(selected_record.rev)

        # Step 4: User changes item_code to "ITEM-THREE" without clearing PO, then clicks Add
        state.item_code_var.set("ITEM-THREE")
        controller.add_record()

        assert len(state.records) == 3
        po3 = state.records[2].po
        # CRITICAL ASSERTION: Newly added record MUST receive a fresh auto PO (PO3), NOT leaked PO1!
        assert po3 != po1, f"PO leak detected! Expected fresh auto PO, got leaked '{po1}'"
        assert po3 != po2
        assert po3.startswith("11")
    finally:
        state.po_registry.close()
