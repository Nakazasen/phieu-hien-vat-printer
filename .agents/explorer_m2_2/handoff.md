# Handoff Report: DataTabPanel Widget Hierarchy & Tab Switching (Milestone 2)

## 1. Observation

### 1.1 Direct Inspection of `ui/components/data_tab.py`
In `DataTabPanel._build()` (`ui/components/data_tab.py:17-238`), the grid layout is configured with 2 top-level columns:
- Column 0 (weight=68): `self.left_panel = ctk.CTkFrame(self, fg_color="transparent")` (lines 25-30)
- Column 1 (weight=32): `self.preview_frame = ctk.CTkFrame(self, corner_radius=12)` (lines 206-210)

Inside `self.left_panel`:
- **Row 0: Form Frame (`self.form_frame`)**:
  - `self.form_frame = ctk.CTkFrame(left_panel, corner_radius=12)` (line 33)
  - `header_row` (line 40): contains `CTkLabel` for `form_mode_var` (line 44) and `right_header` (line 48) containing `ctk.CTkButton(right_header, text="📷 Quét QR", command=self.controller.open_qr_scan_dialog)` (lines 51-61).
  - Row 1: `_form_field(form_frame, 1, 0, "Mã hàng (*):", self.app_state.item_code_var)` (line 72), `_form_field(form_frame, 1, 2, "Tên hàng (*):", self.app_state.item_name_var)` (line 73).
  - Row 2: `_form_field(form_frame, 2, 0, "SL thùng (*):", self.app_state.carton_qty_var)` (line 76), `self.total_qty_entry = self._form_field(form_frame, 2, 2, "Tổng SL (tự tính):", self.app_state.total_qty_var, is_readonly=True)` (lines 77-79).
  - Row 3: `_form_field(form_frame, 3, 0, "Số box (*):", self.app_state.box_var)` (line 82), `_form_field(form_frame, 3, 2, "Rev (*) (01–99):", self.app_state.rev_var)` (line 83).
  - Row 4 (Auto PO):
    - `self.po_entry = self._form_field(form_frame, 4, 0, "PO (tự sinh):", self.app_state.po_var, is_disabled=True)` (lines 86-88).
    - `po_sub_frame` (lines 90-93) containing:
      - `self.po_detail_entry = ctk.CTkEntry(po_sub_frame, textvariable=self.app_state.po_detail_var, ...)` (line 97, `state="disabled"` line 99).
      - `self.po_sub_entry = ctk.CTkEntry(po_sub_frame, textvariable=self.app_state.po_sub_var, ...)` (line 104, `state="disabled"` line 106).
  - Row 5: `self.lot_entry = self._form_field(form_frame, 5, 0, "Ngày/Lot:", self.app_state.lot_var, is_readonly=True)` (lines 109-111).
  - Row 6 (Primary Action Buttons `btn_bar_1`, lines 123-142):
    - `ctk.CTkButton(btn_bar_1, text="➕ Thêm mới", command=self.controller.add_record)` (lines 127-130) -> *Anonymous, not stored as an attribute on `self`*.
    - `ctk.CTkButton(btn_bar_1, text="💾 Cập nhật dòng", command=self.controller.update_selected_record)` (lines 132-135) -> *Anonymous*.
    - `ctk.CTkButton(btn_bar_1, text="🗑️ Xóa dòng", command=self.controller.delete_selected_record)` (lines 137-141) -> *Anonymous*.
  - Row 7 (Utility Buttons `btn_bar_2`, lines 144-163):
    - `ctk.CTkButton(btn_bar_2, text="Lot = 10 space", command=self.controller.fill_lot_spaces)` (lines 148-152) -> *Anonymous*.
    - `ctk.CTkButton(btn_bar_2, text="📋 Điền mẫu", command=self.controller.fill_sample_data)` (lines 154-158) -> *Anonymous*.
    - `ctk.CTkButton(btn_bar_2, text="🧹 Xóa form", command=self.clear_form)` (lines 160-163) -> *Anonymous*.
- **Row 1: Table Frame (`self.table_frame`)**:
  - `self.table_frame = ctk.CTkFrame(left_panel, corner_radius=12)` (line 166)
  - `self.preview_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)` (line 177)
  - Scrollbars: `tree_scroll_y` and `tree_scroll_x` (lines 191-197)

Inside `self.preview_frame` (lines 206-234):
- Title label: `🔍 Xem trước trang in` (line 212)
- Image label: `self.preview_image_label = ctk.CTkLabel(preview_frame, text="Chưa có dữ liệu để xem trước", ...)` (line 216)
- QR payload title label (line 222)
- Textbox: `self.qr_payload_box = ctk.CTkTextbox(preview_frame, height=65, ...)` (line 225)
- Refresh preview button: `ctk.CTkButton(preview_frame, text="🔄 Làm mới xem trước", command=self.refresh_preview_image)` (lines 229-233) -> *Anonymous*.

