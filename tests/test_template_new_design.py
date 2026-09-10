from io import BytesIO
from pathlib import Path
from copy import deepcopy
import pytest
import fitz
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from core.slip_printer_engine import (
    create_record,
    create_overlay_pdf,
    load_layout_config,
    get_default_layout_config,
    generate_preview_image,
    build_qr_payload,
    EDI_TEMPLATE_CROP,
)


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


def test_qr_payload_always_full_regardless_of_slip_options(sample_record):
    """Ensure QR payload keeps 100% data intact (129 chars) even when slip hides fields."""
    payload = build_qr_payload(sample_record)
    assert len(payload) == 129
    assert "000000060000" in payload
    assert "000000020000" in payload
    assert "3V2ND00160 01" in payload
    assert "001/003" in payload


def test_default_layout_config_has_options():
    config = get_default_layout_config()
    assert "options" in config
    assert config["options"]["hide_total_qty_on_slip"] is True
    assert config["options"]["hide_package_qty_box"] is True
    # Box No in bottom table is for handwritten entry, not in text_positions
    ids = [item["id"] for item in config["text_positions"]]
    assert "box_bottom_1" not in ids
    assert "qty_right_1" in ids


def test_overlay_pdf_generation_with_options(sample_record):
    config = get_default_layout_config()
    # Default: total qty hidden, package qty hidden -> carton_qty 20 is drawn centered
    buf = create_overlay_pdf([sample_record], config)
    doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    page = doc[0]
    text = page.get_text()

    assert "3V2ND00160" in text
    assert "COVER RIGHT FUSER ASSY" in text
    assert "20" in text
    # Box string is not printed on the slip by default (PACKAGE QTY empty, Box No handwritten)
    assert "001/003" not in text

    # Toggle: show box in PACKAGE QTY box
    config_box = deepcopy(config)
    config_box["options"]["hide_package_qty_box"] = False
    buf2 = create_overlay_pdf([sample_record], config_box)
    doc2 = fitz.open(stream=buf2.getvalue(), filetype="pdf")
    text2 = doc2[0].get_text()
    assert "001/003" in text2


def test_toggle_show_total_qty(sample_record):
    config = get_default_layout_config()
    config["options"]["hide_total_qty_on_slip"] = False
    buf = create_overlay_pdf([sample_record], config)
    doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
    page = doc[0]
    text = page.get_text()
    assert "/" in text
    assert "60" in text
    assert "20" in text


def test_delivery_qty_no_collision_when_total_shown():
    """Verify that when total_qty is shown, carton_qty is placed to the left of '/', preventing collision."""
    record = create_record(
        row_number=1,
        item_code="3V2ND25400",
        item_name="ACTUATOR CAM",
        carton_qty="1600",
        total_qty="1600",
        po="1126090905",
        po_detail="00010",
        po_sub="+001",
        box="001/001",
        rev="01",
        lot="",
    )
    # Test both config where item x=670 and config where item x=705
    for initial_x in (670, 705):
        config = get_default_layout_config()
        config["options"]["hide_total_qty_on_slip"] = False
        for item in config["text_positions"]:
            if item.get("id") == "qty_right_1":
                item["x"] = initial_x
        buf = create_overlay_pdf([record], config)
        doc = fitz.open(stream=buf.getvalue(), filetype="pdf")
        page = doc[0]
        blocks = page.get_text("blocks")
        # Extract text elements with their bounding boxes
        words = page.get_text("words")  # (x0, y0, x1, y1, word, block_no, line_no, word_no)
        # Find carton qty (1600), slash (/), and total qty (1600) in Delivery QTY row (y ~ 90-110)
        carton_word = [w for w in words if w[4] == "1600" and 650 <= w[0] < 700 and 80 <= w[1] <= 120]
        slash_word = [w for w in words if w[4] == "/" and 80 <= w[1] <= 120]
        total_word = [w for w in words if w[4] == "1600" and w[0] > 720 and 80 <= w[1] <= 120]

        assert len(carton_word) == 1, f"Carton qty not found to left of slash with initial_x={initial_x}"
        assert len(slash_word) == 1, f"Slash not found with initial_x={initial_x}"
        assert len(total_word) == 1, f"Total qty not found to right of slash with initial_x={initial_x}"

        # Ensure strict separation (no collision): carton_qty x1 < slash x0 < total_qty x0
        assert carton_word[0][2] < slash_word[0][0], (
            f"Collision detected: carton_qty ends at {carton_word[0][2]} but slash starts at {slash_word[0][0]}"
        )
        assert slash_word[0][2] < total_word[0][0], (
            f"Collision detected: slash ends at {slash_word[0][2]} but total_qty starts at {total_word[0][0]}"
        )


def test_template_qc_boxes_expanded():
    """Verify template.pdf embedded EDI image has expanded QC boxes (>21mm width each)."""
    import numpy as np
    from PIL import Image

    template_path = Path(__file__).resolve().parent.parent / "template.pdf"
    doc = fitz.open(template_path)
    page = doc[0]
    # Extract xref 79 image
    img_info = doc.extract_image(79)
    img = Image.open(BytesIO(img_info["image"])).convert("L")
    arr = np.array(img)

    # In redesigned template:
    # Outer left of Line QC is at x=625 (55.1mm), mid divider is at x=867 (76.5mm), right is at x=1110 (97.9mm)
    # Total width = 485 px (42.8mm), each box is ~242 px (21.4mm)
    # Check vertical lines at x=625, 867, 1110 from y=20 to y=210
    col_left = (arr[25:215, 625] < 100).sum()
    col_mid = (arr[25:215, 867] < 100).sum()
    col_right = (arr[25:215, 1110] < 100).sum()

    assert col_left > 150, f"Left QC box border not found at x=625 (dark count: {col_left})"
    assert col_mid > 150, f"Middle QC box divider not found at x=867 (dark count: {col_mid})"
    assert col_right > 150, f"Right QC box border not found at x=1110 (dark count: {col_right})"

    # Verify that the stamping area (y=50 to 200) inside Line QC box is empty (white)
    stamping_area = arr[50:200, 630:860]
    dark_pixels = (stamping_area < 100).sum()
    assert dark_pixels == 0, f"Stamping area in Line QC box is not clean (dark pixels: {dark_pixels})"

