from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from core.po_registry import FIXED_PO_DETAIL, FIXED_PO_SUB
if TYPE_CHECKING:
    from core.po_registry import PORegistry

import fitz
import qrcode
from PIL import Image
from PyPDF2 import PageObject, PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

ProgressCallback = Callable[[int, int, str], None]

# The user prints only the EDI label in the top-right quarter of template.pdf.
# Coordinates are PDF points in the template's landscape-A4 coordinate system.
EDI_TEMPLATE_CROP = fitz.Rect(558.6, 0.0, 841.92, 287.76)
EDI_COLUMNS = 2
EDI_ROWS = 2
EDI_PER_A4_PAGE = EDI_COLUMNS * EDI_ROWS
EDI_COLUMN_GAP = 11.34  # 4 mm, leaving a practical cut gutter.
EDI_ROW_GAP = 11.34
REV_PATTERN = re.compile(r"^(?:0[1-9]|[1-9][0-9])$")
EDI_TOP_MARGIN = 11.34
EDI_LABEL_WIDTH = EDI_TEMPLATE_CROP.width
EDI_LABEL_HEIGHT = EDI_TEMPLATE_CROP.height
EDI_LEFT_MARGIN = (A4[0] - (EDI_COLUMNS * EDI_LABEL_WIDTH) - EDI_COLUMN_GAP) / 2

START_ROW = 28
MAX_COL = 10
EMPTY_STREAK_STOP = 200
BATCH_SIZE = 500
DEFAULT_LOT_TEXT = " " * 10
SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
XML_NS = f"{{{SPREADSHEET_NS}}}"

FIELD_LABELS = {
    "item_code": "Mã hàng",
    "item_name": "Tên hàng",
    "qty": "Số lượng in",
    "carton_qty": "Số lượng thùng",
    "total_qty": "Tổng số lượng",
    "blank": "Để trống",
    "po": "PO",
    "po_detail": "PO chi tiết",
    "po_sub": "PO phụ",
    "box": "Số box",
    "rev": "Rev",
    "lot": "Ngày/Lot",
}

DEFAULT_LAYOUT_CONFIG: dict[str, Any] = {
    "font": {"name": "Helvetica", "size": 10},
    "qr_positions": {
        "qr_122": {"label": "QR 122 ký tự", "x": 200, "y": 150, "width": 100, "height": 100},
        "qr_full": {"label": "QR đầy đủ", "x": 710, "y": 270, "width": 100, "height": 100},
    },
    "text_positions": [
        {"id": "po_top", "label": "PO trên trái", "field": "po", "x": 400, "y": 180},
        {"id": "po_detail_top", "label": "PO chi tiết trên trái", "field": "po_detail", "x": 460, "y": 180},
        {"id": "po_sub_top", "label": "PO phụ trên trái", "field": "po_sub", "x": 500, "y": 180},
        {"id": "item_code_left_1", "label": "Mã hàng trái 1", "field": "item_code", "x": 20, "y": 200},
        {"id": "rev_left_1", "label": "Rev trái 1", "field": "rev", "x": 100, "y": 200},
        {"id": "item_name_left_1", "label": "Tên hàng trái 1", "field": "item_name", "x": 220, "y": 200},
        {"id": "qty_left_1", "label": "SL trái 1", "field": "qty", "x": 50, "y": 240},
        {"id": "po_left_1", "label": "PO trái 1", "field": "po", "x": 130, "y": 240},
        {"id": "po_detail_left_1", "label": "PO chi tiết trái 1", "field": "po_detail", "x": 200, "y": 240},
        {"id": "lot_left_1", "label": "Lot trái 1", "field": "lot", "x": 260, "y": 240},
        {"id": "item_code_right_1", "label": "Mã hàng phải 1", "field": "item_code", "x": 600, "y": 50},
        {"id": "rev_right_1", "label": "Rev phải 1", "field": "rev", "x": 670, "y": 50},
        {"id": "po_right_1", "label": "PO phải 1", "field": "po", "x": 620, "y": 70},
        {"id": "po_detail_right_1", "label": "PO chi tiết phải 1", "field": "po_detail", "x": 680, "y": 70},
        {"id": "po_sub_right_1", "label": "PO phụ phải 1", "field": "po_sub", "x": 710, "y": 70},
        {"id": "box_right_1", "label": "Box phải 1", "field": "box", "x": 780, "y": 70},
        {"id": "item_name_right_1", "label": "Tên hàng phải 1", "field": "item_name", "x": 650, "y": 85},
        {"id": "qty_right_1", "label": "SL phải 1", "field": "carton_qty", "x": 670, "y": 100},
        {"id": "qty_right_2", "label": "SL phải 2", "field": "total_qty", "x": 750, "y": 100},
        {"id": "lot_right_1", "label": "Lot phải 1", "field": "lot", "x": 610, "y": 150},
        {"id": "po_bottom", "label": "PO dưới", "field": "po", "x": 380, "y": 380},
        {"id": "po_detail_bottom", "label": "PO chi tiết dưới", "field": "po_detail", "x": 440, "y": 380},
        {"id": "po_sub_bottom", "label": "PO phụ dưới", "field": "po_sub", "x": 480, "y": 380},
        {"id": "item_code_bottom", "label": "Mã hàng dưới", "field": "item_code", "x": 30, "y": 410},
        {"id": "rev_bottom", "label": "Rev dưới", "field": "rev", "x": 100, "y": 410},
        {"id": "item_name_bottom", "label": "Tên hàng dưới", "field": "item_name", "x": 190, "y": 410},
        {"id": "qty_bottom", "label": "SL dưới", "field": "qty", "x": 400, "y": 410},
    ],
}


