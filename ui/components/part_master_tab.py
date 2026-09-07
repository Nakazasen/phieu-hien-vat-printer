from __future__ import annotations

from tkinter import messagebox, ttk

import customtkinter as ctk

from ui.app_controller import APP_TITLE, AppController


class PartMasterTabPanel(ctk.CTkFrame):
    """Tab panel for managing Part Master (Master Linh Kiện) data."""

    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. THANH CÔNG CỤ TRÊN CÙNG (TOP TOOLBAR)
        top_bar = ctk.CTkFrame(self, corner_radius=12)
        top_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 6))
        top_bar.grid_columnconfigure(1, weight=1)

        # Tiêu đề & Tổng số lượng linh kiện
        title_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        title_frame.grid(row=0, column=0, padx=(16, 12), pady=10, sticky="w")
        ctk.CTkLabel(
            title_frame,
            text="📋 Danh mục Master Linh Kiện",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).pack(side="left")

        self.count_badge = ctk.CTkLabel(
            title_frame,
            textvariable=self.app_state.master_count_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#3B82F6", "#1D4ED8"),
            text_color="white",
            corner_radius=8,
            padx=10,
            pady=2,
        )
        self.count_badge.pack(side="left", padx=(10, 0))

        # Thanh tìm kiếm nhanh
        search_frame = ctk.CTkFrame(top_bar, fg_color="transparent")
        search_frame.grid(row=0, column=1, sticky="ew", padx=(10, 16), pady=10)
        search_frame.grid_columnconfigure(0, weight=1)

        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.app_state.master_search_var,
            placeholder_text="🔍 Tìm kiếm nhanh theo Mã linh kiện hoặc Tên linh kiện...",
            height=34,
            font=ctk.CTkFont(size=12),
        )
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search_entry.bind("<KeyRelease>", self._on_search_key)
        search_entry.bind("<Return>", lambda _e: self.refresh_table())

        ctk.CTkButton(
            search_frame,
            text="Tìm",
            width=65,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.refresh_table,
        ).grid(row=0, column=1, padx=(0, 4))

        ctk.CTkButton(
            search_frame,
            text="Làm mới",
            width=80,
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color=("gray75", "gray30"),
            hover_color=("gray65", "gray25"),
            text_color=("gray10", "gray90"),
            command=self._clear_search_and_refresh,
        ).grid(row=0, column=2)

        # 2. KHU VỰC CHÍNH (LEFT: FORM NHẬP LIỆU | RIGHT: BẢNG TRA CỨU)
        # Bên trái: Form nhập liệu Master
        left_card = ctk.CTkFrame(self, corner_radius=12, width=340)
        left_card.grid(row=1, column=0, sticky="nsew", padx=(12, 6), pady=(0, 10))
        left_card.grid_propagate(False)
        left_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            left_card,
            text="📝 Thêm / Sửa Linh Kiện Master",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(14, 8))

        # Mã linh kiện
        ctk.CTkLabel(
            left_card,
            text="Mã hàng (*):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=1, column=0, sticky="w", padx=14, pady=6)
        self.entry_item_code = ctk.CTkEntry(
            left_card,
            textvariable=self.app_state.master_item_code_var,
            placeholder_text="Ví dụ: 3V2ND00160",
            height=30,
            font=ctk.CTkFont(size=12),
        )
        self.entry_item_code.grid(row=1, column=1, sticky="ew", padx=(0, 14), pady=6)
        self.entry_item_code.bind("<FocusOut>", self._normalize_code)

        # Tên linh kiện
        ctk.CTkLabel(
            left_card,
            text="Tên hàng (*):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=14, pady=6)
        self.entry_item_name = ctk.CTkEntry(
            left_card,
            textvariable=self.app_state.master_item_name_var,
            placeholder_text="Ví dụ: COVER RIGHT FUSER ASSY",
            height=30,
            font=ctk.CTkFont(size=12),
        )
        self.entry_item_name.grid(row=2, column=1, sticky="ew", padx=(0, 14), pady=6)
        self.entry_item_name.bind("<FocusOut>", self._normalize_name)

        # Rev
        ctk.CTkLabel(
            left_card,
            text="Rev (*) (01–99):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=3, column=0, sticky="w", padx=14, pady=6)
        self.entry_rev = ctk.CTkEntry(
            left_card,
            textvariable=self.app_state.master_rev_var,
            placeholder_text="01",
            height=30,
            width=90,
            font=ctk.CTkFont(size=12),
        )
        self.entry_rev.grid(row=3, column=1, sticky="w", padx=(0, 14), pady=6)

        # Chú thích validation
        ctk.CTkLabel(
            left_card,
            text="(*) Bắt buộc nhập đầy đủ thông tin.\nRev bắt buộc đúng 2 chữ số từ 01 đến 99.",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", padx=14, pady=(2, 10))

        # Nút hành động Form
        btn_box = ctk.CTkFrame(left_card, fg_color="transparent")
        btn_box.grid(row=5, column=0, columnspan=2, sticky="ew", padx=14, pady=6)
        btn_box.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_save = ctk.CTkButton(
            btn_box,
            text="💾 Lưu Master",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white",
            command=self.controller.save_part_master,
        )
        self.btn_save.grid(row=0, column=0, sticky="ew", padx=2)

        self.btn_delete = ctk.CTkButton(
            btn_box,
            text="🗑️ Xóa",
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#EF4444", "#991B1B"),
            hover_color=("#DC2626", "#7F1D1D"),
            text_color="white",
            command=self.controller.delete_part_master,
        )
        self.btn_delete.grid(row=0, column=1, sticky="ew", padx=2)

        self.btn_clear = ctk.CTkButton(
            btn_box,
            text="🧹 Làm mới",
            height=34,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            border_width=1,
            border_color=("gray70", "gray40"),
            text_color=("gray30", "gray70"),
            hover_color=("gray90", "gray20"),
            command=self.controller.clear_part_master_form,
        )
        self.btn_clear.grid(row=0, column=2, sticky="ew", padx=2)

        # Trạng thái thao tác form
        self.status_lbl = ctk.CTkLabel(
            left_card,
            textvariable=self.app_state.master_status_var,
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
            wraplength=310,
            justify="left",
        )
        self.status_lbl.grid(row=6, column=0, columnspan=2, sticky="w", padx=14, pady=(8, 0))

        # Tiện ích nạp từ danh sách hiện tại
        import_box = ctk.CTkFrame(left_card, corner_radius=8, fg_color=("gray90", "gray20"))
        import_box.grid(row=7, column=0, columnspan=2, sticky="ew", padx=14, pady=(16, 10))
        import_box.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            import_box,
            text="💡 Mẹo: Có thể đồng bộ nhanh toàn bộ mã linh kiện từ bảng dữ liệu hiện tại vào Master:",
            font=ctk.CTkFont(size=11),
            text_color=("gray30", "gray70"),
            wraplength=300,
            justify="left",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 4))

        ctk.CTkButton(
            import_box,
            text="📥 Nạp từ bảng in hiện tại vào Master",
            height=28,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#2563EB", "#1D4ED8"),
            hover_color=("#1D4ED8", "#1E40AF"),
            command=self._import_from_active_records,
        ).grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        # Bên phải: Bảng danh sách Master Linh Kiện
        right_card = ctk.CTkFrame(self, corner_radius=12)
        right_card.grid(row=1, column=1, sticky="nsew", padx=(6, 12), pady=(0, 10))
        right_card.grid_columnconfigure(0, weight=1)
        right_card.grid_rowconfigure(0, weight=1)

        columns = ("item_code", "item_name", "rev", "updated_at")
        self.tree = ttk.Treeview(right_card, columns=columns, show="headings")
        self.tree.heading("item_code", text="Mã linh kiện")
        self.tree.heading("item_name", text="Tên linh kiện")
        self.tree.heading("rev", text="Rev")
        self.tree.heading("updated_at", text="Cập nhật lần cuối")

        self.tree.column("item_code", width=150, anchor="w")
        self.tree.column("item_name", width=280, anchor="w")
        self.tree.column("rev", width=65, anchor="center")
        self.tree.column("updated_at", width=150, anchor="center")

        tree_scroll_y = ttk.Scrollbar(right_card, orient="vertical", command=self.tree.yview)
        tree_scroll_x = ttk.Scrollbar(right_card, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.tree.grid(row=0, column=0, sticky="nsew", padx=(10, 0), pady=(10, 0))
        tree_scroll_y.grid(row=0, column=1, sticky="ns", padx=(0, 10), pady=(10, 0))
        tree_scroll_x.grid(row=1, column=0, sticky="ew", padx=(10, 0), pady=(0, 10))

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _normalize_code(self, _event=None) -> None:
        val = self.app_state.master_item_code_var.get().strip().upper()
        self.app_state.master_item_code_var.set(val)

    def _normalize_name(self, _event=None) -> None:
        val = self.app_state.master_item_name_var.get().strip().upper()
        self.app_state.master_item_name_var.set(val)

    def _on_search_key(self, _event=None) -> None:
        if hasattr(self, "_search_job") and self._search_job:
            self.after_cancel(self._search_job)
        self._search_job = self.after(200, self.refresh_table)

    def _clear_search_and_refresh(self) -> None:
        self.app_state.master_search_var.set("")
        self.refresh_table()

    def refresh_table(self) -> None:
        """Query SQLite and reload table entries."""
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not hasattr(self.app_state, "part_master"):
            return

        query = self.app_state.master_search_var.get().strip()
        items = self.app_state.part_master.list_all(query)
        total_count = self.app_state.part_master.count()

        if query:
            self.app_state.master_count_var.set(f"Tìm thấy {len(items)} / {total_count}")
        else:
            self.app_state.master_count_var.set(f"Tổng: {total_count} mã")

        for entry in items:
            self.tree.insert(
                "",
                "end",
                iid=entry.item_code,
                values=(entry.item_code, entry.item_name, entry.rev, entry.updated_at),
            )

    def _on_tree_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        item_code = selected[0]
        entry = self.app_state.part_master.get(item_code)
        if entry:
            self.app_state.master_item_code_var.set(entry.item_code)
            self.app_state.master_item_name_var.set(entry.item_name)
            self.app_state.master_rev_var.set(entry.rev)
            self.app_state.master_status_var.set(f"Đang chọn: {entry.item_code} (Rev {entry.rev})")

    def _on_tree_double_click(self, _event=None) -> None:
        """Double-click to apply to main Data Tab and switch view."""
        selected = self.tree.selection()
        if not selected:
            return
        item_code = selected[0]
        entry = self.app_state.part_master.get(item_code)
        if entry:
            self.app_state.item_code_var.set(entry.item_code)
            self.app_state.item_name_var.set(entry.item_name)
            self.app_state.rev_var.set(entry.rev)
            if hasattr(self.controller, "view") and hasattr(self.controller.view, "notebook"):
                self.controller.view.notebook.select(0)
                if self.controller.view:
                    self.controller.view.append_log(f"Master: Đã chuyển mã {entry.item_code} sang Form in phiếu")

    def _import_from_active_records(self) -> None:
        """Sync valid records currently loaded in the print table to Master."""
        records = getattr(self.app_state, "records", [])
        if not records:
            messagebox.showinfo(APP_TITLE, "Bảng dữ liệu in hiện tại đang trống, không có dòng nào để nạp.")
            return

        added_count = 0
        for r in records:
            code = r.item_code.strip().upper()
            name = r.item_name.strip()
            rev = r.rev.strip()
            if code and name and len(rev) == 2 and rev.isdigit():
                try:
                    self.app_state.part_master.upsert(code, name, rev)
                    added_count += 1
                except Exception:
                    pass

        self.refresh_table()
        messagebox.showinfo(
            APP_TITLE,
            f"Đã đồng bộ thành công {added_count} mã linh kiện từ bảng in vào Master!",
        )
