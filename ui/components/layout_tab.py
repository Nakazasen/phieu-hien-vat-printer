from tkinter import ttk

import customtkinter as ctk

from core.slip_printer_engine import FIELD_LABELS, list_layout_items
from ui.app_controller import AppController


class LayoutTabPanel(ctk.CTkFrame):
    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self.step_size_var = ctk.StringVar(value="5")
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=4, uniform="layout_cols")
        self.grid_columnconfigure(1, weight=6, uniform="layout_cols")
        self.grid_rowconfigure(0, weight=1)

        # --- CỘT TRÁI: DANH SÁCH PHẦN TỬ ---
        list_frame = ctk.CTkFrame(self, corner_radius=12)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        header_left = ctk.CTkFrame(list_frame, fg_color="transparent")
        header_left.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(header_left, text="📋 Danh sách phần tử trên phiếu", font=ctk.CTkFont(size=15, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(
            header_left,
            text="Bấm vào một dòng bên dưới để bắt đầu căn chỉnh vị trí",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, sticky="w", pady=(1, 0))

        columns = ("label", "field", "x", "y")
        self.layout_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=6)
        self.layout_tree.heading("label", text="Vị trí trên phiếu")
        self.layout_tree.heading("field", text="Loại nội dung")
        self.layout_tree.heading("x", text="Cách mép trái (X)")
        self.layout_tree.heading("y", text="Cách mép trên (Y)")
        self.layout_tree.column("label", width=170, anchor="w")
        self.layout_tree.column("field", width=110, anchor="w")
        self.layout_tree.column("x", width=90, anchor="center")
        self.layout_tree.column("y", width=90, anchor="center")
        self.layout_tree.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=(0, 10))

        layout_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.layout_tree.yview)
        layout_scroll.grid(row=1, column=1, sticky="ns", padx=(0, 10), pady=(0, 10))
        self.layout_tree.configure(yscrollcommand=layout_scroll.set)
        self.layout_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)

        # --- CỘT PHẢI: BẢNG ĐIỀU KHIỂN TRỰC QUAN (CUỘN MƯỢT, KHÔNG BỊ KHUẤT NÚT) ---
        editor = ctk.CTkScrollableFrame(self, corner_radius=12)
        editor.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        editor.grid_columnconfigure(0, weight=1)

        # Tiêu đề & Phần tử đang chọn
        header_right = ctk.CTkFrame(editor, fg_color="transparent")
        header_right.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        ctk.CTkLabel(header_right, text="🎮 Bảng điều hướng vị trí", font=ctk.CTkFont(size=16, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )

        active_card = ctk.CTkFrame(editor, corner_radius=8, fg_color=("gray90", "gray20"))
        active_card.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        active_card.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(active_card, text="Đang chọn:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=0, column=0, padx=(10, 4), pady=6)
        self.active_label_display = ctk.CTkLabel(
            active_card, textvariable=self.app_state.layout_label_var, font=ctk.CTkFont(size=13, weight="bold"), text_color="#10B981"
        )
        self.active_label_display.grid(row=0, column=1, sticky="w", padx=(0, 10), pady=6)

        # 1. BƯỚC NHẢY (STEP SELECTOR)
        step_row = ctk.CTkFrame(editor, fg_color="transparent")
        step_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        ctk.CTkLabel(step_row, text="Mức dịch chuyển:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 8))
        for step_val, label in (("1", "1 mm (Tinh chỉnh)"), ("5", "5 mm (Chuẩn)"), ("15", "15 mm (Nhanh)")):
            ctk.CTkRadioButton(
                step_row, text=label, value=step_val, variable=self.step_size_var, font=ctk.CTkFont(size=11)
            ).pack(side="left", padx=6)

        # 2. CỤM NÚT ĐIỀU HƯỚNG D-PAD
        dpad_frame = ctk.CTkFrame(editor, corner_radius=8, fg_color=("gray92", "gray17"))
        dpad_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=(0, 6))
        dpad_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            dpad_frame, text="⬆️ Lên trên", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._nudge(0, -1)
        ).grid(row=0, column=1, padx=4, pady=(6, 2), sticky="ew")

        ctk.CTkButton(
            dpad_frame, text="⬅️ Sang trái", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._nudge(-1, 0)
        ).grid(row=1, column=0, padx=(8, 2), pady=2, sticky="ew")

        ctk.CTkLabel(dpad_frame, text="🎯", font=ctk.CTkFont(size=16)).grid(row=1, column=1, pady=2)

        ctk.CTkButton(
            dpad_frame, text="➡️ Sang phải", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._nudge(1, 0)
        ).grid(row=1, column=2, padx=(2, 8), pady=2, sticky="ew")

        ctk.CTkButton(
            dpad_frame, text="⬇️ Xuống dưới", height=32, font=ctk.CTkFont(size=12, weight="bold"),
            command=lambda: self._nudge(0, 1)
        ).grid(row=2, column=1, padx=4, pady=(2, 6), sticky="ew")

        # 3. CỤM THAY ĐỔI KÍCH THƯỚC (DÀNH CHO QR & Ô IN)
        size_frame = ctk.CTkFrame(editor, corner_radius=8, fg_color=("gray92", "gray17"))
        size_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 6))
        size_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkLabel(size_frame, text="📐 Kích thước:", font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 2)
        )
        ctk.CTkButton(size_frame, text="➕ Rộng hơn", height=28, font=ctk.CTkFont(size=11), command=lambda: self._resize(1, 0)).grid(
            row=1, column=0, padx=(8, 2), pady=(0, 6), sticky="ew"
        )
        ctk.CTkButton(size_frame, text="➖ Hẹp hơn", height=28, font=ctk.CTkFont(size=11), command=lambda: self._resize(-1, 0)).grid(
            row=1, column=1, padx=2, pady=(0, 6), sticky="ew"
        )
        ctk.CTkButton(size_frame, text="➕ Cao hơn", height=28, font=ctk.CTkFont(size=11), command=lambda: self._resize(0, 1)).grid(
            row=1, column=2, padx=2, pady=(0, 6), sticky="ew"
        )
        ctk.CTkButton(size_frame, text="➖ Thấp hơn", height=28, font=ctk.CTkFont(size=11), command=lambda: self._resize(0, -1)).grid(
            row=1, column=3, padx=(2, 8), pady=(0, 6), sticky="ew"
        )

        # 4. CÁC NÚT LƯU & KHÔI PHỤC HÀNH ĐỘNG
        actions_frame = ctk.CTkFrame(editor, fg_color="transparent")
        actions_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=(2, 6))
        actions_frame.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            actions_frame,
            text="💾 Lưu vị trí này",
            height=36,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white",
            command=self.controller.save_layout_config_to_disk,
        ).grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        ctk.CTkButton(
            actions_frame, text="🔄 Hủy chỉnh sửa", height=30, font=ctk.CTkFont(size=11), command=self.controller.reload_layout_config,
            fg_color=("gray75", "gray35"), hover_color=("gray65", "gray45"), text_color=("black", "white")
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=(0, 3))

        ctk.CTkButton(
            actions_frame, text="⚙️ Khôi phục gốc", height=30, font=ctk.CTkFont(size=11), command=self.controller.reset_layout_config,
            fg_color="transparent", border_width=1, border_color=("gray60", "gray40"),
            text_color=("gray30", "gray70"), hover_color=("gray85", "gray25")
        ).grid(row=1, column=2, sticky="ew", padx=(3, 0))

        # Ghi chú hướng dẫn ngắn
        ctk.CTkLabel(
            editor,
            text="💡 Mẹo: Khi bấm các nút điều hướng trên, hình mẫu xem trước bên tab dữ liệu sẽ cập nhật vị trí ngay lập tức.",
            wraplength=320,
            justify="left",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60"),
        ).grid(row=6, column=0, sticky="w", padx=10, pady=(2, 8))

    def _nudge(self, x_dir: int, y_dir: int) -> None:
        try:
            step = float(self.step_size_var.get())
        except ValueError:
            step = 5.0
        self.controller.nudge_layout(x_dir * step, y_dir * step)

    def _resize(self, w_dir: int, h_dir: int) -> None:
        try:
            step = float(self.step_size_var.get())
        except ValueError:
            step = 5.0
        self.controller.resize_layout(w_dir * step, h_dir * step)

    def refresh_tree(self, select_id: str | None = None) -> None:
        for item in self.layout_tree.get_children():
            self.layout_tree.delete(item)

        items = list_layout_items(self.app_state.layout_config)
        for item in items:
            field_label = FIELD_LABELS.get(item["field"], item["field"])
            self.layout_tree.insert(
                "", "end", iid=item["id"], values=(item["label"], field_label, f"{item['x']} pt", f"{item['y']} pt")
            )

        if items:
            target_id = select_id if select_id in [i["id"] for i in items] else items[0]["id"]
            self.layout_tree.selection_set(target_id)
            self.layout_tree.focus(target_id)
            self._load_editor(target_id)

    def _on_tree_selected(self, _event=None) -> None:
        selected = self.layout_tree.selection()
        if selected:
            self._load_editor(selected[0])

    def _load_editor(self, item_id: str) -> None:
        for item in list_layout_items(self.app_state.layout_config):
            if item["id"] == item_id:
                self.app_state.layout_choice_var.set(item_id)
                self.app_state.layout_label_var.set(item["label"])
                self.app_state.layout_field_var.set(FIELD_LABELS.get(item["field"], item["field"]))
                self.app_state.x_var.set(str(item["x"]))
                self.app_state.y_var.set(str(item["y"]))
                self.app_state.width_var.set("" if item["width"] is None else str(item["width"]))
                self.app_state.height_var.set("" if item["height"] is None else str(item["height"]))
                return