@dataclass(slots=True)
class SlipRecord:
    row_number: int
    item_code: str
    item_name: str
    carton_qty: str
    total_qty: str
    po: str
    po_detail: str
    po_sub: str
    box: str
    rev: str
    lot: str
    qr_payload: str = ""

    def with_payload(self) -> SlipRecord:
        return replace(self, qr_payload=build_qr_payload(self))

    @property
    def qty_display(self) -> str:
        total = self.total_qty.strip()
        carton = self.carton_qty.strip()
        if total and total != carton:
            return f"{carton}/{total}"
        return carton

    @property
    def display_values(self) -> tuple[str, ...]:
        return (
            str(self.row_number),
            self.item_code,
            self.item_name,
            self.carton_qty,
            self.total_qty,
            self.po,
            self.po_detail,
            self.po_sub,
            self.box,
            self.rev,
            self.lot,
        )

    def as_field_map(self) -> dict[str, str]:
        return {
            "item_code": self.item_code,
            "item_name": self.item_name,
            "qty": self.qty_display,
            "carton_qty": self.carton_qty,
            "total_qty": self.total_qty,
            "po": self.po,
            "po_detail": self.po_detail,
            "po_sub": self.po_sub,
            "box": self.box,
            "rev": self.rev,
            "lot": self.lot,
        }


def normalize_lot(value: object | None) -> str:
    if value is None or str(value) == "":
        return DEFAULT_LOT_TEXT
    return str(value)


def normalize_box(box_value: object) -> str:
    """Normalize a box value into 7-character XXX/YYY standard format.

    Examples:
    - "1" or 1 -> "001/001"
    - "3" or 3 -> "001/003"
    - "001/003" -> "001/003"
    - "2/3" -> "002/003"
    """
    text = _string_value(box_value).strip()
    if not text:
        return ""
    if "/" in text:
        parts = text.split("/", 1)
        try:
            curr = int(parts[0].strip())
            total = int(parts[1].strip())
            return f"{curr:03d}/{total:03d}"
        except ValueError:
            return text
    try:
        n = int(text)
        if n <= 0:
            return text
        if n == 1:
            return "001/001"
        return f"001/{n:03d}"
    except ValueError:
        return text


def expand_box_sequence(box_value: object) -> list[str]:
    """Expand a box count integer or formatted string into a list of box strings.

    Examples:
    - 3 or "3" or "003" -> ["001/003", "002/003", "003/003"]
    - 1 or "1" -> ["001/001"]
    - "001/003" -> ["001/003"]
    - "002/003" -> ["002/003"]
    - "2/5" -> ["002/005"]
    """
    text = _string_value(box_value).strip()
    if not text:
        raise ValueError("Số box không được để trống.")

    if "/" in text:
        parts = text.split("/", 1)
        try:
            curr = int(parts[0].strip())
            total = int(parts[1].strip())
            if curr <= 0 or total <= 0:
                raise ValueError("Số box phải lớn hơn 0.")
            if curr > total:
                raise ValueError(f"Số thứ tự box ({curr}) không được lớn hơn tổng số box ({total}).")
            return [f"{curr:03d}/{total:03d}"]
        except ValueError as exc:
            if "không được lớn hơn" in str(exc) or "phải lớn hơn 0" in str(exc):
                raise
            raise ValueError("Số box theo dạng 001/003 phải chứa các số hợp lệ.") from exc

    try:
        n = int(text)
    except ValueError as exc:
        raise ValueError("Số box phải là số nguyên dương (ví dụ: 3) hoặc theo dạng 001/003.") from exc

    if n <= 0:
        raise ValueError("Số box phải lớn hơn 0.")

    return [f"{i:03d}/{n:03d}" for i in range(1, n + 1)]


