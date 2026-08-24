# Milestone 2 Review & Adversarial Challenge Report

## Review Summary

**Verdict**: **APPROVE**  
**Assessment**: The Milestone 2 deliverables (`ui/components/tutorial_script.py`, `ui/components/sidebar.py`, `ui/components/data_tab.py`, `tests/test_tutorial_script.py`) completely and authentically fulfill all requirements specified in `ORIGINAL_REQUEST.md` §R2 and `PROJECT.md` M2. No integrity violations, facade implementations, or hardcoded shortcuts were detected.

---

## 1. Observation

Direct code examination and execution yielded the following observations:

### A. Business Requirements Coverage (`ORIGINAL_REQUEST.md` §R2)
1. **Excel Import Walkthrough (§R2.1)**:
   - File: `ui/components/tutorial_script.py:186-199`
   - Step ID: `step_excel_import`
   - Title: `"1. Nạp dữ liệu từ Excel"`
   - Content: Guides user to select `.xlsx` file and click `"Import từ Excel"`. Highlights required columns (`Mã hàng`, `Tên hàng`, `SL thùng`, `Số box`, `Rev`), describes blank Lot behavior (10 spaces in QR), and warns about automatic red highlight for duplicates.
   - Getter: `_get_excel_target` dynamically queries `sidebar.get_excel_import_widget()`, falling back to `excel_import_button`, `excel_import_btn`, `btn_import_excel`, `excel_frame`, or `sidebar`.

2. **Smart QR Scanner 3 Modes (§R2.2)**:
   - File: `ui/components/tutorial_script.py:202-215`
   - Step ID: `step_qr_scanner`
   - Title: `"2. Quét mã QR thông minh"`
   - Content: Explains opening the scanner tool and details all 3 operational modes:
     1. Phân tách (分割): Splits large cartons while maintaining root PO and incrementing detail POs (`00010`, `00020`, ...).
     2. Hoàn kho (戻入): Processes returns with detail POs in the 900+ series (`00900`, `00910`, ...).
     3. Bóc tách / Nhập tem: Decodes 129-character QR string into data grid or form.
   - Getter: `_get_qr_target` queries `sidebar.get_qr_scan_widget()` and `data_tab.get_qr_button_widget()`.

3. **Auto PO & Manual Entry (§R2.3)**:
   - File: `ui/components/tutorial_script.py:218-231`
   - Step ID: `step_auto_po`
   - Title: `"3. Tạo mã Auto PO & Thêm phiếu"`
   - Content: Explains auto-generation of PO numbers adhering to the standard `11YYMMDDNN` specification (11 + YYMMDD + sequence 01-99), uniqueness guarantee via SQLite `PORegistry`, and quick actions (`➕ Thêm mới`, `📋 Điền mẫu`).
   - Getter: `_get_form_target` queries `data_tab.get_form_frame()`, `data_tab.get_add_button_widget()`, and attribute fallbacks.

4. **PDF Generation & Printing (§R2.4)**:
   - File: `ui/components/tutorial_script.py:234-247`
   - Step ID: `step_pdf_generation`
   - Title: `"4. Tạo & In phiếu hiện vật PDF"`
   - Content: Explains visual preview of 129-character QR string, paper-saving automatic 4-slips-per-A4 page imposition, and the two-step action `"Tạo PDF"` and `"Mở PDF vừa tạo"`.
   - Getter: `_get_pdf_target` queries `sidebar.get_generate_pdf_widget()` and `data_tab.get_preview_frame()`.

### B. Widget Accessors & Properties (`ui/components/sidebar.py` & `ui/components/data_tab.py`)
- **`SidebarPanel` (`ui/components/sidebar.py:116-168`)**:
  - Exposes dedicated methods: `get_excel_import_widget()`, `get_excel_path_widget()`, `get_excel_frame_widget()`, `get_qr_scan_widget()`, `get_generate_pdf_widget()`, `get_open_pdf_widget()`.
  - Exposes compatibility property aliases: `excel_import_btn`, `btn_import_excel`, `qr_scan_btn`, `btn_qr_scan`, `btn_generate_pdf`, `open_pdf_btn`, `btn_open_pdf`.
