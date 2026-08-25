"""Vietnamese Interactive Tutorial Script & Factory Function for InPhieuHienVat.

Defines the 4 core business workflow walkthrough steps:
1. Excel Data Import & Duplicate Detection (step_excel_import)
2. Smart QR Scanning with 3 Modes (step_qr_scanner)
3. Auto PO Generation (11YYMMDDNN) & Form Addition (step_auto_po)
4. PDF Generation (4 slips / A4 page) & Direct Printing (step_pdf_generation)
"""
from __future__ import annotations

from typing import Any, Optional
import tkinter as tk
import customtkinter as ctk

from ui.components.tutorial_overlay import TutorialStep


def _resolve_app(app: Optional[Any]) -> Optional[Any]:
    """Helper to resolve the view/root window reference from controller or app instance."""
    if app is None:
        return None
    try:
        if getattr(app, "sidebar", None) is not None or getattr(app, "data_tab", None) is not None:
            return app
        if hasattr(app, "view") and getattr(app, "view") is not None:
            return getattr(app, "view")
    except Exception:
        pass
    return app


def build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]:
    """Constructs the canonical 4-step interactive walkthrough sequence.

    Parameters:
        app: Optional reference to SlipPrinterApp or AppController.
             If None or uninitialized, all widget getters safely return None
             allowing modal centered tooltip display.

    Returns:
        List of 4 TutorialStep instances matching ORIGINAL_REQUEST.md §R2.
    """

    def _get_excel_target() -> Optional[tk.Widget | ctk.CTkBaseClass]:
        try:
            resolved = _resolve_app(app)
            if resolved is None:
                return None
            sidebar = getattr(resolved, "sidebar", None)
            if sidebar is not None:
                if hasattr(sidebar, "get_excel_import_widget"):
                    try:
                        w = sidebar.get_excel_import_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("excel_import_button", "excel_import_btn", "btn_import_excel", "excel_frame"):
                    try:
                        w = getattr(sidebar, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
                return sidebar
            return getattr(resolved, "excel_import_button", getattr(resolved, "excel_import_btn", None))
        except Exception:
            return None

    def _get_qr_target() -> Optional[tk.Widget | ctk.CTkBaseClass]:
        try:
            resolved = _resolve_app(app)
            if resolved is None:
                return None
            # Legacy locations first (older layouts / mock objects); the real app
            # no longer has these buttons, so resolution falls through to qr_tab.
            sidebar = getattr(resolved, "sidebar", None)
            if sidebar is not None:
                if hasattr(sidebar, "get_qr_scan_widget"):
                    try:
                        w = sidebar.get_qr_scan_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("qr_scan_button", "qr_scan_btn", "btn_qr_scan"):
                    try:
                        w = getattr(sidebar, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
            data_tab = getattr(resolved, "data_tab", None)
            if data_tab is not None:
                if hasattr(data_tab, "get_qr_button_widget"):
                    try:
                        w = data_tab.get_qr_button_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("btn_qr_scan", "qr_scan_btn"):
                    try:
                        w = getattr(data_tab, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
            # Preferred: dedicated QR scan tab (consolidates the two legacy buttons)
            qr_tab = getattr(resolved, "qr_tab", None)
            if qr_tab is not None:
                if hasattr(qr_tab, "get_scan_panel_widget"):
                    try:
                        w = qr_tab.get_scan_panel_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                return qr_tab
            return None
        except Exception:
            return None

    def _get_form_target() -> Optional[tk.Widget | ctk.CTkBaseClass]:
        try:
            resolved = _resolve_app(app)
            if resolved is None:
                return None
            data_tab = getattr(resolved, "data_tab", None)
            if data_tab is not None:
                if hasattr(data_tab, "get_form_frame"):
                    try:
                        w = data_tab.get_form_frame()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                if hasattr(data_tab, "get_add_button_widget"):
                    try:
                        w = data_tab.get_add_button_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("form_frame", "btn_add_record", "add_btn", "po_entry"):
                    try:
                        w = getattr(data_tab, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
                return data_tab
            return None
        except Exception:
            return None

    def _get_pdf_target() -> Optional[tk.Widget | ctk.CTkBaseClass]:
        try:
            resolved = _resolve_app(app)
            if resolved is None:
                return None
            sidebar = getattr(resolved, "sidebar", None)
            if sidebar is not None:
                if hasattr(sidebar, "get_generate_pdf_widget"):
                    try:
                        w = sidebar.get_generate_pdf_widget()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("generate_button", "btn_generate_pdf"):
                    try:
                        w = getattr(sidebar, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
            data_tab = getattr(resolved, "data_tab", None)
            if data_tab is not None:
                if hasattr(data_tab, "get_preview_frame"):
                    try:
                        w = data_tab.get_preview_frame()
                        if w is not None:
                            return w
                    except Exception:
                        pass
                for attr in ("preview_frame", "preview_image_label"):
                    try:
                        w = getattr(data_tab, attr, None)
                        if w is not None:
                            return w
                    except Exception:
                        pass
            return None
        except Exception:
            return None

    # Step 1: Nạp dữ liệu từ Excel
    step_1 = TutorialStep(
        step_id="step_excel_import",
        title="1. Nạp dữ liệu từ Excel",
        description=(
            "Chọn file bảng kê Excel (.xlsx) và bấm 'Import từ Excel'.\n\n"
            "• Cột bắt buộc: Mã hàng, Tên hàng, SL thùng, Số box, Rev (01–99).\n"
            "• Cột Ngày/Lot: Nếu để trống sẽ tự động điền 10 dấu cách trong mã QR.\n"
            "• Dữ liệu trùng lặp (trùng mã hàng, PO, box) sẽ được tự động phát hiện và tô nền đỏ cảnh báo."
        ),
        target_widget_getter=_get_excel_target,
        target_tab_index=0,
        tooltip_position="right",
        padding=8,
    )

    # Step 2: Quét mã QR thông minh
    step_2 = TutorialStep(
        step_id="step_qr_scanner",
        title="2. Quét mã QR thông minh",
        description=(
            "Mở tab '📷 Quét QR' (cạnh Lịch sử Đăng ký EDI) để dùng công cụ quét tem chuyên dụng với 3 chế độ:\n\n"
            "1. Phân tách (分割): Quét tem nguồn, rồi phát hành từng tem tách bằng cách tăng chữ số thứ nhất của mã chi tiết (00010 → 10010 → 20010).\n"
            "2. Hoàn kho (戻入): Quét tem cần hoàn; giữ nguyên chữ số thứ nhất và tăng chữ số thứ hai (10010 → 11010, 20010 → 21010, 11010 → 12010).\n"
            "3. In lại (再発行): Giải mã chuỗi QR 129 ký tự và giữ nguyên mã chi tiết của tem đã quét để tái phát hành."
        ),
        target_widget_getter=_get_qr_target,
        target_tab_index=3,
        tooltip_position="right",
        padding=8,
    )

    # Step 3: Tạo mã Auto PO & Thêm phiếu
    step_3 = TutorialStep(
        step_id="step_auto_po",
        title="3. Tạo mã Auto PO & Thêm phiếu",
        description=(
            "Quản lý và nhập tem thủ công tại Tab Dữ liệu:\n\n"
            "• Mã Auto PO: Tự động cấp phát mã PO chuẩn định dạng '11YYMMDDNN' (11 + Năm/Tháng/Ngày + STT 01–99 trong ngày).\n"
            "• Không lo trùng lặp: Cơ sở dữ liệu PO Registry đảm bảo mỗi tem có số PO duy nhất.\n"
            "• Thao tác nhanh: Bấm '➕ Thêm mới' để thêm tem vào bảng in hoặc '📋 Điền mẫu' để thử nghiệm."
        ),
        target_widget_getter=_get_form_target,
        target_tab_index=0,
        tooltip_position="right",
        padding=8,
    )

    # Step 4: Tạo & In phiếu hiện vật PDF
    step_4 = TutorialStep(
        step_id="step_pdf_generation",
        title="4. Tạo & In phiếu hiện vật PDF",
        description=(
            "Xuất và in ấn phiếu hiện vật chất lượng cao:\n\n"
            "• Xem trước trực quan: Kiểm tra hình ảnh tem và chuỗi QR 129 ký tự tại khung xem trước bên phải.\n"
            "• Tiết kiệm giấy in: Hệ thống tự động ghép chuẩn xác 4 phiếu / trang A4 theo đúng layout cấu hình.\n"
            "• Xuất & In: Bấm 'Tạo PDF' để xuất file, sau đó bấm 'Mở PDF vừa tạo' để in trực tiếp."
        ),
        target_widget_getter=_get_pdf_target,
        target_tab_index=0,
        tooltip_position="right",
        padding=8,
    )

    return [step_1, step_2, step_3, step_4]