def calculate_total_qty(carton_qty: object, box: object) -> str:
    """Calculate total quantity from carton quantity and the final Box segment.

    A Box value of ``001/003`` represents three boxes, so the multiplier is
    the segment after the last slash. A plain numeric Box value is also valid.
    """
    carton_text = _string_value(carton_qty).strip()
    box_text = _string_value(box).strip()
    multiplier_text = box_text.rsplit("/", 1)[-1].strip()

    if not carton_text:
        raise ValueError("Số lượng thùng không được để trống.")
    if not box_text or not multiplier_text:
        raise ValueError("Số box phải là số hoặc theo dạng 001/003.")

    try:
        carton_value = Decimal(carton_text)
        box_count = Decimal(multiplier_text)
    except InvalidOperation as exc:
        raise ValueError("Số lượng thùng và số box phải là giá trị số hợp lệ.") from exc

    if carton_value <= 0 or box_count <= 0:
        raise ValueError("Số lượng thùng và số box phải lớn hơn 0.")

    total = carton_value * box_count
    if total == total.to_integral_value():
        return str(int(total))
    return format(total.normalize(), "f").rstrip("0").rstrip(".")


def create_record(
    *,
    row_number: int,
    item_code: object,
    item_name: object,
    carton_qty: object,
    total_qty: object | None,
    po: object,
    po_detail: object,
    po_sub: object,
    box: object,
    rev: object,
    lot: object | None = None,
) -> SlipRecord:
    # Normalize once at the record boundary so pasted/manual, Excel and QR data
    # all produce the same printable EDI values.
    item_code_text = _string_value(item_code).strip().upper()
    item_name_text = _string_value(item_name).strip().upper()
    carton_qty_text = _string_value(carton_qty).strip()
    normalized_box = normalize_box(_string_value(box).strip())
    total_qty_text = calculate_total_qty(carton_qty_text, normalized_box)
    record = SlipRecord(
        row_number=row_number,
        item_code=item_code_text,
        item_name=item_name_text,
        carton_qty=carton_qty_text,
        total_qty=total_qty_text,
        po=_string_value(po).strip(),
        po_detail=_string_value(po_detail).strip(),
        po_sub=_string_value(po_sub).strip(),
        box=normalized_box,
        rev=_string_value(rev).strip(),
        lot=normalize_lot(_string_value(lot).strip()),
    )
    return record.with_payload()


def validate_revision(value: object) -> str:
    """Return a valid two-digit revision, or raise a user-facing error.

    Revisions are printed as part of the EDI label and must retain their
    leading zero.  Accept 01 through 99 only; values such as 1, 001, 00 or
    text are rejected consistently for manual entry, Excel imports and PDF
    generation.
    """
    revision = _string_value(value).strip()
    if not REV_PATTERN.fullmatch(revision):
        raise ValueError("Rev phải có 2 chữ số từ 01 đến 99 (ví dụ: 01, 02).")
    return revision


def get_default_layout_config() -> dict[str, Any]:
    return deepcopy(DEFAULT_LAYOUT_CONFIG)


def ensure_layout_config_file(config_path: str | Path) -> Path:
    path = Path(config_path)
    if not path.exists():
        save_layout_config(get_default_layout_config(), path)
    return path


def load_layout_config(config_path: str | Path) -> dict[str, Any]:
    path = ensure_layout_config_file(config_path)
    return json.loads(path.read_text(encoding="utf-8"))


def save_layout_config(config: dict[str, Any], config_path: str | Path) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def list_layout_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, value in config.get("qr_positions", {}).items():
        items.append(
            {
                "kind": "qr",
                "id": key,
                "label": value.get("label", key),
                "field": key,
                "x": value["x"],
                "y": value["y"],
                "width": value["width"],
                "height": value["height"],
            }
        )
    for value in config.get("text_positions", []):
        items.append(
            {
                "kind": "text",
                "id": value["id"],
                "label": value.get("label", value["id"]),
                "field": value["field"],
                "x": value["x"],
                "y": value["y"],
                "width": None,
                "height": None,
            }
        )
    return items


