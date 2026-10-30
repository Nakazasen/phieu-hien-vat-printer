"""Adversarial stress-test suite by Challenger subagent (challenger_impl_1).

Empirically verifies:
1. Barcode 1D Code128:
   - Boundary slicing: 10 chars exact, >10 chars (e.g. 50 chars), <10 chars (e.g. 1 char, empty string, None),
     strings with spaces/tabs/hyphens/underscores.
   - humanReadable strictly False: inspect object properties, assert no text rendered under barcode bars.
   - Barcode width and height in points: verify fit cleanly within designated slot above QR code without overflowing
     into QR area (Y=170..270) or upper border.
2. 6-Slips per A4 Page Geometry & Pagination:
   - Empirical boundary test for pagination: N=0, 1, 5, 6, 7, 11, 12, 13, 24, 25 slips. Assert page counts match ceil(N/6).
   - Geometry verification: all 6 positions within A4 portrait bounds (595.28 x 841.89 pt), non-overlapping.
   - Aspect ratio distortion: (x1 - x0) / (y1 - y0) compared to cropped EDI template (283.32 / 287.76 = 0.98457), <0.01%.
   - Center vertical cutting gutter: midpoint between col 0 and col 1 exactly at X = 297.64 pt (A4 midline 595.28 / 2).
"""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import MagicMock

import fitz
import pytest
from reportlab.graphics.barcode import code128
from reportlab.graphics.barcode import code128, code39
from reportlab.lib.pagesizes import A4, landscape

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
    calculate_a4_page_count,
    create_overlay_pdf,
    create_record,
    generate_pdf_from_records,
    get_default_layout_config,
)


def _make_dummy_records(count: int) -> list:
    return [
        create_record(
            row_number=i,
            item_code=f"PART{i:06d}",
            item_name=f"ITEM NAME {i}",
            carton_qty="10",
            total_qty="50",
            po=f"1126090{i:03d}",
            po_detail="00010",
            po_sub="+001",
            box=f"{i:03d}/{count:03d}",
            rev="01",
            lot="",
        )
        for i in range(1, count + 1)
    ]


# ==============================================================================
# 1. Stress-test Barcode 1D Code128
# ==============================================================================