- **`DataTabPanel` (`ui/components/data_tab.py:439-512`)**:
  - Exposes dedicated methods: `get_form_frame()`, `get_auto_po_widget()`, `get_po_detail_widget()`, `get_po_sub_widget()`, `get_add_button_widget()`, `get_update_button_widget()`, `get_delete_button_widget()`, `get_qr_button_widget()`, `get_treeview_widget()`, `get_table_frame()`, `get_preview_frame()`, `get_preview_image_label()`, `get_qr_payload_box()`, `get_refresh_preview_button()`.
  - Exposes compatibility property aliases: `qr_scan_btn`, `add_btn`, `update_btn`, `delete_btn`.

### C. Test Execution Output
- Command: `pytest tests/test_tutorial_script.py tests/test_tutorial_overlay.py -v`
- Result: `35 passed, 1 warning in 40.20s` (Exit code: 0)
- 18 tests in `tests/test_tutorial_script.py` and 17 tests in `tests/test_tutorial_overlay.py` all passed.

---

## 2. Logic Chain

1. **Step Content Grounding**:
   - `ORIGINAL_REQUEST.md` §R2 specifies 4 core workflows: Excel Import, QR Scanner (3 modes), Auto PO, and PDF Generation.
   - `build_tutorial_steps()` in `tutorial_script.py` constructs exactly 4 `TutorialStep` instances with IDs `step_excel_import`, `step_qr_scanner`, `step_auto_po`, and `step_pdf_generation`.
   - Each step's description accurately and clearly explains the exact business logic (required Excel columns, 10-space lot padding, split/return/extract QR modes, `11YYMMDDNN` PO format, 4 slips/A4 layout).

2. **Decoupling and Fault Tolerance**:
   - `build_tutorial_steps()` accepts an optional `app` reference (`SlipPrinterApp` or `AppController`).
   - If `app` is `None` (headless / testing mode) or if any accessor raises an exception, the widget getters catch the error and safely return `None`.
   - `InteractiveTutorialOverlay` handles `target_widget = None` by displaying a full scrim and placing the tooltip card in the center of the window (`PlacementEngine.calculate(..., None)`), preventing GUI lockup or crashes.

3. **Architectural Conformance**:
   - `SidebarPanel` and `DataTabPanel` retain clear separation of concerns, storing actual Tkinter/CustomTkinter widgets (`excel_import_button`, `qr_scan_button`, `generate_button`, `form_frame`, etc.) and providing accessor methods with type annotations.
   - `ui/components/tutorial_overlay.py` re-exports `build_tutorial_steps` and includes it in `__all__`, maintaining backwards compatibility with any modules importing directly from `tutorial_overlay`.
   - `AppController` and `SlipPrinterApp` provide `get_tutorial_steps()` and `start_tutorial()` methods to trigger the workflow.

4. **Integrity Verification**:
   - No mock or hardcoded return values are embedded in production code.
   - Widget accessors directly return `getattr(self, ...)`.
   - Tests instantiate real `AppState`, `AppController`, `SidebarPanel`, and `DataTabPanel` widgets against a live Tk root, verifying that actual object identities match.

---

## 3. Caveats

- **Milestone 3 Integration**: The manual trigger button on the header (`💡 Hướng dẫn`) and persistent tracking (`has_seen_tutorial` in `user_settings.json`) are scheduled for Milestone 3 according to `PROJECT.md` and are therefore not part of Milestone 2 review scope.
- **PyPDF2 Warning**: The test log output reported a non-blocking `DeprecationWarning` regarding `PyPDF2` in third-party library dependencies, which does not affect tutorial functionality.

---

## 4. Conclusion

Milestone 2 implementation is **complete, robust, and cleanly designed**. It satisfies 100% of the functional and architectural requirements for tutorial scripts and panel widget accessors.

**Final Verdict**: **APPROVE**

---

## 5. Verification Method

To independently verify these findings:

1. Run the test suites:
   ```powershell
   pytest tests/test_tutorial_script.py tests/test_tutorial_overlay.py -v
   ```
   *Expected outcome*: 35 passed tests.

2. Inspect the implementation files:
   - `ui/components/tutorial_script.py` (lines 32-250)
   - `ui/components/sidebar.py` (lines 115-168)
   - `ui/components/data_tab.py` (lines 438-512)
   - `ui/components/tutorial_overlay.py` (lines 861-875)
