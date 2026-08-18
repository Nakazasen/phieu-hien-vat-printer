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

        self._path_field(2, "File Excel (nếu import)", self.app_state.excel_var, self.controller.pick_excel_file)
        self._path_field(3, "File PDF mẫu", self.app_state.template_var, self.controller.pick_template_pdf)
        self._path_field(4, "Thư mục đầu ra", self.app_state.output_dir_var, self.controller.pick_output_dir)

        ctk.CTkLabel(self, text="Tên file đầu ra (tùy chọn)", font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=10, column=0, sticky="w", padx=24, pady=(16, 8)
        )
        ctk.CTkEntry(self, textvariable=self.app_state.output_name_var, height=40, font=ctk.CTkFont(size=14)).grid(
            row=11, column=0, sticky="ew", padx=24
        )

        ctk.CTkButton(
            self, text="Import từ Excel", 
            command=self.controller.import_from_excel, 
            height=40, 
            fg_color=("gray85", "gray25"), 
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray35")
        ).grid(row=12, column=0, sticky="ew", padx=24, pady=(24, 8))

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
        self.generate_button.grid(row=13, column=0, sticky="ew", padx=24, pady=(8, 8))
        
        ctk.CTkButton(
            self, text="Mở PDF vừa tạo", 
            command=self.controller.open_generated_pdf,
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            hover_color=("gray85", "gray25"),
            height=36
        ).grid(row=14, column=0, sticky="ew", padx=24, pady=(0, 24))

    def _path_field(self, row_group: int, label: str, variable: ctk.StringVar, command) -> None:
        ctk.CTkLabel(self, text=label, font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=row_group * 2, column=0, sticky="w", padx=24, pady=(16, 8)
        )
        field_row = ctk.CTkFrame(self, fg_color="transparent")
        field_row.grid(row=row_group * 2 + 1, column=0, sticky="ew", padx=24)
        field_row.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(field_row, textvariable=variable, height=40, font=ctk.CTkFont(size=13)).grid(
            row=0, column=0, sticky="ew", padx=(0, 12)
        )
        ctk.CTkButton(
            field_row, text="Chọn", width=80, height=40, command=command,
            fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("gray70", "gray40")
        ).grid(row=0, column=1)

    def set_generate_button_state(self, state: str) -> None:
        self.generate_button.configure(state=state)
