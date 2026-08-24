from collections import Counter
from tkinter import ttk
from typing import Optional

import customtkinter as ctk

from core.po_registry import FIXED_PO_DETAIL, FIXED_PO_SUB
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

        self.btn_qr_scan = ctk.CTkButton(
            right_header,
            text="📷 Quét QR",
            height=26,
            width=90,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="white",
            command=self.controller.open_qr_scan_dialog,
        )
        self.btn_qr_scan.pack(side="right", padx=(8, 0))

        ctk.CTkLabel(
            right_header,
            text="(*) Bắt buộc · Tổng SL = SL thùng x Box",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=300,
        ).pack(side="right")

        # Hàng 1: Mã hàng (*) | Tên hàng (*)
        self._form_field(form_frame, 1, 0, "Mã hàng (*):", self.app_state.item_code_var)
        self._form_field(form_frame, 1, 2, "Tên hàng (*):", self.app_state.item_name_var)

        # Hàng 2: SL thùng (*) | Tổng số lượng (tự tính)
        self._form_field(form_frame, 2, 0, "SL thùng (*):", self.app_state.carton_qty_var)
        self.total_qty_entry = self._form_field(
            form_frame, 2, 2, "Tổng SL (tự tính):", self.app_state.total_qty_var, is_readonly=True
        )

        # Hàng 3: Số box (*) | Rev (*)
        self._form_field(form_frame, 3, 0, "Số box (*):", self.app_state.box_var)
        self._form_field(form_frame, 3, 2, "Rev (*) (01–99):", self.app_state.rev_var)

        # Hàng 4: PO (tự sinh) | PO chi tiết & PO phụ (tự sinh)
        self.po_entry = self._form_field(
            form_frame, 4, 0, "PO (tự sinh):", self.app_state.po_var, is_disabled=True
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

        # Hàng 5: Ngày/Lot
        self.lot_entry = self._form_field(
            form_frame, 5, 0, "Ngày/Lot:", self.app_state.lot_var, is_readonly=True
        )
        self.lot_entry.bind("<Button-1>", self.controller.warn_lot_field_locked)

        ctk.CTkLabel(
            form_frame,
            text="(Để trống = 10 dấu cách trong QR)",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=260,
        ).grid(row=5, column=2, columnspan=2, sticky="w", padx=(6, 12), pady=2)

        # Hàng 6: Nút thao tác chính (Primary Actions - Hàng 1)
        btn_bar_1 = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_bar_1.grid(row=6, column=0, columnspan=4, sticky="ew", padx=10, pady=(6, 2))
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

        # Hàng 7: Nút tiện ích phụ (Secondary Utilities - Hàng 2)
        btn_bar_2 = ctk.CTkFrame(form_frame, fg_color="transparent")
        btn_bar_2.grid(row=7, column=0, columnspan=4, sticky="ew", padx=10, pady=(2, 8))
        btn_bar_2.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_bar_2, text="Lot = 10 space", height=28, font=ctk.CTkFont(size=11),
            fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("gray70", "gray40"),
            command=self.controller.fill_lot_spaces
        ).grid(row=0, column=0, sticky="ew", padx=3)

        ctk.CTkButton(
            btn_bar_2, text="📋 Điền mẫu", height=28, font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1, border_color=("gray70", "gray40"),
            text_color=("gray30", "gray70"), hover_color=("gray90", "gray20"), command=self.controller.fill_sample_data
        ).grid(row=0, column=1, sticky="ew", padx=3)

        ctk.CTkButton(
            btn_bar_2, text="🧹 Xóa form", height=28, font=ctk.CTkFont(size=11),
            fg_color="transparent", text_color=("gray40", "gray60"), hover_color=("gray85", "gray25"), command=self.clear_form
        ).grid(row=0, column=2, sticky="ew", padx=3)

        # --- 2. BẢNG DỮ LIỆU (TREEVIEW - CHIẾM TOÀN BỘ KHÔNG GIAN CÒN LẠI) ---
        self.table_frame = ctk.CTkFrame(left_panel, corner_radius=12)
        table_frame = self.table_frame
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"))

        columns = ("row", "item_code", "item_name", "carton_qty", "total_qty", "qty_display", "po", "po_detail", "po_sub", "box", "rev", "lot")
        self.preview_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)
        headings = {
            "row": "Dòng", "item_code": "Mã hàng", "item_name": "Tên hàng", "carton_qty": "SL thùng",
            "total_qty": "Tổng SL", "qty_display": "Tem hiển thị", "po": "PO", "po_detail": "PO chi tiết",
            "po_sub": "PO phụ", "box": "Box", "rev": "Rev", "lot": "Ngày/Lot",
        }
        widths = {
            "row": 50, "item_code": 115, "item_name": 190, "carton_qty": 75, "total_qty": 75,
            "qty_display": 95, "po": 100, "po_detail": 90, "po_sub": 80, "box": 75, "rev": 55, "lot": 120,
        }
        for key in columns:
            self.preview_tree.heading(key, text=headings[key])
            self.preview_tree.column(key, width=widths[key], anchor="w")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.preview_tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.preview_tree.xview)
        self.preview_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.preview_tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        tree_scroll_y.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=(10, 0))
        tree_scroll_x.grid(row=1, column=0, sticky="ew", padx=(10, 10), pady=(0, 10))
        self.preview_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)

        # Highlight duplicate rows in red (Requirement R2)
        self.preview_tree.tag_configure("duplicate", background="#FEE2E2", foreground="#991B1B")

        # ==========================================
        # PANEL PHẢI: XEM TRƯỚC TRANG IN & MÃ QR
        # ==========================================
        self.preview_frame = ctk.CTkFrame(self, corner_radius=12)
        preview_frame = self.preview_frame
        preview_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(preview_frame, text="🔍 Xem trước trang in", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=14, pady=(10, 6)
        )

        self.preview_image_label = ctk.CTkLabel(
            preview_frame, text="Chưa có dữ liệu để xem trước", font=ctk.CTkFont(size=13), text_color="gray50"
        )
        self.preview_image_label.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self.preview_image_label.bind("<Configure>", lambda e: self._on_preview_resize())

        ctk.CTkLabel(preview_frame, text="Chuỗi QR của dòng đang chọn:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, sticky="w", padx=14, pady=(0, 4)
        )
        self.qr_payload_box = ctk.CTkTextbox(preview_frame, height=65, font=ctk.CTkFont(family="Consolas", size=11))
        self.qr_payload_box.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        self.qr_payload_box.configure(state="disabled")

        self.btn_refresh_preview = ctk.CTkButton(
            preview_frame, text="🔄 Làm mới xem trước", height=32,
            fg_color=("gray85", "gray25"), text_color=("gray10", "gray90"), hover_color=("gray75", "gray35"),
            command=self.refresh_preview_image
        )
        self.btn_refresh_preview.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))

        # Init state listeners
        self.app_state.carton_qty_var.trace_add("write", self.controller.sync_total_qty)
        self.app_state.box_var.trace_add("write", self.controller.sync_total_qty)

    def _form_field(
        self, parent: ctk.CTkFrame, row: int, column: int, label: str, variable: ctk.StringVar,
        is_readonly: bool = False, is_disabled: bool = False
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
        return entry

    def set_records(self, select_index: int | None = None) -> None:
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
                record.box, record.rev, lot
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

        if self.app_state.records:
            self.app_state.summary_var.set(f"Có {len(self.app_state.records)} dòng hợp lệ")
            self.app_state.status_var.set(f"Đang hiển thị {len(display_records)} dòng. Bấm vào một dòng để chỉnh sửa.")

            if select_index is None:
                select_index = 0
            if select_index < len(display_records):
                self._select_tree_row(select_index)
            else:
                self._select_tree_row(0)
        else:
            self.app_state.summary_var.set("Chưa có dữ liệu")
            self.app_state.status_var.set("Thêm dữ liệu bằng form bên trái hoặc import từ Excel.")
            self.app_state.preview_source_image = None
            self.preview_image_label.configure(text="Chưa có dữ liệu để xem trước", image=None)
            self.set_qr_payload_text("")
            self.app_state.form_mode_var.set("Đang tạo dòng mới")

    def _select_tree_row(self, display_index: int) -> None:
        iid = str(display_index)
        if iid in self.preview_tree.get_children():
            self.preview_tree.selection_set(iid)
            self.preview_tree.focus(iid)
            self.preview_tree.see(iid)
            self._on_tree_selected()

    def _on_tree_selected(self, _event=None) -> None:
        selected = self.preview_tree.selection()
        if not selected:
            return

        display_index = int(selected[0])
        if display_index >= len(self.app_state.preview_index_map):
            return

        self.app_state.selected_record_index = self.app_state.preview_index_map[display_index]
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
        self.app_state.form_mode_var.set(f"Đang sửa dòng {record.row_number}")

        self.set_qr_payload_text(record.qr_payload)

        # We need the controller to update the preview image since it requires engine logic
        if self.controller.view:
            self.controller.view.refresh_preview_image()

    def clear_form(self) -> None:
        for variable in (
            self.app_state.item_code_var, self.app_state.item_name_var, self.app_state.carton_qty_var,
            self.app_state.total_qty_var, self.app_state.po_var, self.app_state.po_detail_var,
            self.app_state.po_sub_var, self.app_state.box_var, self.app_state.rev_var, self.app_state.lot_var,
        ):
            variable.set("")
        self.app_state.rev_var.set("01")
        self.app_state.form_mode_var.set("Đang tạo dòng mới")

    def set_qr_payload_text(self, payload: str) -> None:
        self.qr_payload_box.configure(state="normal")
        self.qr_payload_box.delete("1.0", "end")
        self.qr_payload_box.insert("1.0", payload)
        self.qr_payload_box.configure(state="disabled")

    def _on_preview_resize(self) -> None:
        if self.controller.view:
            self.controller.view.update_preview_display()

    def update_preview_display(self) -> None:
        if self.app_state.preview_source_image is None:
            return

        width = max(self.preview_image_label.winfo_width() - 16, 120)
        height = max(self.preview_image_label.winfo_height() - 16, 120)
        if width <= 0 or height <= 0:
            return

        display_image = self.app_state.preview_source_image.copy()
        display_image.thumbnail((width, height))
        self.app_state.current_preview_image = ctk.CTkImage(
            light_image=display_image,
            dark_image=display_image,
            size=display_image.size,
        )
        self.preview_image_label.configure(text="", image=self.app_state.current_preview_image)

    def refresh_preview_image(self) -> None:
        if self.controller.view:
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

    def get_qr_button_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '📷 Quét QR' button widget in the form header."""
        return getattr(self, "btn_qr_scan", None)

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
    def qr_scan_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_qr_button_widget()

    @property
    def add_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_add_button_widget()

    @property
    def update_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_update_button_widget()

    @property
    def delete_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_delete_button_widget()
