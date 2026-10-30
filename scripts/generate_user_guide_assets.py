"""Generate real user visual guide assets (annotated real UI screenshots, HTML manual, and PDF manual).

Launches the actual SlipPrinterApp in an isolated runtime environment with real production
sample data (302YJ03340, 302YJ12010, 302NR25651, real QR payloads, Split CAV, duplicate rows,
A4/Letter slip renders), captures real screenshots of each workflow screen, overlays pixel-accurate
numbered callouts (1, 2, 3, 4...) using live widget coordinates, and compiles:
- assets/user_guide/ch01_excel_import.png
- assets/user_guide/ch02_manual_cav.png
- assets/user_guide/ch03_qr_scan.png
- assets/user_guide/ch04_pdf_export.png
- assets/user_guide/ch05_layout_history.png
- assets/user_guide/ch06_troubleshooting.png
- assets/user_guide/huong_dan_su_dung.html
- assets/user_guide/Huong_Dan_Su_Dung_InPhieuHienVat.pdf
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import io
import math
import os
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

import fitz
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageGrab

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

ASSETS_DIR = REPO_ROOT / "assets" / "user_guide"


def _enable_dpi_awareness() -> None:
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def _load_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\malgunbd.ttf",
        ]
        if bold
        else [
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\malgun.ttf",
        ]
    )
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _capture_window_image(root) -> Image.Image:
    """Capture the exact rendered window pixels of `root` on Windows."""
    if hasattr(root, "_apply_splitter_width"):
        root._apply_splitter_width()
    root.update_idletasks()
    root.update()
    time.sleep(0.18)
    if hasattr(root, "_apply_splitter_width"):
        root._apply_splitter_width()
    root.lift()
    root.attributes("-topmost", True)
    root.update_idletasks()
    root.update()
    time.sleep(0.15)

    hwnd = int(root.winfo_id())
    img = ImageGrab.grab(window=hwnd)
    root.attributes("-topmost", False)
    return img.convert("RGB")


def _widget_rel_box(root, widget, pad: int = 4) -> tuple[int, int, int, int]:
    """Return (x1, y1, x2, y2) of `widget` relative to `root`'s client area."""
    root.update_idletasks()
    rx = root.winfo_rootx()
    ry = root.winfo_rooty()
    rw = root.winfo_width()
    rh = root.winfo_height()

    target = getattr(widget, "_canvas", widget)
    wx = target.winfo_rootx() - rx
    wy = target.winfo_rooty() - ry
    ww = target.winfo_width()
    wh = target.winfo_height()

    x1 = max(2, wx - pad)
    y1 = max(2, wy - pad)
    x2 = min(rw - 2, wx + ww + pad)
    y2 = min(rh - 2, wy + wh + pad)
    return (int(x1), int(y1), int(x2), int(y2))


