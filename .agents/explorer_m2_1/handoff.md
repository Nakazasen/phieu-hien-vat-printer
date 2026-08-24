# Milestone 2 Investigation Report: SidebarPanel Widget Hierarchy & Accessor Methods

**Author:** `explorer_m2_1` (teamwork_preview_explorer)  
**Working Directory:** `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m2_1`  
**Date:** 2026-08-19  

---

## 1. Observation

Direct observations from source code inspection:

### 1.1 `ui/main_window.py` (Lines 88–92)
`SidebarPanel` is embedded inside a `ttk.Panedwindow` on the left pane:
```python
sidebar_host = ctk.CTkFrame(self.splitter, corner_radius=14, fg_color=("gray94", "gray14"))
sidebar_host.grid_rowconfigure(0, weight=1)
sidebar_host.grid_columnconfigure(0, weight=1)
self.sidebar = SidebarPanel(sidebar_host, self.controller, corner_radius=14, fg_color=("gray94", "gray14"))
self.sidebar.grid(row=0, column=0, sticky="nsew")
```

### 1.2 `ui/components/sidebar.py` (Lines 6–102)
`SidebarPanel` inherits from `ctk.CTkScrollableFrame`. Analysis of its internal widget hierarchy:

1. **Step 1: Excel File Path & Import Button**
   - **Path Field** (`sidebar.py:34`, `sidebar.py:85-98`):
     ```python
     self._path_field(2, "File Excel (nếu import)", self.app_state.excel_var, self.controller.pick_excel_file)
     ```
     Inside `_path_field`:
     ```python
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
     ```
     *Current state:* `field_row`, `CTkEntry`, and `CTkButton` ("Chọn") are local variables. None are stored as instance attributes on `self`.
   - **"Import từ Excel" Button** (`sidebar.py:45-52`):
     ```python
     ctk.CTkButton(
         self, text="Import từ Excel", 
         command=self.controller.import_from_excel, 
         height=40, 
         fg_color=("gray85", "gray25"), 
         text_color=("gray10", "gray90"),
         hover_color=("gray75", "gray35")
     ).grid(row=12, column=0, sticky="ew", padx=24, pady=(20, 6))
     ```
     *Current state:* Created anonymously at row 12; not assigned to `self`.

2. **Step 2: QR Scanner Trigger Button** (`sidebar.py:54-62`)
   ```python
   ctk.CTkButton(
       self, text="⚡ Quét QR (Phân tách · Hoàn kho)",
       command=self.controller.open_qr_scan_dialog,
       height=40,
       font=ctk.CTkFont(size=13, weight="bold"),
       fg_color="#2563EB",
       hover_color="#1D4ED8",
       text_color="white",
   ).grid(row=13, column=0, sticky="ew", padx=24, pady=(0, 8))
   ```
   *Current state:* Created anonymously at row 13; not assigned to `self`.

3. **Step 4: Generate PDF & Open PDF Buttons**
   - **"Tạo PDF" Button** (`sidebar.py:64-74`):
     ```python
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
     ```
     *Current state:* Stored as `self.generate_button` at row 14 (and referenced by `set_generate_button_state` at line 100).
   - **"Mở PDF vừa tạo" Button** (`sidebar.py:76-83`):
     ```python
     ctk.CTkButton(
         self, text="Mở PDF vừa tạo", 
         command=self.controller.open_generated_pdf,
         fg_color="transparent",
         text_color=("gray40", "gray60"),
         hover_color=("gray85", "gray25"),
         height=36
     ).grid(row=15, column=0, sticky="ew", padx=24, pady=(0, 24))
     ```
     *Current state:* Created anonymously at row 15; not assigned to `self`.

### 1.3 `ui/components/tutorial_overlay.py` Integration Expectations
- `TutorialStep` contract requires `target_widget_getter: Callable[[], Optional[tk.Widget | ctk.CTkBaseClass]]`.
- `GeometryHelper.get_relative_bounds(root, widget, pad)` retrieves `actual_widget = getattr(widget, "_canvas", widget)`, queries `winfo_rootx()` and `winfo_rooty()`, and computes pixel-exact bounding boxes relative to `master_window`.
- `PlacementEngine.calculate()` with `preferred_position="right"` (or `"auto"`) places the `TooltipCard` to the right of the sidebar in the main workspace with zero overlap.

---

## 2. Logic Chain

1. **Current Widget Accessibility Gap**:
   - Because only `self.generate_button` is an instance attribute, any lambda getter attempting `lambda: app.sidebar.btn_import_excel` or `lambda: app.sidebar.qr_scan_btn` currently raises an `AttributeError` unless defensive `getattr(..., None)` is used.
   - For `InteractiveTutorialOverlay` to highlight Step 1 ("Import từ Excel") and Step 2 ("Quét QR") on the sidebar, these widgets must be assigned to persistent instance attributes and exposed via clean accessors.

