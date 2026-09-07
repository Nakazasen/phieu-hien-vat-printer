from io import BytesIO
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
    text = doc[0].get_text()
    assert "/" in text
    assert "60" in text
