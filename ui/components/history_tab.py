from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from ui.app_controller import APP_TITLE, AppController


class HistoryTabPanel(ctk.CTkFrame):
    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. KHU VỰC THẺ THỐNG KÊ (KPI METRICS CARDS)
        kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        kpi_container.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        kpi_container.grid_columnconfigure((0, 1, 2), weight=1)

        self._build_kpi_card(
            kpi_container, 0, "📦 Tổng số mã đã đăng ký", self.app_state.history_total_var, ("gray90", "gray17"), "#3B82F6"
        )
        self._build_kpi_card(
            kpi_container, 1, "📅 Đã tạo trong hôm nay", self.app_state.history_today_var, ("gray90", "gray17"), "#10B981"
        )
        self._build_kpi_card(
            kpi_container, 2, "🔢 Số PO tiếp theo", self.app_state.history_next_po_var, ("gray90", "gray17"), "#F59E0B"
        )

        # 2. THANH TÌM KIẾM & NÚT HÀNH ĐỘNG
        toolbar = ctk.CTkFrame(self, corner_radius=12)
        toolbar.grid(row=1, column=0, sticky="ew", padx=12, pady=6)
        toolbar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(toolbar, text="🔍 Tra cứu:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(16, 8), pady=12
        )
        
        search_entry = ctk.CTkEntry(
            toolbar,
            textvariable=self.app_state.history_search_var,
            placeholder_text="Nhập số PO, ngày tháng (YYYY-MM-DD), PO chi tiết, hoặc số Box để lọc...",
            height=36,
            font=ctk.CTkFont(size=13),
        )
        search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=12)
        search_entry.bind("<Return>", lambda _e: self.refresh_history())

        ctk.CTkButton(
            toolbar,
            text="Tìm kiếm",
            width=90,
            height=36,
            command=self.refresh_history,
            font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=2, padx=4, pady=12)

        ctk.CTkButton(
            toolbar,
            text="🔄 Làm mới",
            width=90,
            height=36,
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray70", "gray40"),
            command=self.clear_and_refresh,
        ).grid(row=0, column=3, padx=4, pady=12)

        ctk.CTkButton(
            toolbar,
            text="📥 Xuất Excel / CSV",
            height=36,
            font=ctk.CTkFont(weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white",
            command=self.export_history,
        ).grid(row=0, column=4, padx=(4, 16), pady=12)

        # 3. BẢNG DỮ LIỆU LỊCH SỬ (TREEVIEW)
        table_frame = ctk.CTkFrame(self, corner_radius=14)
        table_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(6, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("created_at", "po", "po_detail", "po_sub", "box")
        self.history_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=6)
        
        headings = {
            "created_at": "🕒 Thời gian đăng ký",
            "po": "📋 Số PO",
            "po_detail": "PO Chi tiết",
            "po_sub": "PO Phụ",
            "box": "📦 Số Box",
        }
        widths = {
            "created_at": 180,
            "po": 160,
            "po_detail": 120,
            "po_sub": 110,
            "box": 110,
        }

        for col in columns:
            self.history_tree.heading(col, text=headings[col])
            self.history_tree.column(col, width=widths[col], anchor="center" if col != "created_at" else "w")

        tree_scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_tree.yview)
        tree_scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)

        self.history_tree.grid(row=0, column=0, sticky="nsew", padx=(14, 0), pady=(14, 0))
        tree_scroll_y.grid(row=0, column=1, sticky="ns", padx=(0, 14), pady=(14, 0))
        tree_scroll_x.grid(row=1, column=0, sticky="ew", padx=(14, 14), pady=(0, 14))

        # 4. THANH TRẠNG THÁI CUỐI BẢNG
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 10))
        ctk.CTkLabel(
            footer,
            textvariable=self.app_state.history_status_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        ).pack(side="left")

    def _build_kpi_card(
        self, parent: ctk.CTkFrame, col: int, title: str, var: ctk.StringVar, bg_color: tuple[str, str], accent_color: str
    ) -> None:
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=bg_color)
        card.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color=("gray40", "gray70")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(10, 2)
        )
        ctk.CTkLabel(card, textvariable=var, font=ctk.CTkFont(size=22, weight="bold"), text_color=accent_color).grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 10)
        )

    def refresh_history(self) -> None:
        search_query = self.app_state.history_search_var.get().strip()
        try:
            # 1. Cập nhật số liệu thống kê
            stats = self.app_state.po_registry.get_statistics()
            self.app_state.history_total_var.set(f"{stats['total_count']:,} mã")
            self.app_state.history_today_var.set(f"{stats['today_count']:,} mã")
            self.app_state.history_next_po_var.set(stats["next_po"])

            # 2. Xóa và nạp lại bảng dữ liệu
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)

            records = self.app_state.po_registry.fetch_history(search=search_query, limit=500)
            for index, r in enumerate(records):
                self.history_tree.insert(
                    "",
                    "end",
                    iid=str(index),
                    values=(r["created_at"], r["po"], r["po_detail"], r["po_sub"], r["box"]),
                )

            if search_query:
                self.app_state.history_status_var.set(
                    f"Tìm thấy {len(records)} kết quả cho từ khóa '{search_query}' (Giới hạn hiển thị 500 dòng gần nhất)."
                )
            else:
                self.app_state.history_status_var.set(
                    f"Đang hiển thị {len(records)} bản ghi đăng ký gần nhất trong cơ sở dữ liệu."
                )
        except Exception as exc:  # noqa: BLE001
            self.app_state.history_status_var.set(f"Lỗi khi tải lịch sử: {exc}")

    def clear_and_refresh(self) -> None:
        self.app_state.history_search_var.set("")
        self.refresh_history()

    def export_history(self) -> None:
        file_path = filedialog.asksaveasfilename(
            title="Lưu file lịch sử đăng ký EDI",
            defaultextension=".csv",
            filetypes=[("CSV file (mở bằng Excel)", "*.csv"), ("All files", "*.*")],
            initialfile="LichSu_DangKy_EDI.csv",
        )
        if not file_path:
            return

        try:
            search_query = self.app_state.history_search_var.get().strip()
            total_exported = self.app_state.po_registry.export_history_to_csv(file_path, search=search_query)
            messagebox.showinfo(
                APP_TITLE,
                f"Đã xuất thành công {total_exported} bản ghi lịch sử ra file:\n{file_path}\n\nBạn có thể mở file này trực tiếp bằng Microsoft Excel.",
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Lỗi khi xuất file:\n{exc}")