2. **Scrollable Frame & Absolute Screen Coordinates**:
   - `SidebarPanel` is a `CTkScrollableFrame`. When widgets are placed inside `self`, CustomTkinter attaches them to an internal canvas.
   - However, `GeometryHelper.get_relative_bounds` invokes `.winfo_rootx()` and `.winfo_rooty()` on the underlying `tk.Canvas` (`widget._canvas`).
   - `.winfo_rootx()` evaluates absolute OS desktop coordinates, which naturally factors in scroll offsets, panedwindow splitter position, and padding.
   - Subtracting `root.winfo_rootx()` produces the exact relative coordinate on `SlipPrinterApp` root window.
   - Therefore, passing any named `ctk.CTkButton`, `ctk.CTkEntry`, or `ctk.CTkFrame` from `SidebarPanel` directly into `TutorialStep.target_widget_getter` is 100% mathematically and graphically sound.

3. **Dual API Contract (Attributes + Accessor Methods)**:
   - To support both direct attribute access (`sidebar.excel_import_btn`, `sidebar.qr_scan_btn`, `sidebar.generate_button`, `sidebar.open_pdf_btn`) and explicit method getters (`sidebar.get_excel_import_widget()`, `sidebar.get_qr_scan_widget()`, `sidebar.get_generate_pdf_widget()`, `sidebar.get_open_pdf_widget()`), `SidebarPanel` should provide both.
   - This ensures full compatibility with `spec_miner_m2_1`'s `build_tutorial_steps(app)`, unit tests in `tests/test_tutorial_overlay_e2e.py`, and future refactoring.

---

## 3. Caveats

- **Sidebar Scroll State**: If the sidebar content is scrolled far down such that a widget is moved outside the visible scroll port, `GeometryHelper.get_relative_bounds` clamps bounds to `[0, root_h]`. If the widget is completely unmapped or clipped, `GeometryHelper` returns `None`, and `InteractiveTutorialOverlay` safely falls back to centered modal display without error.
- **Header QR Button vs. Sidebar QR Button**: Step 2 can highlight either the Sidebar QR button (`sidebar.qr_scan_btn`) or the DataTab header QR button (`data_tab.qr_scan_btn`). Providing `sidebar.get_qr_scan_widget()` ensures both options are cleanly available.

---

## 4. Conclusion & Recommendations

### 4.1 Summary of Widget Mapping in `SidebarPanel`
| Step | Functionality | Current Attribute | Recommended Attribute | Recommended Accessor Method | Alias Properties |
|---|---|---|---|---|---|
| **Step 1** | Import từ Excel | *None (anonymous)* | `self.excel_import_button` | `get_excel_import_widget()` | `excel_import_btn`, `btn_import_excel` |
| **Step 1** | File Excel (Field) | *None (anonymous)* | `self.excel_entry`, `self.excel_frame` | `get_excel_path_widget()` | `excel_path_entry` |
| **Step 2** | Quét QR | *None (anonymous)* | `self.qr_scan_button` | `get_qr_scan_widget()` | `qr_scan_btn`, `btn_qr_scan` |
| **Step 4** | Tạo PDF | `self.generate_button` | `self.generate_button` | `get_generate_pdf_widget()` | `btn_generate_pdf` |
| **Step 4** | Mở PDF vừa tạo | *None (anonymous)* | `self.open_pdf_button` | `get_open_pdf_widget()` | `open_pdf_btn`, `btn_open_pdf` |

---

### 4.2 Concrete Implementation Proposal for `ui/components/sidebar.py`

```python
# Proposed modifications in ui/components/sidebar.py:

class SidebarPanel(ctk.CTkScrollableFrame):
    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Header titles ... (rows 0-2 unchanged)

        # Path fields with attribute storage
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

        # Step 1: Import Excel Button
        self.excel_import_button = ctk.CTkButton(
            self, text="Import từ Excel", 
            command=self.controller.import_from_excel, 
            height=40, 
            fg_color=("gray85", "gray25"), 
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray35")
        )
        self.excel_import_button.grid(row=12, column=0, sticky="ew", padx=24, pady=(20, 6))

        # Step 2: QR Scan Button
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

        # Step 4: Generate PDF Button
        self.generate_button = ctk.CTkButton(
            self,
            text="Tạo PDF",
            height=48,
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.controller.start_generation,
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white"
        )
        self.generate_button.grid(row=14, column=0, sticky="ew", padx=24, pady=(8, 8))
        
        # Step 4: Open Generated PDF Button
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
```

---

## 5. Verification Method

To independently verify these findings:
1. **Inspect `ui/components/sidebar.py`**:
   Check line numbers 34, 45-52, 54-62, 64-74, 76-83 against the analysis in Section 1.
2. **Verify Interface Compatibility**:
   Ensure `build_tutorial_steps(app)` in `spec_miner_m2_1/handoff.md` resolves `_get_excel_target()`, `_get_qr_target()`, and `_get_pdf_target()` cleanly against the proposed accessors.
3. **Execute Unit and E2E Tests once implemented**:
   ```powershell
   pytest tests/test_tutorial_overlay.py tests/test_tutorial_overlay_e2e.py -v
   ```