def update_layout_item(
    config: dict[str, Any],
    item_id: str,
    *,
    x: float,
    y: float,
    width: float | None = None,
    height: float | None = None,
) -> dict[str, Any]:
    updated = deepcopy(config)
    if item_id in updated.get("qr_positions", {}):
        updated["qr_positions"][item_id]["x"] = x
        updated["qr_positions"][item_id]["y"] = y
        if width is not None:
            updated["qr_positions"][item_id]["width"] = width
        if height is not None:
            updated["qr_positions"][item_id]["height"] = height
        return updated

    for item in updated.get("text_positions", []):
        if item["id"] == item_id:
            item["x"] = x
            item["y"] = y
            return updated

    raise KeyError(f"Không tìm thấy phần tử layout: {item_id}")


def format_string_qty(value: object) -> str:
    """Format quantity as the 12-character field used by Kyocera EDI QR.

    The reference printer writes an 8-digit integer followed by four literal
    zeroes: 1 -> ``000000010000`` and 180 -> ``000001800000``.
    """
    formatted_value = f"{int(float(value)):08d}"
    return f"{formatted_value[-8:]}0000"


def format_string_part(item_code: object, rev_value: object) -> str:
    combined_string = f"{_string_value(item_code).strip()} {_string_value(rev_value).strip()}"
    return f"{combined_string:<25}"[:25]


def format_string_lot(lot_value: object) -> str:
    combined_string = _string_value(lot_value)
    return f"{combined_string:<26}"[:26]


def format_string_po(po: object, po_detail: object, po_sub: object) -> str:
    po_str = _string_value(po).strip()
    detail_str = _string_value(po_detail).strip()
    sub_str = _string_value(po_sub).strip()
    return f"{po_str:<10}"[:10] + f"{detail_str:<5}"[:5] + f"{sub_str:<4}"[:4]


def format_string_box(box_value: object) -> str:
    norm = normalize_box(box_value)
    return f"{norm:>7}"[:7]


def build_qr_payload(record: SlipRecord) -> str:
    """Build standardized 129-character QR payload for Kyocera EDI label.

    Structure (129 chars total):
    - 19 chars: PO (10) + PO detail (5) + PO sub (4)
    - 4 chars: Space (4)
    - 12 chars: Total Qty (8 digits + 0000)
    - 25 chars: Item code & Rev (padded to 25)
    - 12 chars: Total Qty repeated (8 digits + 0000)
    - 26 chars: Lot (padded to 26)
    - 24 chars: Space (24)
    - 7 chars: Box (001/003)
    Prefix: 122 chars. Total: 129 chars.
    """
    po_field = format_string_po(record.po, record.po_detail, record.po_sub)
    space_4 = " " * 4
    formatted_total_qty = format_string_qty(record.total_qty)
    formatted_part = format_string_part(record.item_code, record.rev)
    formatted_lot = format_string_lot(record.lot)
    space_24 = " " * 24
    formatted_box = format_string_box(record.box)

    return (
        f"{po_field}{space_4}{formatted_total_qty}{formatted_part}"
        f"{formatted_total_qty}{formatted_lot}{space_24}{formatted_box}"
    )


@dataclass(slots=True)
class QRParsedData:
    po: str
    po_detail: str
    po_sub: str
    total_qty: str
    item_code: str
    rev: str
    lot: str
    box: str
    carton_qty: str
    raw_payload: str


def parse_qr_payload(payload: str) -> QRParsedData:
    """Parse and extract structured fields from a 122+ or 129-char QR code payload."""
    clean_payload = payload.strip("\r\n")
    if len(clean_payload) < 122:
        raise ValueError(
            f"Mã QR không đúng định dạng (độ dài {len(clean_payload)} < 122 ký tự tiêu chuẩn)."
        )

    po = clean_payload[0:10].strip()
    po_detail = clean_payload[10:15].strip() or FIXED_PO_DETAIL
    po_sub = clean_payload[15:19].strip() or FIXED_PO_SUB

    # Total quantity at 23..35 (12 chars: 8 digits + 0000)
    qty_segment = clean_payload[23:35].strip()
    try:
        if len(qty_segment) >= 8:
            val = int(qty_segment[:8])
        else:
            val = int(qty_segment)
        total_qty = str(val) if val > 0 else "1"
    except ValueError:
        total_qty = "1"

    # Item code and Rev at 35..60 (25 chars)
    part_rev_str = clean_payload[35:60].strip()
    if " " in part_rev_str:
        item_code, rev = part_rev_str.rsplit(" ", 1)
        item_code = item_code.strip()
        rev = rev.strip()
    else:
        item_code = part_rev_str
        rev = "01"

    if not (len(rev) == 2 and rev.isdigit() and int(rev) > 0):
        rev = "01"

    # Lot at 72..98 (26 chars)
    lot_segment = clean_payload[72:98].strip()
    lot = lot_segment if lot_segment else ""

    # Box at 122.. (remaining chars, e.g. 7 chars)
    box_segment = clean_payload[122:].strip()
    if not box_segment:
        box = "001/001"
    else:
        norm = normalize_box(box_segment)
        try:
            expand_box_sequence(norm)
            box = norm
        except Exception:
            box = "001/001"

    # Calculate carton_qty
    try:
        if "/" in box:
            multiplier = int(box.rsplit("/", 1)[-1])
            total_val = Decimal(total_qty)
            carton_val = total_val / Decimal(multiplier)
            if carton_val == carton_val.to_integral_value():
                carton_qty = str(int(carton_val))
            else:
                carton_qty = format(carton_val.normalize(), "f").rstrip("0").rstrip(".")
        else:
            carton_qty = total_qty
    except Exception:
        carton_qty = total_qty

    return QRParsedData(
        po=po,
        po_detail=po_detail,
        po_sub=po_sub,
        total_qty=total_qty,
        item_code=item_code,
        rev=rev,
        lot=lot,
        box=box,
        carton_qty=carton_qty,
        raw_payload=clean_payload,
    )