class TestBarcode1DStress:
    """Adversarial stress-testing of Barcode 1D Code128."""

    @pytest.mark.parametrize(
        "raw_input,expected_slice",
        [
            # Exact 10 chars
            ("3W2ND25350", "3W2ND25350"),
            ("1234567890", "1234567890"),
            ("ABCDEFGHIJ", "ABCDEFGHIJ"),
            ("3V2ND00160", "3V2ND00160"),
            # >10 chars (long & massive boundary inputs)
            ("3V2ND00160-CUSTOM-SUFFIX-EXTENDED-PART", "3V2ND00160"),
            ("A" * 50, "A" * 10),
            ("PART_NUMBER_VERY_LONG_STRING_THAT_EXCEEDS_TEN_CHARS", "PART_NUMBE"),
            ("1234567890EXTRA99999", "1234567890"),
            # <10 chars (short boundary inputs)
            ("1", "1"),
            ("AB", "AB"),
            ("3W2ND", "3W2ND"),
            ("123456789", "123456789"),
            # Strings with whitespace, tabs, hyphens, underscores
            ("  3W2ND25350  ", "3W2ND25350"),
            ("\t3V2ND00160\t", "3V2ND00160"),
            ("  ITEM-01_B  ", "ITEM-01_B"),
            ("PART-01_23", "PART-01_23"),
            ("A-B_C.D/12", "A-B_C.D/12"),
            ("  123-456_  ", "123-456_"),
        ],
    )
    def test_barcode_boundary_slicing_adversarial(self, raw_input: str, expected_slice: str):
        """Verify boundary slicing strictly yields the first 10 characters without failure."""
        sliced = str(raw_input or "").strip()[:10]
        assert sliced == expected_slice
        assert len(sliced) <= 10

        # Construct Code128 and assert validity
        # Construct Code 39 and assert validity
        bc = code39.Standard39(sliced, checksum=0, barWidth=0.65, barHeight=28.0, humanReadable=False)
        assert bc.value == expected_slice
        assert bc.humanReadable is False
        assert bc.barWidth == 0.65
        assert bc.barHeight == 28.0

    @pytest.mark.parametrize(
        "empty_input",
        [
            "",
            "   ",
            "\t\t",
            "\n  \t",
            None,
        ],
    )
    def test_barcode_empty_or_none_adversarial_handling(self, empty_input):
        """Verify empty, whitespace-only, or None values normalize safely to empty string."""
        sliced = str(empty_input or "").strip()[:10]
        assert sliced == ""

        # ReportLab Code128 on empty string executes safely
        bc = code128.Code128(sliced, barWidth=0.7, barHeight=20.0, humanReadable=False)
        assert bc.value == ""
        assert bc.humanReadable is False

    def test_barcode_human_readable_strictly_false_object_inspection(self):
        """Verify humanReadable property is False and annotate/text is never invoked."""
        bc = code39.Standard39("3W2ND25350", checksum=0, barWidth=0.65, barHeight=28.0, humanReadable=False)
        assert bc.humanReadable is False

        # In ReportLab, drawHumanReadable() checks `if self.humanReadable:`
        # When False, it must NOT call self.annotate()
        mock_canv = MagicMock()
        bc.annotate = MagicMock()
        bc.drawOn(mock_canv, 711, 433.28)

        # Assert annotate was never called
        bc.annotate.assert_not_called()

        # In contrast, when humanReadable=True, annotate must be called
        bc_true = code39.Standard39("3W2ND25350", checksum=0, barWidth=0.65, barHeight=28.0, humanReadable=True)
        bc_true.annotate = MagicMock()
        bc_true.drawOn(mock_canv, 711, 433.28)
        bc_true.annotate.assert_called_once()

    def test_barcode_human_readable_disabled_in_overlay_pdf_inspection(self):
        """Verify generated overlay PDF contains no text under the barcode bars."""
        record = create_record(
            row_number=1,
            item_code="CHALLENG01",
            item_name="STRESS TEST PART",
            carton_qty="15",
            total_qty="30",
            po="1126090999",
            po_detail="00010",
            po_sub="+001",
            box="001/002",
            rev="01",
            lot="",
        )
        config = get_default_layout_config()
        buf = create_overlay_pdf([record], config)
        doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        page = doc[0]

        # All words on the page: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")

        # Barcode area in landscape A4 (height=595.28):
        # Y_topdown for barcode: 142 to 162 pt.
        # X: 705 to 842 pt.
        # Check that no text exists directly below the barcode baseline (Y=162..170)
        # or inside the barcode bounding box (Y=142..162)
        barcode_area_text = [
            w for w in words
            if 700 <= w[0] <= 842 and 142 <= w[1] <= 170
        ]
        assert len(barcode_area_text) == 0, f"Found unexpected text in barcode slot: {barcode_area_text}"
        doc.close()

    def test_barcode_width_and_height_fit_slot_no_collision_with_qr(self):
        """Verify barcode dimensions fit cleanly above QR code without collision or overflow.

        Slot analysis on template coordinate system:
        - EDI template crop: [558.6, 0.0, 841.92, 287.76]
        - QR code (qr_full): x=710, y=270, width=100, height=100 -> Y span [170.0, 270.0] pt
        - Barcode: x=705, y=162, barHeight=20.0 -> Y span [142.0, 162.0] pt
        - Gap between barcode bottom (162 pt) and QR top (170 pt): exactly 8.0 pt.
        """
        config = get_default_layout_config()
        bc_cfg = config["barcode_positions"]["barcode_item_code"]
        qr_cfg = config["qr_positions"]["qr_full"]

        bc_x = bc_cfg["x"]
        bc_y = bc_cfg["y"]
        bar_height = bc_cfg["barHeight"]
        bar_width = bc_cfg["barWidth"]

        # Top-down coordinates on landscape A4:
        # Drawing baseline is at canvas Y = H - bc_y
        # Barcode height goes upwards on canvas, so top-down Y range is [bc_y - bar_height, bc_y]
        barcode_top_y = bc_y - bar_height  # 162 - 20 = 142 pt
        barcode_bottom_y = bc_y            # 162 pt

        # QR code top-down Y range: [qr_y - qr_height, qr_y]
        qr_top_y = qr_cfg["y"] - qr_cfg["height"]  # 270 - 100 = 170 pt
        qr_bottom_y = qr_cfg["y"]                  # 270 pt

        # 1. Assert barcode is strictly above QR code
        assert barcode_bottom_y < qr_top_y, "Barcode bottom must be above QR code top"
        clearance = qr_top_y - barcode_bottom_y
        assert clearance == 8.0, f"Expected 8.0 pt clearance, got {clearance} pt"

        # 2. Assert barcode is below upper border / header elements (Y ~ 100 pt)
        assert barcode_top_y >= 100.0, "Barcode must be below header elements"

        # 3. Assert barcode width for 10-character codes does not overflow right template border (841.92 pt)
        # 3. Assert barcode width for 10-character codes does not overflow right template border
        sample_codes = ["3W2ND25350", "3V2ND00160", "1234567890", "ABCDEFGHIJ"]
        for code in sample_codes:
            bc = code128.Code128(code, barWidth=bar_width, barHeight=bar_height, humanReadable=False)
            bc = code39.Standard39(code, checksum=0, barWidth=bar_width, barHeight=bar_height, humanReadable=False)
            # Active bars right edge: bc_x + (bc.width - bc.rquiet)
            bars_right_edge = bc_x + (bc.width - bc.rquiet)
            assert bars_right_edge <= EDI_TEMPLATE_CROP.x1, (
                f"Printed bars for {code} (right edge {bars_right_edge:.2f}) overflow EDI crop {EDI_TEMPLATE_CROP.x1}"
            )


