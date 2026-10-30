from typing import Optional

import customtkinter as ctk

from ui.app_controller import APP_TITLE, AppController


class SidebarPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text=APP_TITLE, font=ctk.CTkFont(size=28, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=24, pady=(24, 2)
        )
        ctk.CTkLabel(
            self,
            text="Phát triển: Bùi Đức Vinh · Phòng PTHT Chế tạo",
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, sticky="w", padx=24, pady=(0, 4))
        ctk.CTkLabel(
            self,
            text="Chọn tệp Excel để nhập dữ liệu hoặc nhập trực tiếp, kiểm tra rồi tạo PDF.",
            wraplength=270,
            justify="left",
            font=ctk.CTkFont(size=14),
            text_color=("gray30", "gray70"),
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(4, 16))

        # --- CARD 1: KHỔ GIẤY IN (A4 / LETTER) ---
        self.card_paper = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray18"))
        self.card_paper.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.card_paper.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.card_paper, text="📄 Khổ giấy in", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 6)
        )
        self.paper_size_seg = ctk.CTkSegmentedButton(
            self.card_paper,
            values=["A4 (6 tem)", "Letter (4 tem)"],
            command=self._on_paper_size_changed,
            height=38,
            font=ctk.CTkFont(size=13, weight="bold"),
            selected_color="#10B981",
            selected_hover_color="#059669",
        )
        self.paper_size_seg.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 4))
        initial_val = "Letter (4 tem)" if self.app_state.paper_size_var.get() == "Letter" else "A4 (6 tem)"
        self.paper_size_seg.set(initial_val)

        ctk.CTkLabel(
            self.card_paper,
            text="A4: 6 tem (2×3) · Letter: 4 tem (2×2)",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray50"),
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 12))

        # --- CARD 2: DỮ LIỆU & XUẤT BẢN ---
        self.card_data = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray18"))
        self.card_data.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))
        self.card_data.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.card_data, text="📦 Dữ liệu & Tạo PDF", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 6)
        )

        self.excel_frame, self.excel_entry, self.excel_browse_btn = self._path_field(
            self.card_data, 1, 2, "Tệp Excel (nếu nhập)", self.app_state.excel_var, self.controller.pick_excel_file
        )

        self.excel_import_button = ctk.CTkButton(
            self.card_data, text="Nhập từ Excel",
            command=self.controller.import_from_excel,
            height=40,
            fg_color=("gray85", "gray25"),
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray35")
        )
        self.excel_import_button.grid(row=3, column=0, sticky="ew", padx=16, pady=(8, 6))

        self.generate_button = ctk.CTkButton(
            self.card_data,
            text="Tạo PDF",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.controller.start_generation,
            fg_color="#10B981",  # Emerald Green (Von Restorff Effect)
            hover_color="#059669",
            text_color="white"
        )
        self.generate_button.grid(row=4, column=0, sticky="ew", padx=16, pady=(6, 4))

        # Viền đậm + chữ đậm để người dùng nhận ra nút mở PDF
        self.open_pdf_button = ctk.CTkButton(
            self.card_data, text="Mở PDF vừa tạo",
            command=self.controller.open_generated_pdf,
            fg_color="transparent",
            border_width=2,
            border_color=("#6B7280", "#9CA3AF"),
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            height=36,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.open_pdf_button.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 14))

        # --- CARD 3: CẤU HÌNH ĐẦU RA ---
        self.card_output = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray18"))
        self.card_output.grid(row=5, column=0, sticky="ew", padx=16, pady=(0, 16))
        self.card_output.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.card_output, text="⚙️ Cấu hình đầu ra", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(12, 6)
        )

        self.template_frame, self.template_entry, self.template_browse_btn = self._path_field(
            self.card_output, 1, 2, "Tệp PDF mẫu", self.app_state.template_var, self.controller.pick_template_pdf
        )
        self.output_dir_frame, self.output_dir_entry, self.output_dir_browse_btn = self._path_field(
            self.card_output, 3, 4, "Thư mục đầu ra", self.app_state.output_dir_var, self.controller.pick_output_dir
        )

        ctk.CTkLabel(self.card_output, text="Tên tệp đầu ra (tùy chọn)", font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=5, column=0, sticky="w", padx=16, pady=(12, 4)
        )
        self.output_name_entry = ctk.CTkEntry(self.card_output, textvariable=self.app_state.output_name_var, height=38, font=ctk.CTkFont(size=13))
        self.output_name_entry.grid(row=6, column=0, sticky="ew", padx=16, pady=(0, 14))

    def _on_paper_size_changed(self, value: str) -> None:
        target_size = "Letter" if "letter" in value.lower() else "A4"
        self.controller.on_paper_size_changed(target_size)

    def sync_paper_size_ui(self) -> None:
        curr = self.app_state.paper_size_var.get()
        val = "Letter (4 tem)" if curr == "Letter" else "A4 (6 tem)"
        if hasattr(self, "paper_size_seg"):
            self.paper_size_seg.set(val)

    def _path_field(
        self, parent: ctk.CTkFrame, label_row: int, field_row: int, label: str, variable: ctk.StringVar, command
    ) -> tuple[ctk.CTkFrame, ctk.CTkEntry, ctk.CTkButton]:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=label_row, column=0, sticky="w", padx=16, pady=(8, 4)
        )
        field_row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        field_row_frame.grid(row=field_row, column=0, sticky="ew", padx=16)
        field_row_frame.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(field_row_frame, textvariable=variable, height=38, font=ctk.CTkFont(size=13))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        btn = ctk.CTkButton(
            field_row_frame, text="Chọn", width=75, height=38, command=command,
            fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("gray70", "gray40")
        )
        btn.grid(row=0, column=1)
        return (field_row_frame, entry, btn)

    def set_generate_button_state(self, state: str) -> None:
        self.generate_button.configure(state=state)

    # --- TUTORIAL ACCESSOR METHODS ---

    def get_excel_import_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Nhập từ Excel' button widget for tutorial spotlight."""
        return getattr(self, "excel_import_button", None)

    def get_excel_path_widget(self) -> Optional[ctk.CTkEntry]:
        """Returns the Excel file path input field widget."""
        return getattr(self, "excel_entry", None)

    def get_excel_frame_widget(self) -> Optional[ctk.CTkFrame]:
        """Returns the entire Excel file selector row frame."""
        return getattr(self, "excel_frame", None)

    def get_generate_pdf_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Tạo PDF' button widget."""
        return getattr(self, "generate_button", None)

    def get_open_pdf_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Mở PDF vừa tạo' button widget."""
        return getattr(self, "open_pdf_button", None)

    def get_paper_size_widget(self) -> Optional[ctk.CTkSegmentedButton]:
        """Returns the paper size segmented button widget."""
        return getattr(self, "paper_size_seg", None)

    # --- COMPATIBILITY PROPERTY ALIASES ---

    @property
    def excel_import_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_excel_import_widget()

    @property
    def btn_import_excel(self) -> Optional[ctk.CTkButton]:
        return self.get_excel_import_widget()

    @property
    def btn_generate_pdf(self) -> Optional[ctk.CTkButton]:
        return self.get_generate_pdf_widget()

    @property
    def open_pdf_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_open_pdf_widget()

    @property
    def btn_open_pdf(self) -> Optional[ctk.CTkButton]:
        return self.get_open_pdf_widget()

    @property
    def paper_size_btn(self) -> Optional[ctk.CTkSegmentedButton]:
        return self.get_paper_size_widget()