def _string_value(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _load_shared_strings(workbook_zip: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook_zip.namelist():
        return []

    shared_strings: list[str] = []
    with workbook_zip.open("xl/sharedStrings.xml") as handle:
        for _event, elem in ET.iterparse(handle, events=("end",)):
            if elem.tag == f"{XML_NS}si":
                parts = [node.text or "" for node in elem.iter(f"{XML_NS}t")]
                shared_strings.append("".join(parts))
                elem.clear()
    return shared_strings


def _resolve_active_sheet_path(workbook_zip: zipfile.ZipFile) -> str:
    workbook_root = ET.fromstring(workbook_zip.read("xl/workbook.xml"))
    namespaces = {"main": SPREADSHEET_NS, "rel": REL_NS}
    active_tab = 0
    workbook_view = workbook_root.find("main:bookViews/main:workbookView", namespaces)
    if workbook_view is not None:
        active_tab = int(workbook_view.attrib.get("activeTab", "0"))

    sheets = workbook_root.find("main:sheets", namespaces)
    if sheets is None or not list(sheets):
        raise ValueError("File Excel không chứa bất kỳ trang tính nào.")

    active_sheet = list(sheets)[min(active_tab, len(list(sheets)) - 1)]
    relationship_id = active_sheet.attrib.get(f"{{{REL_NS}}}id")
    if not relationship_id:
        raise ValueError("Không thể xác định liên kết trang tính đang hoạt động.")

    rel_root = ET.fromstring(workbook_zip.read("xl/_rels/workbook.xml.rels"))
    rel_namespaces = {"rel": PKG_REL_NS}
    for rel in rel_root.findall("rel:Relationship", rel_namespaces):
        if rel.attrib.get("Id") == relationship_id:
            target = rel.attrib["Target"].replace("\\", "/")
            if target.startswith("/"):
                target = target.lstrip("/")
            if target.startswith("xl/"):
                return target
            return f"xl/{target}"

    raise ValueError("Không thể xác định đường dẫn trang tính đang hoạt động.")


def _column_index_from_ref(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char.upper()) - 64)
    return index


def _extract_cell_value(cell: ET.Element, shared_strings: list[str]) -> object | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{XML_NS}t"))

    value_node = cell.find(f"{XML_NS}v")
    if value_node is None or value_node.text is None:
        return None

    value = value_node.text
    if cell_type == "s":
        return shared_strings[int(value)]
    if cell_type == "b":
        return value == "1"
    if cell_type == "str":
        return value

    try:
        numeric_value = float(value)
    except ValueError:
        return value
    return int(numeric_value) if numeric_value.is_integer() else numeric_value


def _iter_sheet_rows(excel_file: str | Path):
    with zipfile.ZipFile(excel_file) as workbook_zip:
        shared_strings = _load_shared_strings(workbook_zip)
        sheet_path = _resolve_active_sheet_path(workbook_zip)

        with workbook_zip.open(sheet_path) as handle:
            for _event, elem in ET.iterparse(handle, events=("end",)):
                if elem.tag != f"{XML_NS}row":
                    continue
                row_number = int(elem.attrib.get("r", "0"))
                if row_number < START_ROW:
                    elem.clear()
                    continue

                values: list[object | None] = [None] * MAX_COL
                for cell in elem.findall(f"{XML_NS}c"):
                    ref = cell.attrib.get("r", "")
                    column_index = _column_index_from_ref(ref)
                    if 1 <= column_index <= MAX_COL:
                        values[column_index - 1] = _extract_cell_value(cell, shared_strings)
                yield row_number, tuple(values)
                elem.clear()


def generate_qr_code(data: str) -> Image.Image:
    qr = qrcode.make(data)
    return qr.get_image()

def read_records(excel_file: str | Path) -> list[SlipRecord]:
    records: list[SlipRecord] = []
    empty_streak = 0
    found_data = False

    for row_number, row in _iter_sheet_rows(excel_file):
        leading_cells = row[:9]
        if all(value is None for value in leading_cells):
            empty_streak += 1
            if found_data and empty_streak >= EMPTY_STREAK_STOP:
                break
        else:
            empty_streak = 0

        if row[0] is None or row[1] is None:
            continue

        found_data = True
        total_qty = row[2] if row[2] not in (None, "") else row[3]
        records.append(
            create_record(
                row_number=row_number,
                item_code=row[0],
                item_name=row[1],
                carton_qty=row[3],
                total_qty=total_qty,
                po=row[4],
                po_detail=row[5],
                po_sub=row[6],
                box=row[7],
                rev=row[8],
                lot=row[9],
            )
        )
    return records


def validate_records(
    records: Iterable[SlipRecord],
    *,
    registry: PORegistry | None = None,
) -> list[SlipRecord]:
    validated: list[SlipRecord] = []
    for index, record in enumerate(records, start=1):
        if not record.item_code.strip():
            raise ValueError(f"Dòng {index}: thiếu mã hàng.")
        if not record.item_name.strip():
            raise ValueError(f"Dòng {index}: thiếu tên hàng.")
        if not record.carton_qty.strip():
            raise ValueError(f"Dòng {index}: thiếu số lượng thùng.")
        if not record.box.strip():
            raise ValueError(f"Dòng {index}: thiếu số box.")
        try:
            revision = validate_revision(record.rev)
        except ValueError as exc:
            raise ValueError(f"Dòng {index}: {exc}") from exc
        norm_box = normalize_box(record.box)
        calculated_total_qty = calculate_total_qty(record.carton_qty, norm_box)
        norm_detail = record.po_detail.strip() or FIXED_PO_DETAIL
        norm_sub = record.po_sub.strip() or FIXED_PO_SUB
        validated.append(
            replace(
                record,
                po_detail=norm_detail,
                po_sub=norm_sub,
                box=norm_box,
                rev=revision,
                total_qty=calculated_total_qty,
            ).with_payload()
        )

    if registry is not None:
        combos = [
            (r.po, r.po_detail, r.po_sub, r.box)
            for r in validated
            if r.po.strip()
        ]
        if combos:
            registry.register_combos(combos)

    return validated


def auto_fill_po(
    records: list[SlipRecord],
    registry: PORegistry,
) -> list[SlipRecord]:
    """Fill empty PO fields with auto-generated PO numbers.

    Records that already have a non-empty PO are returned unchanged.
    Records with an empty PO get an auto-generated PO, fixed PO detail
    (``00010``), and fixed PO sub (``+001``).
    Multi-box batches with empty PO sharing the same series use the same PO.

    Returns a new list with updated records.
    """
    result: list[SlipRecord] = []
    i = 0
    while i < len(records):
        record = records[i]
        if record.po.strip():
            result.append(record)
            i += 1
            continue

        new_po = registry.generate_po()
        box_str = record.box.strip()
        is_box_series = False
        total_boxes = 1
        if "/" in box_str:
            parts = box_str.split("/", 1)
            try:
                curr_box = int(parts[0])
                total_boxes = int(parts[1])
                if curr_box == 1 and total_boxes > 1:
                    is_box_series = True
            except ValueError:
                pass

        updated = replace(
            record,
            po=new_po,
            po_detail=record.po_detail.strip() or FIXED_PO_DETAIL,
            po_sub=record.po_sub.strip() or FIXED_PO_SUB,
        )
        result.append(updated.with_payload())
        i += 1

        if is_box_series:
            expected_next = 2
            while i < len(records) and expected_next <= total_boxes:
                next_record = records[i]
                if next_record.po.strip():
                    break
                next_box = next_record.box.strip()
                if "/" not in next_box:
                    break
                next_parts = next_box.split("/", 1)
                try:
                    next_curr = int(next_parts[0])
                    next_tot = int(next_parts[1])
                    if (
                        next_curr == expected_next
                        and next_tot == total_boxes
                        and next_record.item_code.strip() == record.item_code.strip()
                    ):
                        next_updated = replace(
                            next_record,
                            po=new_po,
                            po_detail=next_record.po_detail.strip() or FIXED_PO_DETAIL,
                            po_sub=next_record.po_sub.strip() or FIXED_PO_SUB,
                        )
                        result.append(next_updated.with_payload())
                        expected_next += 1
                        i += 1
                    else:
                        break
                except ValueError:
                    break

    return result


def create_overlay_pdf(records: list[SlipRecord], layout_config: dict[str, Any]) -> BytesIO:
    buffer = BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=landscape(A4))
    for record in records:
        _draw_record_page(pdf_canvas, record, layout_config)
    pdf_canvas.save()
    buffer.seek(0)
    return buffer


