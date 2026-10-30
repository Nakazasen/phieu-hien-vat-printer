from __future__ import annotations

from collections import Counter
import os
from tkinter import messagebox, ttk
from typing import Optional

import customtkinter as ctk

from core.po_registry import FIXED_PO_DETAIL, FIXED_PO_SUB
from core.slip_printer_engine import SlipRecord, calculate_a4_page_count
from ui.app_controller import AppController


class DataTabPanel(ctk.CTkFrame):
    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=68, uniform="tab_cols")
        self.grid_columnconfigure(1, weight=32, uniform="tab_cols")
        self.grid_rowconfigure(0, weight=1)

        # ==========================================
        # PANEL TRÁI: FORM NHẬP LIỆU & BẢNG DỮ LIỆU
        # ==========================================
        self.left_panel = ctk.CTkFrame(self, fg_color="transparent")
        left_panel = self.left_panel
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_panel.grid_columnconfigure(0, weight=1)
        left_panel.grid_rowconfigure(0, weight=0)  # Form gọn cố định chiều cao
        left_panel.grid_rowconfigure(1, weight=1)  # Bảng dữ liệu tự động giãn hết chiều cao còn lại

        # --- 1. FORM NHẬP LIỆU GỌN GÀNG (2 CẶP CỘT RỘNG RÃI) ---
        self.form_frame = ctk.CTkFrame(left_panel, corner_radius=12)
        form_frame = self.form_frame
        form_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        form_frame.grid_columnconfigure(1, weight=1)
        form_frame.grid_columnconfigure(3, weight=2)

        # Tiêu đề Form & Ghi chú
        header_row = ctk.CTkFrame(form_frame, fg_color="transparent")
        header_row.grid(row=0, column=0, columnspan=4, sticky="ew", padx=12, pady=(8, 4))
        header_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_row, textvariable=self.app_state.form_mode_var, font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        right_header = ctk.CTkFrame(header_row, fg_color="transparent")
        right_header.grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            right_header,
            text="(*) Bắt buộc · Tổng SL = SL thùng x Box",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=300,
        ).pack(side="right")

        # Hàng 1: Mã hàng (*) | Tên hàng (*)
        self.item_code_entry = self._form_field(form_frame, 1, 0, "Mã hàng (*):", self.app_state.item_code_var, uppercase=True)
        self.item_code_entry.bind("<FocusOut>", self.controller.on_item_code_input_changed, add="+")
        self.item_code_entry.bind("<Return>", self._on_item_code_return, add="+")
        self.item_code_entry.bind("<KP_Enter>", self._on_item_code_return, add="+")
        self.item_name_entry = self._form_field(form_frame, 1, 2, "Tên hàng (*):", self.app_state.item_name_var, uppercase=True)
        self.item_name_entry.bind("<Return>", lambda _e: self._submit_form_or_advance(), add="+")
        self.item_name_entry.bind("<KP_Enter>", lambda _e: self._submit_form_or_advance(), add="+")

        # Hàng 2: SL/thùng(*) | Tổng số lượng (tự tính)
        self.carton_qty_entry = self._form_field(form_frame, 2, 0, "SL/thùng(*):", self.app_state.carton_qty_var)
        self.carton_qty_entry.bind("<Return>", lambda _e: self._submit_form_or_advance(), add="+")
        self.carton_qty_entry.bind("<KP_Enter>", lambda _e: self._submit_form_or_advance(), add="+")
        self.total_qty_entry = self._form_field(
            form_frame, 2, 2, "Tổng SL (tự tính):", self.app_state.total_qty_var, is_readonly=True
        )

        # Hàng 3: Số thùng(*) | Rev (*)
        self.box_entry = self._form_field(form_frame, 3, 0, "Số thùng(*):", self.app_state.box_var)
        self.box_entry.bind("<Return>", lambda _e: self._submit_form_or_advance(), add="+")
        self.box_entry.bind("<KP_Enter>", lambda _e: self._submit_form_or_advance(), add="+")
        self.rev_entry = self._form_field(form_frame, 3, 2, "Rev (*) (01–99):", self.app_state.rev_var)
        self.rev_entry.bind("<FocusOut>", self.controller.on_rev_input_changed, add="+")
        self.rev_entry.bind("<Return>", lambda _e: self._submit_form_or_advance(), add="+")
        self.rev_entry.bind("<KP_Enter>", lambda _e: self._submit_form_or_advance(), add="+")

        # Hàng 4: PO (tự sinh / mở khóa nhập tay) | PO chi tiết & PO phụ (tự sinh)
        is_offline = getattr(self.app_state.po_registry, "is_offline_fallback", False)
        self.po_label = ctk.CTkLabel(
            form_frame,
            text="PO (nhập tay khi ngoại tuyến):" if is_offline else "PO (tự sinh):",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.po_label.grid(row=4, column=0, sticky="w", padx=(12, 4), pady=2)

        po_box_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        po_box_frame.grid(row=4, column=1, sticky="ew", padx=(0, 10), pady=2)
        po_box_frame.grid_columnconfigure(0, weight=1)

        self.po_entry = ctk.CTkEntry(
            po_box_frame, textvariable=self.app_state.po_var, height=28, font=ctk.CTkFont(size=12)
        )
        self.po_entry.grid(row=0, column=0, sticky="ew")
        self.po_entry.configure(state="normal" if is_offline else "disabled")

        self.btn_unlock_po = ctk.CTkButton(
            po_box_frame,
            text="✏️" if is_offline else "🔓",
            width=32,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=("#2563EB", "#1D4ED8") if is_offline else ("gray85", "gray25"),
            hover_color=("#1D4ED8", "#1E40AF") if is_offline else ("gray75", "gray35"),
            text_color="white" if is_offline else ("gray10", "gray90"),
            command=self._toggle_manual_po,
        )
        self.btn_unlock_po.grid(row=0, column=1, padx=(4, 0))
        self.btn_unlock_po.bind(
            "<Enter>",
            lambda _e: self.app_state.status_var.set(
                "💡 Nhấn nút 🔓/🔒 để mở khóa hoặc khóa chế độ nhập số PO thủ công."
            ),
        )

        po_sub_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        po_sub_frame.grid(row=4, column=2, columnspan=2, sticky="ew", padx=(6, 12), pady=2)
        po_sub_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(po_sub_frame, text="Chi tiết:", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, padx=(0, 2)
        )
        self.po_detail_entry = ctk.CTkEntry(po_sub_frame, textvariable=self.app_state.po_detail_var, height=28, font=ctk.CTkFont(size=12))
        self.po_detail_entry.grid(row=0, column=1, sticky="ew", padx=(0, 6))
        self.po_detail_entry.configure(state="disabled")

        ctk.CTkLabel(po_sub_frame, text="Phụ:", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=2, padx=(0, 2)
        )
        self.po_sub_entry = ctk.CTkEntry(po_sub_frame, textvariable=self.app_state.po_sub_var, height=28, font=ctk.CTkFont(size=12))
        self.po_sub_entry.grid(row=0, column=3, sticky="ew")
        self.po_sub_entry.configure(state="disabled")

        # Hàng 5: Ngày/Lot | CAV No. & Công tắc Tách CAV
        self.lot_entry = self._form_field(
            form_frame, 5, 0, "Ngày/Lot:", self.app_state.lot_var, is_readonly=True
        )
        self.lot_entry.bind(
            "<Button-1>",
            lambda _e: self.app_state.status_var.set(
                "🔒 Ô 'Ngày/Lot' đã được khóa theo quy định chuẩn (nhấp đúp nếu cần xem hướng dẫn)."
            ),
        )
        self.lot_entry.bind("<Double-Button-1>", self.controller.warn_lot_field_locked)

        ctk.CTkLabel(
            form_frame, text="CAV No.:", font=ctk.CTkFont(size=11, weight="bold")
        ).grid(row=5, column=2, sticky="w", padx=(12, 4), pady=2)

        cav_ctrl_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        cav_ctrl_frame.grid(row=5, column=3, sticky="ew", padx=(0, 12), pady=2)
        cav_ctrl_frame.grid_columnconfigure(0, weight=1)

        self.cav_entry = ctk.CTkEntry(
            cav_ctrl_frame,
            textvariable=self.app_state.cav_var,
            height=28,
            font=ctk.CTkFont(size=12),
            placeholder_text="Tự động từ CSV hoặc nhập 1-16",
        )
        self.cav_entry.grid(row=0, column=0, sticky="ew")
        self.cav_entry.configure(state="normal")
        self.cav_entry.bind("<FocusOut>", self.controller.on_manual_cav_entry_committed, add="+")
        self.cav_entry.bind("<Return>", self.controller.on_manual_cav_entry_committed, add="+")
        self.cav_entry.bind("<KP_Enter>", self.controller.on_manual_cav_entry_committed, add="+")

        self.sw_split_cav = ctk.CTkSwitch(
            cav_ctrl_frame,
            text="Tách CAV",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self.app_state.split_cav_var,
            progress_color=("#10B981", "#059669"),
            command=self.controller.on_split_cav_toggled,
        )
        self.sw_split_cav.grid(row=0, column=1, padx=(8, 0))

        # Hàng 6: Khung chọn CAV khi bật "Tách CAV" (chỉ hiển thị các CAV hợp lệ trong CSV)
        self.cav_selector_frame = ctk.CTkFrame(form_frame, corner_radius=8, fg_color=("gray92", "gray20"))
        self.cav_selector_frame.grid(row=6, column=0, columnspan=4, sticky="ew", padx=12, pady=(2, 2))
        self.cav_selector_frame.grid_remove()
        self.cav_checkboxes: dict[int, ctk.CTkCheckBox] = {}
        self.cav_check_vars: dict[int, ctk.BooleanVar] = {}

        # Hàng 7: Nút thao tác chính (Primary Actions - Hàng 1)
        btn_bar_1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_bar_1.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(6, 2))
        btn_bar_1.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_add_record = ctk.CTkButton(
            btn_bar_1, text="➕ Thêm mới", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981", hover_color="#059669", text_color="white", command=self.controller.add_record
        )
        self.btn_add_record.grid(row=0, column=0, sticky="ew", padx=3)

        self.btn_update_record = ctk.CTkButton(
            btn_bar_1, text="💾 Cập nhật dòng", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563EB", hover_color="#1D4ED8", text_color="white", command=self.controller.update_selected_record
        )
        self.btn_update_record.grid(row=0, column=1, sticky="ew", padx=3)

        self.btn_delete_record = ctk.CTkButton(
            btn_bar_1, text="🗑️ Xóa dòng", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#EF4444", "#991B1B"), hover_color=("#DC2626", "#7F1D1D"), text_color="white",
            command=self.controller.delete_selected_record
        )
        self.btn_delete_record.grid(row=0, column=2, sticky="ew", padx=3)

        # Hàng 8: Nút tiện ích phụ (Secondary Utilities - Hàng 2)
        btn_bar_2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_bar_2.grid(row=8, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 8))
        btn_bar_2.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            btn_bar_2, text="📋 Điền mẫu", height=28, font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1, border_color=("gray70", "gray40"),
            text_color=("gray30", "gray70"), hover_color=("gray90", "gray20"), command=self.controller.fill_sample_data
        ).grid(row=0, column=0, sticky="ew", padx=3)

        # Viền đậm + chữ đậm để người dùng nhận ra nút xóa form
        self.btn_clear_form = ctk.CTkButton(
            btn_bar_2, text="🧹 Xóa biểu mẫu", height=28, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="transparent", border_width=2, border_color=("#6B7280", "#9CA3AF"),
            text_color=("gray10", "gray90"), hover_color=("gray85", "gray25"), command=self.clear_form
        )
        self.btn_clear_form.grid(row=0, column=1, sticky="ew", padx=3)

        # --- 2. BẢNG DỮ LIỆU (TREEVIEW - CHIẾM TOÀN BỘ KHÔNG GIAN CÒN LẠI) ---
        self.table_frame = ctk.CTkFrame(left_panel, corner_radius=12)
        table_frame = self.table_frame
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(1, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        # Header thanh bảng dữ liệu + nút Xóa tất cả + badge đếm tem (UI/UX Pro Max)
        table_top_bar = ctk.CTkFrame(table_frame, fg_color="transparent")
        table_top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(8, 4))
        table_top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            table_top_bar, text="📋 Danh sách tem sẵn sàng in", font=ctk.CTkFont(size=13, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        self.btn_clear_all_records = ctk.CTkButton(
            table_top_bar,
            text="🗑️ Xóa tất cả",
            width=115,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#FEE2E2", "#7F1D1D"),
            text_color=("#991B1B", "#FCA5A5"),
            hover_color=("#FECACA", "#991B1B"),
            border_width=1,
            border_color=("#FCA5A5", "#B91C1C"),
            corner_radius=6,
            command=self.controller.clear_all_records,
        )
        self.btn_clear_all_records.grid(row=0, column=1, sticky="e", padx=(8, 8))

        self.metrics_badge = ctk.CTkLabel(
            table_top_bar,
            text="📊 0 tem · 0 trang",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E0F2FE", "#0C4A6E"),
            text_color=("#0369A1", "#38BDF8"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.metrics_badge.grid(row=0, column=2, sticky="e")

        style = ttk.Style()
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

        columns = ("row", "item_code", "item_name", "carton_qty", "total_qty", "qty_display", "po", "po_detail", "po_sub", "box", "rev", "cav_no", "lot")
        self.preview_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        headings = {
            "row": "Dòng", "item_code": "Mã hàng", "item_name": "Tên hàng", "carton_qty": "SL thùng",
            "total_qty": "Tổng SL", "qty_display": "Tem hiển thị", "po": "PO", "po_detail": "PO chi tiết",
            "po_sub": "PO phụ", "box": "Box", "rev": "Rev", "cav_no": "CAV No.", "lot": "Ngày/Lot",
        }
        widths = {
            "row": 50, "item_code": 115, "item_name": 180, "carton_qty": 75, "total_qty": 75,
            "qty_display": 95, "po": 100, "po_detail": 85, "po_sub": 75, "box": 75, "rev": 50, "cav_no": 85, "lot": 110,
        }
        for key in columns:
            self.preview_tree.heading(key, text=headings[key])
            self.preview_tree.column(key, width=widths[key], anchor="w")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.preview_tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.preview_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(4, 0))
        tree_scroll_y.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(4, 0))
        tree_scroll_x.grid(row=2, column=0, sticky="ew", padx=(10, 10), pady=(0, 6))
        ctk.CTkLabel(
            table_frame,
            text="Dòng tô đỏ: tem đã xuất hoặc bị lặp trong danh sách.",
            font=ctk.CTkFont(size=11),
            text_color=("#991B1B", "#FCA5A5"),
            anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 6))
        self.preview_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)
        self.preview_tree.bind("<Delete>", lambda _e: self.controller.delete_selected_record(require_confirm=True))

        # Empty state overlay frame
        self.empty_state_frame = ctk.CTkFrame(table_frame, fg_color=("gray95", "gray18"), corner_radius=8)
        ctk.CTkLabel(
            self.empty_state_frame,
            text="📦 Chưa có dữ liệu tem in",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("gray40", "gray60"),
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            self.empty_state_frame,
            text="Hãy chọn tệp Excel và bấm 'Nhập từ Excel' ở thanh bên\nhoặc điền thông tin vào biểu mẫu phía trên để bắt đầu.",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray50"),
            justify="center",
        ).pack(pady=(0, 16))

        # Highlight duplicate rows (theme-adaptive Light/Dark contrast)
        self.apply_theme_tags()

        # ==========================================
        # PANEL PHẢI: XEM TRƯỚC TEM EDI & MÃ QR
        # ==========================================
        self.preview_frame = ctk.CTkFrame(self, corner_radius=12)
        preview_frame = self.preview_frame
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        preview_frame.grid_rowconfigure(2, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        # Header preview kèm thanh công tắc nhanh
        preview_top_bar = ctk.CTkFrame(preview_frame, fg_color="transparent")
        preview_top_bar.grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 4))
        preview_top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(preview_top_bar, text="🔍 Xem trước tem in", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        # Cụm công tắc tùy chọn hiển thị nhanh (Quick switches)
        quick_opts = ctk.CTkFrame(preview_frame, corner_radius=8, fg_color=("gray92", "gray20"))
        quick_opts.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))
        quick_opts.grid_columnconfigure((0, 1), weight=1)

        self.sw_quick_hide_total = ctk.CTkSwitch(
            quick_opts,
            text="Chỉ in SL thùng",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self.app_state.opt_hide_total_qty_var,
            progress_color=("#10B981", "#059669"),
            command=self.controller.on_layout_option_changed,
        )
        self.sw_quick_hide_total.grid(row=0, column=0, padx=(10, 4), pady=5, sticky="w")

        self.sw_quick_hide_pkg = ctk.CTkSwitch(
            quick_opts,
            text="Ẩn PACKAGE QTY",
            font=ctk.CTkFont(size=11, weight="bold"),
            variable=self.app_state.opt_hide_package_qty_var,
            progress_color=("#10B981", "#059669"),
            command=self.controller.on_layout_option_changed,
        )
        self.sw_quick_hide_pkg.grid(row=0, column=1, padx=(4, 10), pady=5, sticky="e")

        self.preview_image_label = ctk.CTkLabel(
            preview_frame, text="Chưa có dữ liệu để xem trước", font=ctk.CTkFont(size=13), text_color="gray50"
        )
        self.preview_image_label.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))
        # Debounce resize: coalesces the <Configure> flood during window drag-resize
        # into a single re-thumbnail pass (prevents redraw storm on weak machines).
        self._preview_resize_job = None
        self._preview_display_key: tuple | None = None
        self._preview_display_source = None
        self.preview_image_label.bind("<Configure>", self._on_preview_resize)

        ctk.CTkLabel(preview_frame, text="Chuỗi QR của dòng đang chọn:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=3, column=0, sticky="w", padx=14, pady=(0, 4)
        )
        self.qr_payload_box = ctk.CTkTextbox(preview_frame, height=65, font=ctk.CTkFont(family="Consolas", size=11))
        self.qr_payload_box.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.qr_payload_box.configure(state="disabled")

        self.btn_refresh_preview = ctk.CTkButton(
            preview_frame, text="🔄 Làm mới xem trước", height=32,
            fg_color=("gray85", "gray25"), text_color=("gray10", "gray90"), hover_color=("gray75", "gray35"),
            command=self.refresh_preview_image
        )
        self.btn_refresh_preview.grid(row=5, column=0, sticky="ew", padx=12, pady=(0, 12))

        # Init state listeners
        self.app_state.carton_qty_var.trace_add("write", self.controller.sync_total_qty)
        self.app_state.box_var.trace_add("write", self.controller.sync_total_qty)

    def _form_field(
        self, parent: ctk.CTkFrame, row: int, column: int, label: str, variable: ctk.StringVar,
        is_readonly: bool = False, is_disabled: bool = False, uppercase: bool = False
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=row, column=column, sticky="w", padx=(12, 4), pady=2
        )
        entry = ctk.CTkEntry(parent, textvariable=variable, height=28, font=ctk.CTkFont(size=12))
        entry.grid(row=row, column=column + 1, sticky="ew", padx=(0, 12 if column == 2 else 10), pady=2)
        if is_readonly:
            entry.configure(state="readonly")
        elif is_disabled:
            entry.configure(state="disabled")
        else:
            entry.bind("<FocusOut>", lambda _event: self._normalize_form_value(variable, uppercase), add="+")
        return entry

    @staticmethod
    def _normalize_form_value(variable: ctk.StringVar, uppercase: bool = False) -> None:
        """Remove pasted outer whitespace; upper-case the two EDI identification fields."""
        normalized = variable.get().strip()
        if uppercase:
            normalized = normalized.upper()
        if normalized != variable.get():
            variable.set(normalized)

    def _submit_form_or_advance(self) -> None:
        """Ergonomic Return handler: if required fields are present, add the record."""
        code = self.app_state.item_code_var.get().strip()
        name = self.app_state.item_name_var.get().strip()
        carton = self.app_state.carton_qty_var.get().strip()
        box = self.app_state.box_var.get().strip()
        if code and name and carton and box:
            self.controller.add_record()
        elif hasattr(self, "btn_add_record"):
            self.controller.add_record()

    def _on_item_code_return(self, event) -> str:
        """Handle Enter key on item code entry: sync text, load CSV/Master metadata, and advance focus."""
        try:
            typed_code = self.item_code_entry.get().strip().upper()
            if typed_code != self.app_state.item_code_var.get():
                self.app_state.item_code_var.set(typed_code)
        except Exception:  # noqa: BLE001
            pass

        self.controller.on_item_code_input_changed(event, force_reload=True)
        if not self.app_state.item_name_var.get().strip():
            if hasattr(self.controller, "is_inspection_source_available") and self.controller.is_inspection_source_available():
                self.item_code_entry.focus_set()
            else:
                self.item_name_entry.focus_set()
        elif not self.app_state.carton_qty_var.get().strip():
            self.carton_qty_entry.focus_set()
        else:
            self.box_entry.focus_set()
        return "break"

    def _toggle_manual_po(self) -> None:
        """Toggle manual PO number input (used when offline or override is requested)."""
        is_offline = getattr(self.app_state.po_registry, "is_offline_fallback", False)
        if is_offline:
            messagebox.showinfo(
                "Chế độ ngoại tuyến",
                "Do mất kết nối cơ sở dữ liệu LAN dùng chung, ô nhập PO đã được mở sẵn "
                "để Quản lý có thể nhập số PO thủ công.\n\n"
                "👉 Hãy nhập số PO được cấp vào ô 'PO (nhập tay)' trước khi thêm dòng.",
            )
            return

        current_state = str(self.po_entry.cget("state"))
        if current_state == "disabled":
            self.po_entry.configure(state="normal")
            self.po_label.configure(text="PO (nhập tay):")
            self.btn_unlock_po.configure(text="🔒", fg_color=("#F59E0B", "#D97706"), text_color="white")
            self.app_state.manual_po_override = True
            self.po_entry.focus_set()
        else:
            self.po_entry.configure(state="disabled")
            self.po_label.configure(text="PO (tự sinh):")
            self.btn_unlock_po.configure(text="🔓", fg_color=("gray85", "gray25"), text_color=("gray10", "gray90"))
            self.app_state.manual_po_override = False
            self.app_state.po_var.set("")

    def set_records(self, records: list[SlipRecord] | None = None, select_index: int | None = None) -> None:
        if records is not None:
            self.app_state.records = records
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        self.app_state.preview_index_map.clear()
        try:
            preview_limit = max(1, int(self.app_state.preview_limit_var.get()))
        except ValueError:
            self.app_state.preview_limit_var.set("50")
            preview_limit = 50

        # Calculate duplicate frequencies within current records (Requirement R2)
        combo_counts = Counter(
            (
                r.po.strip(),
                r.po_detail.strip() or FIXED_PO_DETAIL,
                r.po_sub.strip() or FIXED_PO_SUB,
                r.box.strip(),
            )
            for r in self.app_state.records
            if r.po.strip()
        )

        display_records = self.app_state.records[:preview_limit]
        for display_index, record in enumerate(display_records):
            lot = "(10 dấu cách)" if record.lot == (" " * 10) else record.lot
            values = (
                str(record.row_number), record.item_code, record.item_name, record.carton_qty,
                record.total_qty, record.qty_display, record.po, record.po_detail, record.po_sub,
                record.box, record.rev, record.cav_no, lot
            )
            po = record.po.strip()
            po_detail = record.po_detail.strip() or FIXED_PO_DETAIL
            po_sub = record.po_sub.strip() or FIXED_PO_SUB
            box = record.box.strip()

            is_duplicate = False
            if po:
                combo_key = (po, po_detail, po_sub, box)
                is_duplicate = (
                    self.app_state.po_registry.is_registered(po, po_detail, po_sub, box)
                    or combo_counts[combo_key] > 1
                )

            tags = ("duplicate",) if is_duplicate else ()
            self.preview_tree.insert("", "end", iid=str(display_index), values=values, tags=tags)
            self.app_state.preview_index_map.append(display_index)

        total_recs = len(self.app_state.records)
        paper_size = self.app_state.paper_size_var.get() if hasattr(self.app_state, "paper_size_var") else "A4"
        total_pages = calculate_a4_page_count(total_recs, paper_size=paper_size)

        if self.app_state.records:
            if hasattr(self, "empty_state_frame"):
                self.empty_state_frame.place_forget()
            if hasattr(self, "metrics_badge"):
                self.metrics_badge.configure(
                    text=f"📊 {total_recs} tem · {total_pages} trang ({paper_size})",
                    fg_color=("#D1FAE5", "#064E3B"),
                    text_color=("#059669", "#6EE7B7"),
                )
            self.app_state.summary_var.set(f"Có {len(self.app_state.records)} dòng hợp lệ")
            self.app_state.status_var.set(f"Đang hiển thị {len(display_records)} dòng. Bấm vào một dòng để chỉnh sửa.")

            if select_index is None:
                select_index = 0
            if select_index < len(display_records):
                self._select_tree_row(select_index)
            else:
                self._select_tree_row(0)
        else:
            if hasattr(self, "empty_state_frame"):
                self.empty_state_frame.place(relx=0.5, rely=0.55, anchor="center")
            if hasattr(self, "metrics_badge"):
                self.metrics_badge.configure(
                    text=f"📊 0 tem · 0 trang ({paper_size})",
                    fg_color=("#E0F2FE", "#0C4A6E"),
                    text_color=("#0369A1", "#38BDF8"),
                )
            self.app_state.summary_var.set("Chưa có dữ liệu")
            self.app_state.status_var.set("Thêm dữ liệu bằng biểu mẫu bên trái hoặc nhập từ Excel.")
            self.app_state.preview_source_image = None
            self.reset_preview_display()
            self.preview_image_label.configure(text="Chưa có dữ liệu để xem trước")
            self.set_qr_payload_text("")
            self.app_state.form_mode_var.set("Đang tạo dòng mới")

    def apply_theme_tags(self) -> None:
        """Update Treeview tag colors to match active Light/Dark appearance mode."""
        try:
            is_dark = str(ctk.get_appearance_mode()).lower() == "dark"
        except Exception:  # noqa: BLE001
            is_dark = False
        if is_dark:
            self.preview_tree.tag_configure(
                "duplicate",
                background="#450A0A",
                foreground="#FCA5A5",
            )
        else:
            self.preview_tree.tag_configure(
                "duplicate",
                background="#FEE2E2",
                foreground="#991B1B",
            )

    def _select_tree_row(self, display_index: int) -> None:
        iid = str(display_index)
        if iid in self.preview_tree.get_children():
            self._programmatic_select = True
            try:
                self.preview_tree.selection_set(iid)
                self.preview_tree.focus(iid)
                self.preview_tree.see(iid)
                self._on_tree_selected()
            finally:
                self._programmatic_select = False

    def _on_tree_selected(self, _event=None) -> None:
        selected = self.preview_tree.selection()
        if not selected:
            return

        display_index = int(selected[0])
        if display_index >= len(self.app_state.preview_index_map):
            return

        target_rec_idx = self.app_state.preview_index_map[display_index]
        is_user_click = (_event is not None) and not getattr(self, "_programmatic_select", False)
        if (
            is_user_click
            and not os.environ.get("PYTEST_CURRENT_TEST")
            and self.app_state.form_mode_var.get() == "Đang tạo dòng mới"
            and (
                self.app_state.item_code_var.get().strip()
                or self.app_state.item_name_var.get().strip()
                or self.app_state.box_var.get().strip()
            )
        ):
            confirm = messagebox.askyesno(
                "Chưa thêm dòng đang nhập",
                "Bạn đang nhập dở thông tin dòng mới trên biểu mẫu nhưng chưa bấm '➕ Thêm mới'.\n\n"
                "👉 Bạn có muốn nạp dữ liệu từ dòng vừa chọn và hủy nội dung đang gõ không?",
            )
            if not confirm:
                return

        self.app_state.selected_record_index = target_rec_idx
        record = self.app_state.records[self.app_state.selected_record_index]

        # Load record into form
        self.app_state.item_code_var.set(record.item_code)
        self.app_state.item_name_var.set(record.item_name)
        self.app_state.carton_qty_var.set(record.carton_qty)
        self.app_state.total_qty_var.set(record.total_qty)
        self.app_state.po_var.set(record.po)
        self.app_state.po_detail_var.set(record.po_detail)
        self.app_state.po_sub_var.set(record.po_sub)
        self.app_state.box_var.set(record.box)
        self.app_state.rev_var.set(record.rev)
        self.app_state.lot_var.set("" if record.lot == (" " * 10) else record.lot)
        self.app_state.cav_var.set(record.cav_no)
        if hasattr(self.controller, "sync_cav_state_for_record"):
            self.controller.sync_cav_state_for_record(record)
        self.app_state.form_mode_var.set(f"Đang sửa dòng {record.row_number}")

        self.set_qr_payload_text(record.qr_payload)

        # We need the controller to update the preview image since it requires engine logic
        if self.controller.view:
            self.controller.view.refresh_preview_image()

    def sync_cav_ui(self) -> None:
        """Rebuild or synchronize the CAV selection checkboxes according to valid_cavs and split_cav_var."""
        valid_cavs = list(getattr(self.app_state, "valid_cavs", []))
        is_split = bool(self.app_state.split_cav_var.get())
        selected = getattr(self.app_state, "selected_cavs", [])
        cav_source = getattr(self.app_state, "cav_source", "none")

        # When CAV comes from CSV or when Split CAV is active with valid CAVs, lock cav_entry to readonly.
        # When CSV is unavailable (fallback mode) and Split CAV is off (or no CAVs defined yet), allow manual entry (1-16).
        if cav_source == "csv" or (is_split and valid_cavs):
            self.cav_entry.configure(state="readonly")
        else:
            self.cav_entry.configure(state="normal")

        # Rebuild checkboxes if the set of valid CAVs changed
        if list(self.cav_checkboxes.keys()) != valid_cavs:
            for child in self.cav_selector_frame.winfo_children():
                child.destroy()
            self.cav_checkboxes.clear()
            self.cav_check_vars.clear()

            if valid_cavs:
                ctk.CTkLabel(
                    self.cav_selector_frame,
                    text="Chọn CAV in:",
                    font=ctk.CTkFont(size=11, weight="bold"),
                ).pack(side="left", padx=(8, 6), pady=4)
                for cav_num in valid_cavs:
                    var = ctk.BooleanVar(master=self.app_state.root, value=(cav_num in selected))
                    cb = ctk.CTkCheckBox(
                        self.cav_selector_frame,
                        text=str(cav_num),
                        variable=var,
                        width=44,
                        checkbox_width=18,
                        checkbox_height=18,
                        font=ctk.CTkFont(size=11, weight="bold"),
                        command=lambda c=cav_num: self._on_cav_checkbox_toggled(c),
                    )
                    cb.pack(side="left", padx=4, pady=4)
                    self.cav_checkboxes[cav_num] = cb
                    self.cav_check_vars[cav_num] = var

        for cav_num, var in self.cav_check_vars.items():
            var.set((cav_num in selected) if is_split else True)
            cb = self.cav_checkboxes.get(cav_num)
            if cb is not None:
                cb.configure(state="normal" if is_split else "disabled")

        if is_split and valid_cavs:
            self.cav_selector_frame.grid()
        else:
            self.cav_selector_frame.grid_remove()

    def _on_cav_checkbox_toggled(self, cav_num: int) -> None:
        var = self.cav_check_vars.get(cav_num)
        if var is None:
            return
        self.controller.set_cav_selection(cav_num, bool(var.get()))

    def clear_form(self) -> None:
        for variable in (
            self.app_state.item_code_var, self.app_state.item_name_var, self.app_state.carton_qty_var,
            self.app_state.total_qty_var, self.app_state.po_var, self.app_state.po_detail_var,
            self.app_state.po_sub_var, self.app_state.box_var, self.app_state.rev_var, self.app_state.lot_var,
            self.app_state.cav_var,
        ):
            variable.set("")
        self.app_state.split_cav_var.set(False)
        self.app_state.valid_cavs.clear()
        self.app_state.selected_cavs.clear()
        self.app_state.cav_source = "none"
        self.sync_cav_ui()
        self.app_state.form_mode_var.set("Đang tạo dòng mới")
        self.app_state.status_var.set("Đã xóa biểu mẫu. Sẵn sàng nhập mã hàng mới.")
        if hasattr(self.controller, "_last_auto_po"):
            self.controller._last_auto_po = None
        if hasattr(self.controller, "_last_added_item_code"):
            self.controller._last_added_item_code = None
        if hasattr(self.controller, "_last_resolved_cav_item_code"):
            self.controller._last_resolved_cav_item_code = ""
        if hasattr(self.controller, "_last_resolved_cav_not_found"):
            self.controller._last_resolved_cav_not_found = False

    def set_qr_payload_text(self, payload: str) -> None:
        self.qr_payload_box.configure(state="normal")
        self.qr_payload_box.delete("1.0", "end")
        self.qr_payload_box.insert("1.0", payload)
        self.qr_payload_box.configure(state="disabled")

    def _on_preview_resize(self, _event=None) -> None:
        # Debounced: fires once 80ms after the last resize event of a burst
        if self._preview_resize_job is not None:
            try:
                self.after_cancel(self._preview_resize_job)
            except Exception:  # noqa: BLE001
                pass
        self._preview_resize_job = self.after(80, self._do_preview_resize)

    def _do_preview_resize(self) -> None:
        self._preview_resize_job = None
        try:
            if self.controller.view:
                self.controller.view.update_preview_display()
        except Exception:  # noqa: BLE001
            pass

    def update_preview_display(self) -> None:
        source = self.app_state.preview_source_image
        if source is None:
            return

        width = max(self.preview_image_label.winfo_width() - 16, 120)
        height = max(self.preview_image_label.winfo_height() - 16, 120)
        if width <= 0 or height <= 0:
            return

        # Skip re-thumbnail when the same source is already drawn at this size
        cache_key = (width, height)
        if (
            self._preview_display_key == cache_key
            and self._preview_display_source is source
            and self.app_state.current_preview_image is not None
        ):
            return

        display_image = source.copy()
        display_image.thumbnail((width, height))
        new_ctk_image = ctk.CTkImage(
            light_image=display_image,
            dark_image=display_image,
            size=display_image.size,
        )
        self.app_state.current_preview_image = new_ctk_image
        self._preview_display_key = cache_key
        self._preview_display_source = source
        self.preview_image_label.configure(image=new_ctk_image)
        self.preview_image_label.configure(text="")

    def reset_preview_display(self) -> None:
        """Clear the preview label and its display cache (used on render errors / empty state)."""
        self._preview_display_key = None
        self._preview_display_source = None
        self.preview_image_label.configure(image=None)
        if hasattr(self.preview_image_label, "_label"):
            try:
                self.preview_image_label._label.configure(image="")
            except Exception:  # noqa: BLE001
                pass
        self.app_state.current_preview_image = None

    def refresh_preview_image(self) -> None:
        if self.controller.view and self.controller.view is not self:
            self.controller.view.refresh_preview_image()

    def has_pending_form_changes(self) -> bool:
        if not self.app_state.records:
            return False
        if self.app_state.selected_record_index >= len(self.app_state.records):
            return False
        current = self.app_state.records[self.app_state.selected_record_index]
        try:
            form_record = self.controller._collect_form_record(row_number=current.row_number)
        except Exception:  # noqa: BLE001
            return False
        return (
            form_record.item_code != current.item_code or form_record.item_name != current.item_name
            or form_record.carton_qty != current.carton_qty or form_record.total_qty != current.total_qty
            or form_record.po != current.po or form_record.po_detail != current.po_detail
            or form_record.po_sub != current.po_sub or form_record.box != current.box
            or form_record.rev != current.rev or form_record.lot != current.lot
            or form_record.cav_no != current.cav_no
        )

    def auto_commit_form(self) -> bool:
        if not self.has_pending_form_changes():
            return False
        try:
            row_number = self.app_state.records[self.app_state.selected_record_index].row_number
            record = self.controller._collect_form_record(row_number=row_number)
        except Exception:  # noqa: BLE001
            return False
        self.app_state.records[self.app_state.selected_record_index] = record
        self.set_records(select_index=self.app_state.selected_record_index)
        return True

    # --- TUTORIAL ACCESSOR METHODS ---

    def get_form_frame(self) -> Optional[ctk.CTkFrame]:
        """Returns the manual entry form container frame."""
        return getattr(self, "form_frame", None)

    def get_auto_po_widget(self) -> Optional[ctk.CTkEntry]:
        """Returns the auto-generated PO number entry widget."""
        return getattr(self, "po_entry", None)

    def get_po_detail_widget(self) -> Optional[ctk.CTkEntry]:
        """Returns the PO detail entry widget."""
        return getattr(self, "po_detail_entry", None)

    def get_po_sub_widget(self) -> Optional[ctk.CTkEntry]:
        """Returns the PO sub entry widget."""
        return getattr(self, "po_sub_entry", None)

    def get_add_button_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '➕ Thêm mới' primary action button widget."""
        return getattr(self, "btn_add_record", None)

    def get_update_button_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '💾 Cập nhật dòng' button widget."""
        return getattr(self, "btn_update_record", None)

    def get_delete_button_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '🗑️ Xóa dòng' button widget."""
        return getattr(self, "btn_delete_record", None)

    def get_clear_all_button_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '🗑️ Xóa tất cả' button widget on the table header."""
        return getattr(self, "btn_clear_all_records", None)

    def get_treeview_widget(self) -> Optional[ttk.Treeview]:
        """Returns the Treeview table widget."""
        return getattr(self, "preview_tree", None)

    def get_table_frame(self) -> Optional[ctk.CTkFrame]:
        """Returns the table container frame."""
        return getattr(self, "table_frame", None)

    def get_preview_frame(self) -> Optional[ctk.CTkFrame]:
        """Returns the preview container frame on the right panel."""
        return getattr(self, "preview_frame", None)

    def get_preview_image_label(self) -> Optional[ctk.CTkLabel]:
        """Returns the label displaying the slip preview image."""
        return getattr(self, "preview_image_label", None)

    def get_qr_payload_box(self) -> Optional[ctk.CTkTextbox]:
        """Returns the textbox displaying the QR code payload."""
        return getattr(self, "qr_payload_box", None)

    def get_refresh_preview_button(self) -> Optional[ctk.CTkButton]:
        """Returns the '🔄 Làm mới xem trước' button widget."""
        return getattr(self, "btn_refresh_preview", None)

    # --- COMPATIBILITY PROPERTY ALIASES ---

    @property
    def add_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_add_button_widget()

    @property
    def update_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_update_button_widget()

    @property
    def delete_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_delete_button_widget()