def _draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    width: int = 4,
) -> None:
    """Draw a thick line with an arrowhead pointing at `end`."""
    draw.line([start, end], fill=color, width=width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    angle = math.atan2(dy, dx)
    head_len = 14
    head_angle = math.pi / 6
    p1 = (
        int(end[0] - head_len * math.cos(angle - head_angle)),
        int(end[1] - head_len * math.sin(angle - head_angle)),
    )
    p2 = (
        int(end[0] - head_len * math.cos(angle + head_angle)),
        int(end[1] - head_len * math.sin(angle + head_angle)),
    )
    draw.polygon([end, p1, p2], fill=color)


def _annotate_image(
    base_img: Image.Image,
    banner_title: str,
    banner_subtitle: str,
    callouts: list[dict[str, Any]],
) -> Image.Image:
    """Render a top context banner and numbered callout boxes + badges + labels onto `base_img`."""
    banner_h = 68
    w, h = base_img.size
    canvas = Image.new("RGB", (w, h + banner_h), (15, 23, 42))
    canvas.paste(base_img, (0, banner_h))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # Top header banner
    odraw.rectangle([0, 0, w, banner_h], fill=(15, 23, 42, 255))
    odraw.line([(0, banner_h - 2), (w, banner_h - 2)], fill=(16, 185, 129, 255), width=3)

    title_font = _load_font(20, bold=True)
    sub_font = _load_font(13, bold=False)
    badge_font = _load_font(16, bold=True)
    label_font = _load_font(13, bold=True)

    odraw.text((20, 10), banner_title, font=title_font, fill=(255, 255, 255, 255))
    odraw.text((20, 39), banner_subtitle, font=sub_font, fill=(148, 163, 184, 255))

    placed_rects: list[tuple[int, int, int, int]] = []

    def _overlaps(r1: tuple[int, int, int, int], r2: tuple[int, int, int, int], pad: int = 6) -> bool:
        return not (
            r1[2] + pad < r2[0]
            or r1[0] - pad > r2[2]
            or r1[3] + pad < r2[1]
            or r1[1] - pad > r2[3]
        )

    # Pass 1: Draw all highlight boxes and numbered badges first
    badge_infos: list[tuple[int, int]] = []
    for item in callouts:
        num = str(item["num"])
        bx1, by1, bx2, by2 = item["box"]
        y1 = by1 + banner_h
        y2 = by2 + banner_h
        x1, x2 = bx1, bx2
        color = item.get("color", (239, 68, 68))

        odraw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=8,
            fill=(color[0], color[1], color[2], 26),
            outline=(color[0], color[1], color[2], 245),
            width=3,
        )

        r = 15
        cx = max(r + 4, min(w - r - 4, x1 + 4))
        cy = max(banner_h + r + 2, min(h + banner_h - r - 2, y1 + 4))
        odraw.ellipse(
            [cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2],
            fill=(255, 255, 255, 255),
        )
        odraw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(color[0], color[1], color[2], 255),
        )
        bbox_num = odraw.textbbox((0, 0), num, font=badge_font)
        nw = bbox_num[2] - bbox_num[0]
        nh = bbox_num[3] - bbox_num[1]
        odraw.text(
            (cx - nw // 2, cy - nh // 2 - 2),
            num,
            font=badge_font,
            fill=(255, 255, 255, 255),
        )
        placed_rects.append((cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4))
        badge_infos.append((cx, cy))

    # Pass 2: Draw callout pills with automatic collision avoidance
    for item in callouts:
        num = str(item["num"])
        bx1, by1, bx2, by2 = item["box"]
        y1 = by1 + banner_h
        y2 = by2 + banner_h
        x1, x2 = bx1, bx2
        color = item.get("color", (239, 68, 68))
        label = item.get("label", "")
        label_pos = item.get("label_pos", "top")

        if label:
            tb = odraw.textbbox((0, 0), f"({num}) {label}", font=label_font)
            tw = (tb[2] - tb[0]) + 18
            th = (tb[3] - tb[1]) + 12

            if label_pos == "bottom":
                lx = max(8, min(w - tw - 8, (x1 + x2) // 2 - tw // 2))
                ly = min(h + banner_h - th - 6, y2 + 12)
            elif label_pos == "right":
                lx = min(w - tw - 8, x2 + 16)
                ly = max(banner_h + 6, min(h + banner_h - th - 6, (y1 + y2) // 2 - th // 2))
            elif label_pos == "left":
                lx = max(8, x1 - tw - 16)
                ly = max(banner_h + 6, min(h + banner_h - th - 6, (y1 + y2) // 2 - th // 2))
            else:  # top
                lx = max(8, min(w - tw - 8, (x1 + x2) // 2 - tw // 2))
                ly = max(banner_h + 6, y1 - th - 12)

            # Shift vertically if overlapping any previously placed badge or label
            for _attempt in range(16):
                cand = (lx, ly, lx + tw, ly + th)
                if not any(_overlaps(cand, prev) for prev in placed_rects):
                    break
                if label_pos == "top":
                    ly = max(banner_h + 6, ly - (th + 8))
                else:
                    ly = min(h + banner_h - th - 6, ly + (th + 8))

            placed_rects.append((lx, ly, lx + tw, ly + th))

            if label_pos == "bottom":
                arrow_start = (lx + tw // 2, ly)
                arrow_end = (max(x1 + 10, min(x2 - 10, lx + tw // 2)), y2 + 2)
            elif label_pos == "right":
                arrow_start = (lx, ly + th // 2)
                arrow_end = (x2 + 2, (y1 + y2) // 2)
            elif label_pos == "left":
                arrow_start = (lx + tw, ly + th // 2)
                arrow_end = (x1 - 2, (y1 + y2) // 2)
            else:
                arrow_start = (lx + tw // 2, ly + th)
                arrow_end = (max(x1 + 10, min(x2 - 10, lx + tw // 2)), y1 - 2)

            _draw_arrow(odraw, arrow_start, arrow_end, (color[0], color[1], color[2]), width=3)
            odraw.rounded_rectangle(
                [lx, ly, lx + tw, ly + th],
                radius=6,
                fill=(15, 23, 42, 242),
                outline=(color[0], color[1], color[2], 255),
                width=2,
            )
            odraw.text(
                (lx + 9, ly + 4),
                f"({num}) {label}",
                font=label_font,
                fill=(255, 255, 255, 255),
            )

    return Image.alpha_composite(canvas.convert("RGBA"), overlay).convert("RGB")


def generate_all_assets() -> dict[str, Path]:
    _enable_dpi_awareness()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(
        prefix="inphieuhienvat-guide-gen-", ignore_cleanup_errors=True
    ) as tmp_dir:
        tmp_path = Path(tmp_dir)
        os.environ["LOCALAPPDATA"] = str(tmp_path)
        os.environ["INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT"] = "1"
        os.environ["PYTEST_CURRENT_TEST"] = "guide_generator"

        from core.po_registry import PORegistry
        from core.slip_printer_engine import (
            create_record,
            generate_pdf_from_records,
            generate_preview_image,
            get_default_layout_config,
        )
        from ui.main_window import SlipPrinterApp

        fixture_csv_root = REPO_ROOT / "tests" / "fixtures" / "inspection_data"
        app = SlipPrinterApp()
        # Clean up any sample record from shared DB and switch to isolated temp DB for screenshot generation
        try:
            app.app_state.po_registry.delete_combo("1126000102", "00010", "+001", "002/003")
            app.app_state.po_registry.close()
        except Exception:
            pass
        app.app_state.po_registry = PORegistry(tmp_path / "guide_po_registry.db")

        app.geometry("1360x840+40+30")
        app._apply_theme_mode("Light", persist=False)
        app.app_state.inspection_root_var.set(str(fixture_csv_root))
        app.update_idletasks()
        app.update()
        time.sleep(0.25)

        # Register 1 duplicate PO in isolated temp DB so duplicate row highlighting is demonstrated in real life
        app.app_state.po_registry.register_combo("1126000102", "00010", "+001", "002/003")

        sample_records = [
            create_record(
                row_number=4,
                item_code="302YJ03340",
                item_name="BOTTLE WASTE",
                carton_qty=60,
                total_qty=180,
                po="1126000101",
                po_detail="00010",
                po_sub="+001",
                box="001/003",
                rev="02",
                lot="",
                cav_no="1, 2",
            ),
            create_record(
                row_number=5,
                item_code="302YJ03340",
                item_name="BOTTLE WASTE",
                carton_qty=60,
                total_qty=180,
                po="1126000102",
                po_detail="00010",
                po_sub="+001",
                box="002/003",
                rev="02",
                lot="",
                cav_no="1, 2",
            ),
            create_record(
                row_number=6,
                item_code="302YJ12010",
                item_name="FRAME DRUM",
                carton_qty=18,
                total_qty=36,
                po="1126000103",
                po_detail="00010",
                po_sub="+001",
                box="001/002",
                rev="08",
                lot="",
                cav_no="1, 2",
            ),
            create_record(
                row_number=7,
                item_code="302YJ14030",
                item_name="CASE DLP",
                carton_qty=30,
                total_qty=90,
                po="1126000104",
                po_detail="00010",
                po_sub="+001",
                box="001/003",
                rev="03",
                lot="",
                cav_no="1, 2",
            ),
        ]

        # Ensure synchronous preview rendering for crisp screenshot capture
        def _sync_preview() -> None:
            if not app.app_state.records:
                return
            idx = min(app.app_state.selected_record_index, len(app.app_state.records) - 1)
            rec = app.app_state.records[idx]
            img = generate_preview_image(rec, app.app_state.paths.template_path, app.app_state.layout_config)
            app.app_state.preview_source_image = img
            app.data_tab.update_preview_display()

        # =====================================================================
        # CHAPTER 1: EXCEL IMPORT & DUPLICATE EDI CHECK
        # =====================================================================
        app.notebook.select(0)
        app.set_records(sample_records, select_index=0, source="Đã nạp 4 dòng mẫu từ DummySlip.xlsx.")
        _sync_preview()
        app.update_idletasks()
        app.update()

        img_ch1_raw = _capture_window_image(app)
        ch1_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, app.sidebar.excel_import_button, pad=6),
                "color": (37, 99, 235),
                "label": "Bước 1: Chọn tệp Excel (.xlsx) & bấm 'Nhập từ Excel'",
                "label_pos": "right",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, app.data_tab.table_frame, pad=4),
                "color": (239, 68, 68),
                "label": "Bước 2: Bảng tự tô ĐỎ các dòng trùng mã PO/Box đã xuất",
                "label_pos": "top",
            },
            {
                "num": 3,
                "box": _widget_rel_box(app, app.data_tab.preview_frame, pad=4),
                "color": (16, 185, 129),
                "label": "Bước 3: Kiểm tra ảnh xem trước tem & chuỗi QR 129 ký tự",
                "label_pos": "left",
            },
            {
                "num": 4,
                "box": _widget_rel_box(app, app.data_tab.btn_clear_all_records, pad=6),
                "color": (245, 158, 11),
                "label": "Bước 4: Bấm nút 'Xóa tất cả' để làm trống toàn bộ bảng",
                "label_pos": "top",
            },
        ]
        ch1_path = ASSETS_DIR / "ch01_excel_import.png"
        _annotate_image(
            img_ch1_raw,
            "CHUYÊN ĐỀ 1: NHẬP DỮ LIỆU TỪ EXCEL & KIỂM TRA TRÙNG LẶP MÃ EDI",
            "Luồng thao tác chuẩn khi in hàng loạt từ file Excel sản xuất — Tự động phát hiện và tô đỏ dòng trùng PO + Box",
            ch1_callouts,
        ).save(ch1_path, quality=95)

        # =====================================================================
        # CHAPTER 2: MANUAL INPUT, AUTO CSV LOOKUP & SPLIT CAV
        # =====================================================================
        app.notebook.select(0)
        app.app_state.item_code_var.set("302YJ03340")
        app.controller.on_item_code_input_changed(force_reload=True)
        app.app_state.box_var.set("001/004")
        app.app_state.split_cav_var.set(True)
        app.controller.on_split_cav_toggled()
        app.controller.set_selected_cavs([1])
        _sync_preview()
        app.update_idletasks()
        app.update()

        img_ch2_raw = _capture_window_image(app)
        ch2_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, app.data_tab.item_code_entry, pad=6),
                "color": (37, 99, 235),
                "label": "Bước 1: Nhập Mã hàng rồi nhấn Enter -> Tự điền Tên, Rev, SL/thùng, CAV",
                "label_pos": "bottom",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, app.data_tab.sw_split_cav, pad=6),
                "color": (245, 158, 11),
                "label": "Bước 2: Bật 'Tách CAV' nếu muốn chọn riêng từng số khuôn (CAV)",
                "label_pos": "top",
            },
            {
                "num": 3,
                "box": _widget_rel_box(app, app.data_tab.cav_selector_frame, pad=6),
                "color": (16, 185, 129),
                "label": "Bước 3: Tích chọn các số CAV thực tế đóng trong thùng (VD: CAV 1)",
                "label_pos": "bottom",
            },
            {
                "num": 4,
                "box": _widget_rel_box(app, app.data_tab.get_add_button_widget(), pad=6),
                "color": (239, 68, 68),
                "label": "Bước 4: Bấm '+ Thêm mới' (Hệ thống tự cấp PO 10 số duy nhất trên LAN)",
                "label_pos": "bottom",
            },
        ]
        ch2_path = ASSETS_DIR / "ch02_manual_cav.png"
        _annotate_image(
            img_ch2_raw,
            "CHUYÊN ĐỀ 2: NHẬP THỦ CÔNG, TRA CỨU CSV TỰ ĐỘNG & CHẾ ĐỘ TÁCH CAV",
            "Tự động lấy dữ liệu chuẩn từ thư mục Inspection_data trên mạng LAN (\\10.170.178.1) & hỗ trợ tách lẻ từng CAV",
            ch2_callouts,
        ).save(ch2_path, quality=95)

        # Reset split_cav for subsequent chapters
        app.app_state.split_cav_var.set(False)
        app.controller.on_split_cav_toggled()
        _sync_preview()

        # =====================================================================
        # CHAPTER 3: QR SCANNER (SPLIT 分割 / RETURN 戻入 / REISSUE CẤP LẠI)
        # =====================================================================
        app.notebook.select(3)
        app.update_idletasks()
        app.update()
        panel = app.qr_tab.scan_panel
        sample_qr = sample_records[0].qr_payload
        panel.scan_input_var.set(sample_qr)
        panel.process_scanned_code()
        panel.carton_qty_var.set("20")
        panel._update_payload_preview()
        app.update_idletasks()
        app.update()

        img_ch3_raw = _capture_window_image(app)
        ch3_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, panel.scan_entry, pad=6),
                "color": (37, 99, 235),
                "label": "Bước 1: Đặt con trỏ vào ô Quét QR và bắn súng mã vạch (tự giải mã 129 ký tự)",
                "label_pos": "bottom",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, panel.mode_segment, pad=6),
                "color": (245, 158, 11),
                "label": "Bước 2: Chọn nghiệp vụ: Phân tách (Chia lẻ) / Hoàn kho (Trả kho) / In lại tem",
                "label_pos": "top",
            },
            {
                "num": 3,
                "box": _widget_rel_box(app, panel.form_frame, pad=4),
                "color": (16, 185, 129),
                "label": "Bước 3: Nhập số lượng tách mới (Hệ thống tự tính mã PO chi tiết 10010, 20010...)",
                "label_pos": "bottom",
            },
            {
                "num": 4,
                "box": _widget_rel_box(app, panel.payload_box, pad=6),
                "color": (239, 68, 68),
                "label": "Bước 4: Kiểm tra chuỗi QR 129 ký tự mới & Bấm '+ Thêm vào danh sách in'",
                "label_pos": "top",
            },
        ]
        ch3_path = ASSETS_DIR / "ch03_qr_scan.png"
        _annotate_image(
            img_ch3_raw,
            "CHUYÊN ĐỀ 3: QUÉT MÃ QR — PHÂN TÁCH (CHIA LẺ THÙNG), HOÀN KHO & CẤP LẠI PHIẾU",
            "Giải mã tức thì tem hiện vật 129 ký tự bằng súng bắn QR — Tự động cấp mã nhánh phân tách/hoàn kho chuẩn KDTVN",
            ch3_callouts,
        ).save(ch3_path, quality=95)

        # =====================================================================
        # CHAPTER 4: PREVIEW SLIP ANATOMY & PDF EXPORT (A4 6 SLIPS / LETTER 4 SLIPS)
        # =====================================================================
        app.notebook.select(0)
        app.set_records(sample_records, select_index=0)
        _sync_preview()
        app.update_idletasks()
        app.update()

        # Build a composite visual showing the Sidebar PDF Controls + Real Rendered Slip Anatomy
        img_ch4_raw = _capture_window_image(app)
        # Overlay a high-resolution rendered slip inset on the right side for crystal-clear inspection
        slip_img = generate_preview_image(
            sample_records[0],
            app.app_state.paths.template_path,
            get_default_layout_config(),
            zoom=2.2,
        ).convert("RGB")
        sw, sh = slip_img.size
        target_sw = 560
        target_sh = int(sh * (target_sw / sw))
        slip_resized = slip_img.resize((target_sw, target_sh), Image.Resampling.LANCZOS)

        # Paste inset with emerald frame on right side of img_ch4_raw
        ix = img_ch4_raw.width - target_sw - 28
        iy = 110
        draw_ch4 = ImageDraw.Draw(img_ch4_raw)
        draw_ch4.rounded_rectangle(
            [ix - 8, iy - 36, ix + target_sw + 8, iy + target_sh + 8],
            radius=10,
            fill=(15, 23, 42),
            outline=(16, 185, 129),
            width=3,
        )
        draw_ch4.text(
            (ix + 8, iy - 28),
            "MẪU TEM HIỆN VẬT THỰC TẾ KHI XUẤT RA PDF (A4: 6 TEM / LETTER: 4 TEM)",
            font=_load_font(13, bold=True),
            fill=(110, 231, 183),
        )
        img_ch4_raw.paste(slip_resized, (ix, iy))

        ch4_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, app.sidebar.paper_size_seg, pad=6),
                "color": (245, 158, 11),
                "label": "Bước 1: Chọn khổ giấy máy in (A4 chuẩn = 6 tem/trang, Letter = 4 tem/trang)",
                "label_pos": "right",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, app.sidebar.generate_button, pad=6),
                "color": (16, 185, 129),
                "label": "Bước 2: Bấm 'Tạo PDF' để kết xuất và lưu chống trùng lên LAN DB",
                "label_pos": "right",
            },
            {
                "num": 3,
                "box": _widget_rel_box(app, app.sidebar.open_pdf_button, pad=6),
                "color": (37, 99, 235),
                "label": "Bước 3: Bấm 'Mở PDF vừa tạo' và chọn tỷ lệ in Actual Size (100%)",
                "label_pos": "right",
            },
            {
                "num": 4,
                "box": (ix, iy, ix + target_sw, iy + target_sh),
                "color": (239, 68, 68),
                "label": "Tem in chuẩn: Đầy đủ Mã vạch 1D Code39, QR 129 ký tự, CAV No. (1, 2) & ô đóng dấu QC",
                "label_pos": "bottom",
            },
        ]
        ch4_path = ASSETS_DIR / "ch04_pdf_export.png"
        _annotate_image(
            img_ch4_raw,
            "CHUYÊN ĐỀ 4: XEM TRƯỚC TEM HIỆN VẬT & XUẤT FILE PDF IN ẤN (KHỔ A4 / LETTER)",
            "Đảm bảo tỷ lệ 100% không co hình — Tự động dàn 6 tem/trang (A4) hoặc 4 tem/trang (Letter) kèm khe cắt 5.0mm",
            ch4_callouts,
        ).save(ch4_path, quality=95)

        # =====================================================================
        # CHAPTER 5: LAYOUT 2026 CUSTOMIZATION & EDI HISTORY / PART MASTER
        # =====================================================================
        app.notebook.select(1)
        app.update_idletasks()
        app.update()

        img_ch5_raw = _capture_window_image(app)
        ch5_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, app.layout_tab.options_card, pad=6),
                "color": (16, 185, 129),
                "label": "1. Công tắc thông minh 2026: Ẩn/Hiện tổng SL & số thứ tự thùng trên mặt tem",
                "label_pos": "bottom",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, app.layout_tab.layout_tree, pad=4),
                "color": (37, 99, 235),
                "label": "2. Bảng tọa độ từng trường trên tem (X, Y, Rộng, Cao, Cỡ chữ pt)",
                "label_pos": "top",
            },
            {
                "num": 3,
                "box": (
                    _widget_rel_box(app, app.notebook, pad=0)[0] + 150,
                    _widget_rel_box(app, app.notebook, pad=0)[1],
                    _widget_rel_box(app, app.notebook, pad=0)[0] + 540,
                    _widget_rel_box(app, app.notebook, pad=0)[1] + 34,
                ),
                "color": (245, 158, 11),
                "label": "3. Tab 'Lịch sử Đăng ký EDI' & 'Master Linh Kiện' để tra cứu PO đã phát hành",
                "label_pos": "bottom",
            },
        ]
        ch5_path = ASSETS_DIR / "ch05_layout_history.png"
        _annotate_image(
            img_ch5_raw,
            "CHUYÊN ĐỀ 5: TÙY CHỈNH LAYOUT TEM 2026, LỊCH SỬ ĐĂNG KÝ EDI & KHO MASTER",
            "Tinh chỉnh vị trí in thực tế theo từng máy in tại xưởng và quản lý lịch sử mã PO chống in trùng",
            ch5_callouts,
        ).save(ch5_path, quality=95)

        # =====================================================================
        # CHAPTER 6: TROUBLESHOOTING & OFFLINE / ERROR HANDLING
        # =====================================================================
        app.notebook.select(0)
        app.update_idletasks()
        app.update()

        img_ch6_raw = _capture_window_image(app)
        ch6_callouts = [
            {
                "num": 1,
                "box": _widget_rel_box(app, app.db_status_badge, pad=6),
                "color": (16, 185, 129),
                "label": "1. Đèn báo kết nối LAN DB: Màu xanh = Tự sinh PO; Màu đỏ = Chế độ Offline",
                "label_pos": "bottom",
            },
            {
                "num": 2,
                "box": _widget_rel_box(app, app.data_tab.btn_unlock_po, pad=8),
                "color": (245, 158, 11),
                "label": "2. Nút Khóa/Mở khóa: Mở khóa nhập số PO thủ công khi mất mạng LAN",
                "label_pos": "bottom",
            },
            {
                "num": 3,
                "box": _widget_rel_box(app, app.data_tab.cav_entry, pad=6),
                "color": (37, 99, 235),
                "label": "3. Ô CAV No.: Tự đọc từ CSV trên LAN hoặc cho phép nhập tay (1-16) khi thiếu file",
                "label_pos": "bottom",
            },
            {
                "num": 4,
                "box": _widget_rel_box(app, app.update_btn, pad=6),
                "color": (239, 68, 68),
                "label": "4. Kiểm tra bản cập nhật mới nhất từ máy chủ LAN (\\\\fstvn01)",
                "label_pos": "left",
            },
        ]
        ch6_path = ASSETS_DIR / "ch06_troubleshooting.png"
        _annotate_image(
            img_ch6_raw,
            "CHUYÊN ĐỀ 6: XỬ LÝ SỰ CỐ THƯỜNG GẶP (MẤT MẠNG LAN, LỖI CSV, CẬP NHẬT PHẦN MỀM)",
            "Cách nhận biết trạng thái kết nối LAN, mở khóa nhập PO tay, nạp lại CSV và tự động ghi log chẩn đoán",
            ch6_callouts,
        ).save(ch6_path, quality=95)

        app.destroy()

    # Build standalone HTML & PDF manuals from the 6 chapters
    from ui.components.user_guide_content import USER_GUIDE_CHAPTERS

    html_path = _build_html_manual(USER_GUIDE_CHAPTERS)
    pdf_path = _build_pdf_manual(USER_GUIDE_CHAPTERS)
    return {
        "ch01": ch1_path,
        "ch02": ch2_path,
        "ch03": ch3_path,
        "ch04": ch4_path,
        "ch05": ch5_path,
        "ch06": ch6_path,
        "html": html_path,
        "pdf": pdf_path,
    }


def _build_html_manual(chapters: list[dict[str, Any]]) -> Path:
    """Create a rich standalone interactive HTML manual with embedded base64 images and lightbox zoom."""
    sections_html = []
    nav_html = []

    for idx, ch in enumerate(chapters):
        img_path = ASSETS_DIR / ch["image_filename"]
        b64_data = ""
        if img_path.is_file():
            b64_data = base64.b64encode(img_path.read_bytes()).decode("ascii")

        nav_html.append(
            f'<a href="#{ch["id"]}" class="nav-item"><span class="badge">{idx + 1}</span> {ch["short_title"]}</a>'
        )

        steps_cards = []
        for step in ch["steps"]:
            steps_cards.append(
                f"""
                <div class="step-card">
                    <div class="step-num" style="background:{step.get('color', '#2563EB')}">{step['num']}</div>
                    <div class="step-body">
                        <h4>{step['title']}</h4>
                        <p>{step['detail']}</p>
                    </div>
                </div>
                """
            )

        tips_list = "".join(f"<li>{tip}</li>" for tip in ch.get("tips", []))
        sections_html.append(
            f"""
            <section id="{ch['id']}" class="chapter-card">
                <div class="chapter-header">
                    <span class="chapter-tag">CHUYÊN ĐỀ {idx + 1} / {len(chapters)}</span>
                    <h2>{ch['title']}</h2>
                    <p class="chapter-summary">{ch['summary']}</p>
                </div>
                <div class="screenshot-box">
                    <img src="data:image/png;base64,{b64_data}" alt="{ch['title']}" onclick="openLightbox(this.src, '{ch['title']}')" />
                    <div class="zoom-hint">🔍 Bấm vào hình ảnh để phóng to toàn màn hình</div>
                </div>
                <div class="steps-grid">
                    {''.join(steps_cards)}
                </div>
                <div class="tips-box">
                    <strong>💡 Lưu ý quan trọng tại xưởng:</strong>
                    <ul>{tips_list}</ul>
                </div>
            </section>
            """
        )

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Cẩm Nang Hướng Dẫn Sử Dụng — In Phiếu Hiện Vật (KDTVN)</title>
<style>
:root {{
    --bg: #0f172a;
    --card: #1e293b;
    --text: #f8fafc;
    --muted: #94a3b8;
    --accent: #10b981;
    --blue: #2563eb;
    --border: #334155;
}}
* {{ box-sizing: border-box; }}
body {{
    margin: 0;
    font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.55;
}}
.layout {{
    display: grid;
    grid-template-columns: 290px 1fr;
    min-height: 100vh;
}}
.sidebar {{
    background: #0b1120;
    border-right: 1px solid var(--border);
    padding: 24px 16px;
    position: sticky;
    top: 0;
    height: 100vh;
    overflow-y: auto;
}}
.brand {{
    font-size: 18px;
    font-weight: 700;
    color: #fff;
    margin-bottom: 6px;
}}
.brand-sub {{
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 18px;
}}
.search-box {{
    width: 100%;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid var(--border);
    background: var(--card);
    color: #fff;
    margin-bottom: 16px;
}}
.nav-item {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    color: #cbd5e1;
    text-decoration: none;
    border-radius: 8px;
    margin-bottom: 6px;
    font-size: 14px;
    font-weight: 600;
}}
.nav-item:hover {{
    background: var(--card);
    color: #fff;
}}
.badge {{
    background: var(--blue);
    color: #fff;
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 12px;
    flex-shrink: 0;
}}
.content {{
    padding: 32px 40px;
    max-width: 1280px;
}}
.chapter-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px;
    margin-bottom: 36px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
}}
.chapter-tag {{
    display: inline-block;
    background: rgba(16,185,129,0.15);
    color: #34d399;
    font-size: 12px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 999px;
}}
.chapter-header h2 {{
    margin: 10px 0 6px;
    font-size: 22px;
}}
.chapter-summary {{
    color: var(--muted);
    margin-top: 0;
}}
.screenshot-box {{
    margin: 18px 0 22px;
    background: #090d16;
    border: 2px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    text-align: center;
}}
.screenshot-box img {{
    width: 100%;
    height: auto;
    display: block;
    cursor: zoom-in;
}}
.zoom-hint {{
    padding: 8px;
    font-size: 12px;
    color: #38bdf8;
    background: rgba(15,23,42,0.9);
}}
.steps-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 14px;
    margin-bottom: 18px;
}}
.step-card {{
    display: flex;
    gap: 14px;
    background: rgba(15,23,42,0.65);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
}}
.step-num {{
    width: 32px;
    height: 32px;
    border-radius: 50%;
    color: #fff;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}}
.step-body h4 {{
    margin: 0 0 4px;
    font-size: 15px;
}}
.step-body p {{
    margin: 0;
    font-size: 13.5px;
    color: #cbd5e1;
}}
.tips-box {{
    background: rgba(245,158,11,0.12);
    border-left: 4px solid #f59e0b;
    padding: 14px 18px;
    border-radius: 8px;
    font-size: 13.5px;
}}
.tips-box ul {{
    margin: 6px 0 0;
    padding-left: 20px;
}}
#lightbox {{
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.92);
    z-index: 9999;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    padding: 20px;
}}
#lightbox img {{
    max-width: 96vw;
    max-height: 88vh;
    border-radius: 8px;
    border: 2px solid #10b981;
}}
#lightbox-caption {{
    margin-top: 10px;
    color: #fff;
    font-weight: 600;
}}
@media print {{
    .sidebar {{ display: none; }}
    .layout {{ display: block; }}
    body {{ background: #fff; color: #000; }}
    .chapter-card {{ break-inside: avoid; border: 1px solid #ccc; background: #fff; box-shadow: none; }}
}}
</style>
</head>
<body>
<div class="layout">
    <aside class="sidebar">
        <div class="brand">📖 In Phiếu Hiện Vật</div>
        <div class="brand-sub">Cẩm nang Trực quan Người dùng Thật (KDTVN)</div>
        <input type="search" id="searchInput" class="search-box" placeholder="🔍 Tìm thao tác (VD: Tách CAV, QR)..." oninput="filterChapters(this.value)" />
        <nav>
            {''.join(nav_html)}
        </nav>
    </aside>
    <main class="content">
        {''.join(sections_html)}
    </main>
</div>
<div id="lightbox" onclick="this.style.display='none'">
    <img id="lightbox-img" src="" alt="Zoom" />
    <div id="lightbox-caption"></div>
</div>
<script>
function openLightbox(src, title) {{
    document.getElementById('lightbox-img').src = src;
    document.getElementById('lightbox-caption').textContent = title + ' (Bấm bất kỳ đâu hoặc nhấn Esc để đóng)';
    document.getElementById('lightbox').style.display = 'flex';
}}
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') document.getElementById('lightbox').style.display = 'none';
}});
function filterChapters(q) {{
    const norm = (q || '').toLowerCase().trim();
    document.querySelectorAll('.chapter-card').forEach(sec => {{
        const txt = sec.innerText.toLowerCase();
        sec.style.display = (!norm || txt.includes(norm)) ? 'block' : 'none';
    }});
}}
</script>
</body>
</html>
"""
    out_html = ASSETS_DIR / "huong_dan_su_dung.html"
    out_html.write_text(html_content, encoding="utf-8")
    return out_html


def _strip_unsupported_pdf_glyphs(text: str) -> str:
    """Remove supplementary-plane emojis and variation selectors not supported by Segoe UI standard TTF in PyMuPDF."""
    out: list[str] = []
    for ch in text:
        cp = ord(ch)
        if cp > 0xFFFF or cp in (0xFE0F, 0xFE0E, 0x2795, 0x2705):
            continue
        out.append(ch)
    cleaned = "".join(out)
    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")
    return cleaned.strip()


def _build_pdf_manual(chapters: list[dict[str, Any]]) -> Path:
    """Create a multi-page printable A4 landscape PDF manual with the annotated screenshots and steps."""
    doc = fitz.open()
    font_path = r"C:\Windows\Fonts\segoeui.ttf"
    font_bold_path = r"C:\Windows\Fonts\segoeuib.ttf"

    for idx, ch in enumerate(chapters):
        # Landscape A4: 842 x 595 pt
        page = doc.new_page(width=842, height=595)
        page.draw_rect(fitz.Rect(0, 0, 842, 54), color=(0.06, 0.09, 0.16), fill=(0.06, 0.09, 0.16))
        page.insert_text(
            fitz.Point(24, 24),
            _strip_unsupported_pdf_glyphs(
                f"CẨM NANG SỬ DỤNG: IN PHIẾU HIỆN VẬT — CHUYÊN ĐỀ {idx + 1}/{len(chapters)}: {ch['title'].upper()}"
            ),
            fontsize=13,
            fontfile=font_bold_path if os.path.exists(font_bold_path) else None,
            fontname="F0" if os.path.exists(font_bold_path) else "helv",
            color=(1, 1, 1),
        )
        page.insert_text(
            fitz.Point(24, 42),
            _strip_unsupported_pdf_glyphs(ch["summary"]),
            fontsize=9.5,
            fontfile=font_path if os.path.exists(font_path) else None,
            fontname="F1" if os.path.exists(font_path) else "helv",
            color=(0.75, 0.82, 0.92),
        )

        img_path = ASSETS_DIR / ch["image_filename"]
        if img_path.is_file():
            page.insert_image(fitz.Rect(20, 64, 545, 420), filename=str(img_path), keep_proportion=True)

        # Right column: steps
        y_cursor = 68.0
        for step in ch["steps"]:
            box_rect = fitz.Rect(558, y_cursor, 822, y_cursor + 74)
            page.draw_rect(box_rect, color=(0.82, 0.86, 0.92), fill=(0.96, 0.98, 1.0), width=1)
            page.insert_textbox(
                fitz.Rect(566, y_cursor + 5, 814, y_cursor + 24),
                _strip_unsupported_pdf_glyphs(f"Bước ({step['num']}): {step['title']}"),
                fontsize=9.5,
                fontfile=font_bold_path if os.path.exists(font_bold_path) else None,
                fontname="F0" if os.path.exists(font_bold_path) else "helv",
                color=(0.08, 0.15, 0.32),
            )
            page.insert_textbox(
                fitz.Rect(566, y_cursor + 23, 814, y_cursor + 70),
                _strip_unsupported_pdf_glyphs(step["detail"]),
                fontsize=8.5,
                fontfile=font_path if os.path.exists(font_path) else None,
                fontname="F1" if os.path.exists(font_path) else "helv",
                color=(0.2, 0.25, 0.33),
            )
            y_cursor += 80.0

        # Bottom tips bar
        tips_rect = fitz.Rect(20, 430, 545, 575)
        page.draw_rect(tips_rect, color=(0.96, 0.62, 0.04), fill=(1.0, 0.98, 0.92), width=1.2)
        tips_text = "LƯU Ý QUAN TRỌNG TẠI XƯỞNG:\n" + "\n".join(
            f"• {_strip_unsupported_pdf_glyphs(t)}" for t in ch.get("tips", [])
        )
        page.insert_textbox(
            fitz.Rect(28, 436, 537, 569),
            tips_text,
            fontsize=8.8,
            fontfile=font_path if os.path.exists(font_path) else None,
            fontname="F1" if os.path.exists(font_path) else "helv",
            color=(0.35, 0.2, 0.02),
        )

    out_pdf = ASSETS_DIR / "Huong_Dan_Su_Dung_InPhieuHienVat.pdf"
    doc.save(str(out_pdf))
    doc.close()
    return out_pdf


if __name__ == "__main__":
    generated = generate_all_assets()
    for k, p in generated.items():
        print(f"[OK] {k}: {p} ({p.stat().st_size:,} bytes)")