def _draw_record_page(pdf_canvas: canvas.Canvas, record: SlipRecord, layout_config: dict[str, Any]) -> None:
    _, height = landscape(A4)
    qr_image_full = generate_qr_code(record.qr_payload)
    qr_image_122 = generate_qr_code(record.qr_payload[:122])

    qr_positions = layout_config["qr_positions"]
    qr_122 = qr_positions["qr_122"]
    qr_full = qr_positions["qr_full"]
    pdf_canvas.drawInlineImage(
        qr_image_122,
        qr_122["x"],
        height - qr_122["y"],
        width=qr_122["width"],
        height=qr_122["height"],
    )
    pdf_canvas.drawInlineImage(
        qr_image_full,
        qr_full["x"],
        height - qr_full["y"],
        width=qr_full["width"],
        height=qr_full["height"],
    )

    font = layout_config["font"]
    pdf_canvas.setFont(font["name"], font["size"])
    values = record.as_field_map()
    for item in layout_config["text_positions"]:
        text = values.get(item["field"], "")
        pdf_canvas.drawString(item["x"], height - item["y"], text)
    pdf_canvas.showPage()


def _merge_overlay_with_template_pages(overlay_pdf_stream: BytesIO, template_pdf_path: str | Path) -> bytes:
    overlay_pdf = PdfReader(overlay_pdf_stream)
    template_pdf = PdfReader(str(template_pdf_path))
    output_pdf = PdfWriter()
    for overlay_page in overlay_pdf.pages:
        template_page = template_pdf.pages[0]
        template_page_copy = PageObject.create_blank_page(
            width=template_page.mediabox.width,
            height=template_page.mediabox.height,
        )
        template_page_copy.merge_page(template_page)
        template_page_copy.merge_page(overlay_page)
        output_pdf.add_page(template_page_copy)

    output_buffer = BytesIO()
    output_pdf.write(output_buffer)
    return output_buffer.getvalue()


