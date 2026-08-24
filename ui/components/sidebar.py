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
            text="Chọn Excel để import hoặc nhập trực tiếp, kiểm tra dữ liệu rồi tạo PDF.",
            wraplength=270,
            justify="left",
            font=ctk.CTkFont(size=14),
            text_color=("gray30", "gray70"),
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(4, 24))

        self.excel_frame, self.excel_entry, self.excel_browse_btn = self._path_field(
            2, "File Excel (nếu import)", self.app_state.excel_var, self.controller.pick_excel_file
        )
        self.template_frame, self.template_entry, self.template_browse_btn = self._path_field(
            3, "File PDF mẫu", self.app_state.template_var, self.controller.pick_template_pdf
        )
        self.output_dir_frame, self.output_dir_entry, self.output_dir_browse_btn = self._path_field(
            4, "Thư mục đầu ra", self.app_state.output_dir_var, self.controller.pick_output_dir
        )

        ctk.CTkLabel(self, text="Tên file đầu ra (tùy chọn)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=10, column=0, sticky="w", padx=24, pady=(16, 8)
        )
        self.output_name_entry = ctk.CTkEntry(self, textvariable=self.app_state.output_name_var, height=40, font=ctk.CTkFont(size=14))
        self.output_name_entry.grid(row=11, column=0, sticky="ew", padx=24)

        self.excel_import_button = ctk.CTkButton(
            self, text="Import từ Excel", 
            command=self.controller.import_from_excel, 
            height=40, 
            fg_color=("gray85", "gray25"), 
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray35")
        )
        self.excel_import_button.grid(row=12, column=0, sticky="ew", padx=24, pady=(20, 6))

        self.qr_scan_button = ctk.CTkButton(
            self, text="⚡ Quét QR (Phân tách · Hoàn kho)",
            command=self.controller.open_qr_scan_dialog,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="white",
        )
        self.qr_scan_button.grid(row=13, column=0, sticky="ew", padx=24, pady=(0, 8))

        self.generate_button = ctk.CTkButton(
            self,
            text="Tạo PDF",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.controller.start_generation,
            fg_color="#10B981",  # Emerald Green (Von Restorff Effect)
            hover_color="#059669",
            text_color="white"
        )
        self.generate_button.grid(row=14, column=0, sticky="ew", padx=24, pady=(8, 8))
        
        self.open_pdf_button = ctk.CTkButton(
            self, text="Mở PDF vừa tạo", 
            command=self.controller.open_generated_pdf,
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            hover_color=("gray85", "gray25"),
            height=36
        )
        self.open_pdf_button.grid(row=15, column=0, sticky="ew", padx=24, pady=(0, 24))

    def _path_field(self, row_group: int, label: str, variable: ctk.StringVar, command) -> tuple[ctk.CTkFrame, ctk.CTkEntry, ctk.CTkButton]:
        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_group * 2, column=0, sticky="w", padx=24, pady=(16, 8)
        )
        field_row = ctk.CTkFrame(self, fg_color="transparent")
        field_row.grid(row=row_group * 2 + 1, column=0, sticky="ew", padx=24)
        field_row.grid_columnconfigure(0, weight=1)
        entry = ctk.CTkEntry(field_row, textvariable=variable, height=40, font=ctk.CTkFont(size=13))
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        btn = ctk.CTkButton(
            field_row, text="Chọn", width=80, height=40, command=command,
            fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("gray70", "gray40")
        )
        btn.grid(row=0, column=1)
        return (field_row, entry, btn)

    def set_generate_button_state(self, state: str) -> None:
        self.generate_button.configure(state=state)

    # --- TUTORIAL ACCESSOR METHODS ---

    def get_excel_import_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Import từ Excel' button widget for tutorial spotlight."""
        return getattr(self, "excel_import_button", None)

    def get_excel_path_widget(self) -> Optional[ctk.CTkEntry]:
        """Returns the Excel file path input field widget."""
        return getattr(self, "excel_entry", None)

    def get_excel_frame_widget(self) -> Optional[ctk.CTkFrame]:
        """Returns the entire Excel file selector row frame."""
        return getattr(self, "excel_frame", None)

    def get_qr_scan_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the '⚡ Quét QR' button widget on the sidebar."""
        return getattr(self, "qr_scan_button", None)

    def get_generate_pdf_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Tạo PDF' button widget."""
        return getattr(self, "generate_button", None)

    def get_open_pdf_widget(self) -> Optional[ctk.CTkButton]:
        """Returns the 'Mở PDF vừa tạo' button widget."""
        return getattr(self, "open_pdf_button", None)

    # --- COMPATIBILITY PROPERTY ALIASES ---

    @property
    def excel_import_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_excel_import_widget()

    @property
    def btn_import_excel(self) -> Optional[ctk.CTkButton]:
        return self.get_excel_import_widget()

    @property
    def qr_scan_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_qr_scan_widget()

    @property
    def btn_qr_scan(self) -> Optional[ctk.CTkButton]:
        return self.get_qr_scan_widget()

    @property
    def btn_generate_pdf(self) -> Optional[ctk.CTkButton]:
        return self.get_generate_pdf_widget()

    @property
    def open_pdf_btn(self) -> Optional[ctk.CTkButton]:
        return self.get_open_pdf_widget()

    @property
    def btn_open_pdf(self) -> Optional[ctk.CTkButton]:
        return self.get_open_pdf_widget()