### 1.2 Direct Inspection of `ui/main_window.py`
In `SlipPrinterApp._build_content()` (`ui/main_window.py:152-171`):
- `notebook = ttk.Notebook(parent)` (line 152) -> *Local variable, not saved as `self.notebook`*.
- Tab 0: `self.data_tab = DataTabPanel(notebook, self.controller, corner_radius=0)` (line 156), added as `notebook.add(self.data_tab, text="Dữ liệu và xem trước")` (line 157).
- Tab 1: `self.layout_tab = LayoutTabPanel(notebook, self.controller, corner_radius=0)` (line 161), added as `notebook.add(self.layout_tab, text="Chỉnh sửa Layout PDF")` (line 162).
- Tab 2: `self.history_tab = HistoryTabPanel(notebook, self.controller, corner_radius=0)` (line 166), added as `notebook.add(self.history_tab, text="📊 Lịch sử Đăng ký EDI")` (line 167).

### 1.3 Direct Inspection of `ui/components/tutorial_overlay.py`
- `TabSyncHelper.ensure_tab_active()` (lines 370-414) and `InteractiveTutorialOverlay._render_current_step()` (lines 620-633) automatically look up `self.notebook` or `self.master.notebook` when `step.target_tab_index` is specified.
- If `self.master.notebook` is not set on `SlipPrinterApp`, `InteractiveTutorialOverlay` falls back to `TabSyncHelper.find_parent_notebook(target_widget)`. However, setting `self.notebook = notebook` on `SlipPrinterApp` ensures 100% deterministic tab synchronization.

---

## 2. Logic Chain

1. **Step 3 (Auto PO & Manual Form)** requires highlighting either the entire `form_frame`, the auto PO entry (`self.po_entry`), or the `➕ Thêm mới` button (`add_record`), while ensuring Tab 0 (`DataTabPanel`) is active.
   - Evidence: `self.form_frame` and `self.po_entry` exist as attributes, but the `➕ Thêm mới` button is currently an anonymous local widget inside `_build()`.
   - Inference: Assigning `self.btn_add_record = ctk.CTkButton(...)` in `_build()` and exposing accessor methods (`get_form_frame()`, `get_auto_po_widget()`, `get_add_button_widget()`) allows both the Tutorial Engine and test suites to access these widgets directly without brittle DOM crawling.

2. **Step 4 (PDF Generation & Preview Frame / Treeview)** requires highlighting the `SidebarPanel.generate_button` and/or the `DataTabPanel.preview_frame` / `self.preview_tree`.
   - Evidence: `self.preview_frame` and `self.preview_tree` exist on `DataTabPanel`.
   - Inference: Providing accessor methods `get_preview_frame()`, `get_treeview_widget()`, and `get_preview_image_label()` standardizes access across components.

3. **Tab Switching Synchronization**:
   - Evidence: `DataTabPanel` is at index 0 of `ttk.Notebook`. In `main_window.py:152`, `notebook` is currently a local variable.
   - Inference: Exposing `self.notebook = notebook` in `SlipPrinterApp` enables `TutorialOverlay` to directly switch tabs (`self.notebook.select(0)`) and invoke `update_idletasks()` before geometry calculations, eliminating any unmapped widget geometry issues.

---

## 3. Caveats

- **Existing Tests DOM Crawling**: Some existing stress tests (e.g. `tests/test_adversarial_stress.py:58-71`) traverse `form_frame.winfo_children()` to find buttons. Adding named attributes (`self.btn_add_record`, `self.btn_update_record`, etc.) and accessor methods is 100% backward-compatible and will not break existing tests.
- **CustomTkinter `.place()` Geometry Contract**: In CustomTkinter, `CTkBaseClass.place()` does not accept `width` or `height` keyword arguments; attempting `widget.place(..., width=120, height=35)` throws `ValueError: 'width' and 'height' arguments must be passed to the constructor of the widget, not the place method`. Any mock widgets or tutorial components must pass `width` and `height` in the widget constructor (e.g. `ctk.CTkButton(master, width=120, height=35)`) before calling `.place(x=..., y=...)`.
- **DPI / Unmapped Geometry**: When switching to Tab 0 from another tab, Tkinter requires `update_idletasks()` before `winfo_rootx()` / `winfo_rooty()` return non-zero coordinates. `InteractiveTutorialOverlay` already handles this via `TabSyncHelper.ensure_tab_active()` and `self.master.update_idletasks()`.

---

## 4. Conclusion & Recommended Specifications

### 4.1 Recommended Attribute Assignments in `ui/components/data_tab.py`
In `DataTabPanel._build()`:
```python
# Save button references as attributes
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

# Primary buttons
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

# Preview refresh button
self.btn_refresh_preview = ctk.CTkButton(
    preview_frame, text="🔄 Làm mới xem trước", height=32,
    fg_color=("gray85", "gray25"), text_color=("gray10", "gray90"), hover_color=("gray75", "gray35"),
    command=self.refresh_preview_image
)
self.btn_refresh_preview.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 12))
```