def _compose_edi_labels_on_a4(merged_label_pdf_bytes: bytes) -> bytes:
    """Crop one EDI label per record and place up to four labels on portrait A4."""
    source = fitz.open(stream=merged_label_pdf_bytes, filetype="pdf")
    output = fitz.open()
    try:
        for first_label_index in range(0, source.page_count, EDI_PER_A4_PAGE):
            output_page = output.new_page(width=A4[0], height=A4[1])
            labels_on_page = min(EDI_PER_A4_PAGE, source.page_count - first_label_index)
            for position in range(labels_on_page):
                column = position % EDI_COLUMNS
                row = position // EDI_COLUMNS
                x0 = EDI_LEFT_MARGIN + column * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
                y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
                destination = fitz.Rect(x0, y0, x0 + EDI_LABEL_WIDTH, y0 + EDI_LABEL_HEIGHT)
                output_page.show_pdf_page(
                    destination,
                    source,
                    first_label_index + position,
                    clip=EDI_TEMPLATE_CROP,
                    keep_proportion=True,
                    overlay=True,
                )
        return output.tobytes(garbage=4, deflate=True)
    finally:
        output.close()
        source.close()


def merge_overlay_with_template_bytes(overlay_pdf_stream: BytesIO, template_pdf_path: str | Path) -> bytes:
    merged_labels = _merge_overlay_with_template_pages(overlay_pdf_stream, template_pdf_path)
    return _compose_edi_labels_on_a4(merged_labels)

# Đã thay thế merge_overlay_with_template bằng logic chia lô (batching) trong generate_pdf_from_records.