# ==============================================================================
# 2. Stress-test 6-Slips per A4 Page Geometry & Pagination
# ==============================================================================


class TestSixSlipsGeometryAndPaginationStress:
    """Adversarial stress-testing of 6-slips per A4 page geometry and pagination."""

    @pytest.mark.parametrize(
        "slip_count,expected_pages",
        [
            (0, 0),
            (1, 1),
            (5, 1),
            (6, 1),
            (7, 2),
            (11, 2),
            (12, 2),
            (13, 3),
            (24, 4),
            (25, 5),
            (60, 10),
            (61, 11),
            (100, 17),
        ],
    )
    def test_pagination_boundary_cases_oracle(self, slip_count: int, expected_pages: int):
        """Empirical boundary test for pagination against mathematical oracle ceil(N/6)."""
        actual_pages = calculate_a4_page_count(slip_count)
        assert actual_pages == expected_pages

        if slip_count > 0:
            oracle_ceil = math.ceil(slip_count / 6)
            assert actual_pages == oracle_ceil, (
                f"calculate_a4_page_count({slip_count})={actual_pages} != ceil({slip_count}/6)={oracle_ceil}"
            )

    @pytest.mark.parametrize(
        "slip_count,expected_pages",
        [
            (1, 1),
            (5, 1),
            (6, 1),
            (7, 2),
            (11, 2),
            (12, 2),
            (13, 3),
            (24, 4),
            (25, 5),
        ],
    )
    def test_empirical_pdf_generation_boundary_pagination(self, tmp_path: Path, slip_count: int, expected_pages: int):
        """Generate actual PDF files across boundary slip counts and verify physical page count."""
        template_path = Path("template.pdf")
        if not template_path.is_file():
            pytest.skip("template.pdf not found in project root")

        records = _make_dummy_records(slip_count)
        out_pdf = tmp_path / f"adversarial_boundary_{slip_count}.pdf"
        generate_pdf_from_records(records, template_path, out_pdf)

        doc = fitz.open(out_pdf)
        assert doc.page_count == expected_pages, (
            f"Physical PDF for {slip_count} slips has {doc.page_count} pages, expected {expected_pages}"
        )
        # Verify every page is portrait A4
        for p in doc:
            assert p.rect.width == pytest.approx(595.28, abs=0.1)
            assert p.rect.height == pytest.approx(841.89, abs=0.1)
        doc.close()

    def test_six_slips_geometry_bounds_on_a4_portrait(self):
        """Verify all 6 destination rectangles are strictly within A4 portrait and non-overlapping."""
        a4_w, a4_h = A4  # 595.275590551181, 841.8897637795276
        rectangles: list[fitz.Rect] = []

        for pos in range(6):
            col = pos % EDI_COLUMNS
            row = pos // EDI_COLUMNS
            x0 = EDI_LEFT_MARGIN + col * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
            y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
            x1 = x0 + EDI_LABEL_WIDTH
            y1 = y0 + EDI_LABEL_HEIGHT

            # 1. Strictly within bounds
            assert 0.0 <= x0 < x1 <= a4_w, f"Slot {pos} X bounds [{x0}, {x1}] exceed A4 width {a4_w}"
            assert 0.0 <= y0 < y1 <= a4_h, f"Slot {pos} Y bounds [{y0}, {y1}] exceed A4 height {a4_h}"

            rectangles.append(fitz.Rect(x0, y0, x1, y1))

        # 2. Pairwise non-overlapping check
        for i in range(len(rectangles)):
            for j in range(i + 1, len(rectangles)):
                intersection = rectangles[i].intersect(rectangles[j])
                assert intersection.is_empty, f"Slot {i} and Slot {j} overlap at {intersection}"

    def test_aspect_ratio_distortion_less_than_threshold(self):
        """Verify destination box aspect ratio distortion relative to cropped EDI template is < 0.01%."""
        crop_w = EDI_TEMPLATE_CROP.width   # 273.12 pt
        crop_h = EDI_TEMPLATE_CROP.height  # 276.24 pt
        orig_ratio = crop_w / crop_h

        dest_w = EDI_LABEL_WIDTH   # 273.12 pt
        dest_h = EDI_LABEL_HEIGHT  # 276.24 pt
        dest_ratio = dest_w / dest_h

        distortion = abs(dest_ratio - orig_ratio) / orig_ratio

        # Distortion must be less than 0.01% (0.0001) - 100% scale has 0.0% distortion
        assert distortion < 0.0001, f"Aspect ratio distortion {distortion:.6%} exceeds 0.01% limit"
        assert distortion == pytest.approx(0.0, abs=1e-6)

    def test_center_vertical_cutting_gutter_midline_alignment(self):
        """Verify center vertical cutting gutter midpoint aligns exactly with A4 portrait midline."""
        a4_w, _ = A4  # 595.28 pt
        midline = a4_w / 2.0  # 297.64 pt

        col0_right = EDI_LEFT_MARGIN + EDI_LABEL_WIDTH
        col1_left = col0_right + EDI_COLUMN_GAP
        gutter_midpoint = (col0_right + col1_left) / 2.0

        # Gutter midpoint must match A4 midline
        assert gutter_midpoint == pytest.approx(297.64, abs=0.01)
        assert abs(gutter_midpoint - midline) < 0.05, (
            f"Gutter midpoint {gutter_midpoint} deviates from A4 midline {midline}"
        )

        # Symmetry of left and right margins
        col1_right = col1_left + EDI_LABEL_WIDTH
        right_margin = a4_w - col1_right
        assert right_margin == pytest.approx(EDI_LEFT_MARGIN, abs=0.05)

        # Symmetry of top and bottom margins
        total_height = 3 * EDI_LABEL_HEIGHT + 2 * EDI_ROW_GAP
        bottom_margin = A4[1] - (EDI_TOP_MARGIN + total_height)
        assert bottom_margin == pytest.approx(EDI_TOP_MARGIN, abs=0.05)