### 4.2 Recommended Accessor Methods on `DataTabPanel`
Add to `DataTabPanel`:
```python
# --- STEP 3 & FORM ACCESSORS ---
def get_form_frame(self) -> ctk.CTkFrame:
    """Return the manual entry form container frame."""
    return self.form_frame

def get_auto_po_widget(self) -> ctk.CTkEntry:
    """Return the auto-generated PO number entry widget."""
    return self.po_entry

def get_po_detail_widget(self) -> ctk.CTkEntry:
    """Return the PO detail entry widget."""
    return self.po_detail_entry

def get_po_sub_widget(self) -> ctk.CTkEntry:
    """Return the PO sub entry widget."""
    return self.po_sub_entry

def get_add_button_widget(self) -> ctk.CTkButton:
    """Return the '➕ Thêm mới' primary action button widget."""
    return getattr(self, "btn_add_record", None)

def get_update_button_widget(self) -> ctk.CTkButton:
    """Return the '💾 Cập nhật dòng' button widget."""
    return getattr(self, "btn_update_record", None)

def get_delete_button_widget(self) -> ctk.CTkButton:
    """Return the '🗑️ Xóa dòng' button widget."""
    return getattr(self, "btn_delete_record", None)

def get_qr_button_widget(self) -> ctk.CTkButton:
    """Return the '📷 Quét QR' button widget in the form header."""
    return getattr(self, "btn_qr_scan", None)

# --- TABLE & PREVIEW ACCESSORS ---
def get_treeview_widget(self) -> ttk.Treeview:
    """Return the Treeview table widget."""
    return self.preview_tree

def get_table_frame(self) -> ctk.CTkFrame:
    """Return the table container frame."""
    return self.table_frame

def get_preview_frame(self) -> ctk.CTkFrame:
    """Return the preview container frame on the right panel."""
    return self.preview_frame

def get_preview_image_label(self) -> ctk.CTkLabel:
    """Return the label displaying the slip preview image."""
    return self.preview_image_label

def get_qr_payload_box(self) -> ctk.CTkTextbox:
    """Return the textbox displaying the QR code payload."""
    return self.qr_payload_box

def get_refresh_preview_button(self) -> ctk.CTkButton:
    """Return the '🔄 Làm mới xem trước' button widget."""
    return getattr(self, "btn_refresh_preview", None)
```

### 4.3 Recommended Notebook Exposure in `ui/main_window.py`
In `SlipPrinterApp._build_content(parent)`:
```python
# Change line 152:
self.notebook = ttk.Notebook(parent)
self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 6))

self.data_tab = DataTabPanel(self.notebook, self.controller, corner_radius=0)
self.notebook.add(self.data_tab, text="Dữ liệu và xem trước")
self.data_tab.set_records(select_index=None)

self.layout_tab = LayoutTabPanel(self.notebook, self.controller, corner_radius=0)
self.notebook.add(self.layout_tab, text="Chỉnh sửa Layout PDF")

self.history_tab = HistoryTabPanel(self.notebook, self.controller, corner_radius=0)
self.notebook.add(self.history_tab, text="📊 Lịch sử Đăng ký EDI")

self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)
```

### 4.4 Mapping for Milestone 2 Tutorial Steps 3 & 4
- **Step 3: Auto PO generation & Form Entry**:
  - `target_widget_getter = lambda: app.data_tab.get_add_button_widget()` (or `app.data_tab.get_form_frame()`)
  - `target_tab_index = 0` (`DataTabPanel`)
  - `tooltip_position = "bottom"` or `"right"`
- **Step 4: PDF Generation & Preview**:
  - `target_widget_getter = lambda: app.sidebar.get_generate_pdf_button()` (or `app.data_tab.get_preview_frame()`)
  - `target_tab_index = 0` (`DataTabPanel`)
  - `tooltip_position = "right"` or `"auto"`

---

## 5. Verification Method

To independently verify the widget hierarchy and accessor contracts:

1. **Static Analysis & Inspection**:
   - Inspect `ui/components/data_tab.py` lines 17-238 to confirm the widget hierarchy matches the observation section.
   - Inspect `ui/main_window.py` lines 152-171 to verify notebook tab indices (Tab 0 = DataTab, Tab 1 = LayoutTab, Tab 2 = HistoryTab).

2. **Automated Unit / Integration Test Command**:
   ```powershell
   pytest tests/test_tutorial_overlay.py tests/test_tutorial_overlay_e2e.py -v
   ```

3. **Runtime Contract Check Script**:
   ```python
   import customtkinter as ctk
   from ui.app_controller import AppController
   from ui.app_state import AppState
   from ui.components.data_tab import DataTabPanel

   root = ctk.CTk()
   state = AppState(root)
   ctrl = AppController(state)
   tab = DataTabPanel(root, ctrl)

   assert tab.get_form_frame() is not None
   assert tab.get_auto_po_widget() is not None
   assert tab.get_treeview_widget() is not None
   assert tab.get_preview_frame() is not None
   assert tab.get_add_button_widget() is not None
   print("All DataTabPanel widget accessors verified successfully.")
   root.destroy()
   ```