def generate_preview_image(
    record: SlipRecord,
    template_pdf_path: str | Path,
    layout_config: dict[str, Any],
    *,
    zoom: float = 1.35,
    clip: fitz.Rect | None = EDI_TEMPLATE_CROP,
) -> Image.Image:
    """Render a preview of the printed EDI label for one record.

    By default only the actual EDI label region (EDI_TEMPLATE_CROP — the exact
    rectangle that gets cropped and tiled 4-per-A4 by the print pipeline) is
    rendered, so the preview shows readable label content instead of a tiny
    label floating on a full A4 page. Pass ``clip=None`` to render the full page.
    """
    overlay_buffer = create_overlay_pdf([record.with_payload()], layout_config)
    # Render the original landscape template page.  The crop coordinates above
    # are defined in that page's coordinate system; applying them after the
    # label has been tiled onto portrait A4 leaves only a thin, blank strip.
    merged_pdf_bytes = _merge_overlay_with_template_pages(overlay_buffer, template_pdf_path)
    return render_pdf_first_page(merged_pdf_bytes, zoom=zoom, clip=clip)


def render_pdf_first_page(pdf_bytes: bytes, *, zoom: float = 1.35, clip: fitz.Rect | None = None) -> Image.Image:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = document.load_page(0)
        matrix = fitz.Matrix(zoom, zoom)
        if clip is not None:
            pixmap = page.get_pixmap(matrix=matrix, clip=fitz.Rect(clip), alpha=False)
        else:
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
        return Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    finally:
        document.close()


def generate_pdf_from_records(
    records: list[SlipRecord],
    template_pdf_path: str | Path,
    output_pdf_path: str | Path,
    *,
    layout_config: dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
    registry: PORegistry | None = None,
) -> list[SlipRecord]:
    normalized_records = validate_records(records, registry=registry)
    current_layout = layout_config or get_default_layout_config()
    total_records = len(normalized_records)

    if progress_callback:
        progress_callback(0, total_records, f"Đã nạp {total_records} dòng để in")

    output_path = Path(output_pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Gom tất cả label PDF lại (chưa dàn trang A4)
    all_labels_pdf = fitz.open()

    # Bước 1 & 2: Sinh Overlay và Merge theo lô để tiết kiệm RAM (đặc biệt là tránh PyPDF2 ngốn RAM)
    for i in range(0, total_records, BATCH_SIZE):
        batch = normalized_records[i:i + BATCH_SIZE]
        overlay_buffer = create_overlay_pdf(batch, current_layout)
        merged_labels_bytes = _merge_overlay_with_template_pages(overlay_buffer, template_pdf_path)
        
        batch_doc = fitz.open(stream=merged_labels_bytes, filetype="pdf")
        all_labels_pdf.insert_pdf(batch_doc)
        batch_doc.close()
        
        if progress_callback:
            progress_callback(min(i + len(batch), total_records), total_records, f"Đã ghép {min(i + len(batch), total_records)}/{total_records} tem")

    # Bước 3: Dàn trang A4 (4 tem / trang)
    output_pdf = fitz.open()
    try:
        if progress_callback:
            progress_callback(total_records, total_records, "Đang dàn trang A4...")
            
        for first_label_index in range(0, all_labels_pdf.page_count, EDI_PER_A4_PAGE):
            output_page = output_pdf.new_page(width=A4[0], height=A4[1])
            labels_on_page = min(EDI_PER_A4_PAGE, all_labels_pdf.page_count - first_label_index)
            for position in range(labels_on_page):
                column = position % EDI_COLUMNS
                row = position // EDI_COLUMNS
                x0 = EDI_LEFT_MARGIN + column * (EDI_LABEL_WIDTH + EDI_COLUMN_GAP)
                y0 = EDI_TOP_MARGIN + row * (EDI_LABEL_HEIGHT + EDI_ROW_GAP)
                destination = fitz.Rect(x0, y0, x0 + EDI_LABEL_WIDTH, y0 + EDI_LABEL_HEIGHT)
                output_page.show_pdf_page(
                    destination,
                    all_labels_pdf,
                    first_label_index + position,
                    clip=EDI_TEMPLATE_CROP,
                    keep_proportion=True,
                    overlay=True,
                )
        
        if progress_callback:
            progress_callback(total_records, total_records, f"Đang lưu file PDF ({output_pdf.page_count} trang A4)...")
            
        output_pdf.save(str(output_path), garbage=4, deflate=True)
    finally:
        output_pdf.close()
        all_labels_pdf.close()

    return normalized_records


def generate_pdf_from_excel(
    excel_file: str | Path,
    template_pdf_path: str | Path,
    output_pdf_path: str | Path,
    *,
    layout_config: dict[str, Any] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[SlipRecord]:
    records = read_records(excel_file)
    if not records:
        raise ValueError(f"Không tìm thấy dòng dữ liệu hợp lệ. Kỳ vọng dữ liệu từ dòng {START_ROW}, cột A:J.")
    return generate_pdf_from_records(
        records,
        template_pdf_path,
        output_pdf_path,
        layout_config=layout_config,
        progress_callback=progress_callback,
    )
