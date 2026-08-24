# Forensic Audit Report — Milestone 2

**Work Product**: Milestone 2: Tutorial Script & Business Flow Integration (`ui/components/tutorial_script.py`, `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/main_window.py`, `ui/app_controller.py`, `tests/test_tutorial_script.py`, `tests/test_tutorial_overlay.py`)  
**Profile**: General Project  
**Integrity Mode**: Development Mode (Ground truth: `ORIGINAL_REQUEST.md`)  
**Verdict**: **CLEAN**

---

## 1. Observation

### Observation 1: Tutorial Script Factory Implementation (`ui/components/tutorial_script.py`)
- **File & Lines**: `ui/components/tutorial_script.py:32-250`
- **Function**: `build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]`
- **Structure**:
  - Dynamically constructs a list of 4 `TutorialStep` instances corresponding to the 4 core business workflows specified in `ORIGINAL_REQUEST.md` §R2:
    1. `step_excel_import` (Lines 186–199): Title `"1. Nạp dữ liệu từ Excel"`, comprehensive description detailing Excel `.xlsx` format, required columns (Mã hàng, Tên hàng, SL thùng, Số box, Rev 01–99), empty Lot handling (10 spaces in QR), and duplicate warning detection.
    2. `step_qr_scanner` (Lines 202–215): Title `"2. Quét mã QR thông minh"`, detailed description of the 3 dedicated operational modes: Phân tách (分割), Hoàn kho (戻入) with 900+ suffix, and Bóc tách / Nhập tem (129 chars).
    3. `step_auto_po` (Lines 218–231): Title `"3. Tạo mã Auto PO & Thêm phiếu"`, detailed explanation of auto-incrementing `11YYMMDDNN` PO formatting, PO Registry anti-collision guarantee, manual entry, and 'Điền mẫu' action.
    4. `step_pdf_generation` (Lines 234–247): Title `"4. Tạo & In phiếu hiện vật PDF"`, detailed explanation of visual print preview, 129-char QR inspection, 4 slips per A4 page layout packaging, 'Tạo PDF', and direct opening via 'Mở PDF vừa tạo'.
  - Contains dynamic widget target resolver functions (`_get_excel_target`, `_get_qr_target`, `_get_form_target`, `_get_pdf_target`) with resilient fallback hierarchy: method getter -> direct attribute names -> fallback frame -> `None`.

### Observation 2: Named Widget Accessors in `SidebarPanel` (`ui/components/sidebar.py`)
- **File & Lines**: `ui/components/sidebar.py:114–169`
- **Methods**:
  - `get_excel_import_widget()` -> returns `self.excel_import_button` (Line 118)
  - `get_excel_path_widget()` -> returns `self.excel_entry` (Line 122)
  - `get_excel_frame_widget()` -> returns `self.excel_frame` (Line 126)
  - `get_qr_scan_widget()` -> returns `self.qr_scan_button` (Line 130)
  - `get_generate_pdf_widget()` -> returns `self.generate_button` (Line 134)
  - `get_open_pdf_widget()` -> returns `self.open_pdf_button` (Line 138)
- **Compatibility Property Aliases**: `excel_import_btn`, `btn_import_excel`, `qr_scan_btn`, `btn_qr_scan`, `btn_generate_pdf`, `open_pdf_btn`, `btn_open_pdf` (Lines 142–168).

### Observation 3: Named Widget Accessors in `DataTabPanel` (`ui/components/data_tab.py`)
- **File & Lines**: `ui/components/data_tab.py:437–512`
- **Methods**:
  - `get_form_frame()` -> returns `self.form_frame` (Line 441)
  - `get_auto_po_widget()` -> returns `self.po_entry` (Line 445)
  - `get_po_detail_widget()` -> returns `self.po_detail_entry` (Line 449)
  - `get_po_sub_widget()` -> returns `self.po_sub_entry` (Line 453)
  - `get_add_button_widget()` -> returns `self.btn_add_record` (Line 457)
  - `get_update_button_widget()` -> returns `self.btn_update_record` (Line 461)
  - `get_delete_button_widget()` -> returns `self.btn_delete_record` (Line 465)
  - `get_qr_button_widget()` -> returns `self.btn_qr_scan` (Line 469)
  - `get_treeview_widget()` -> returns `self.preview_tree` (Line 473)
  - `get_table_frame()` -> returns `self.table_frame` (Line 477)
  - `get_preview_frame()` -> returns `self.preview_frame` (Line 481)
  - `get_preview_image_label()` -> returns `self.preview_image_label` (Line 485)
  - `get_qr_payload_box()` -> returns `self.qr_payload_box` (Line 489)
  - `get_refresh_preview_button()` -> returns `self.btn_refresh_preview` (Line 493)
- **Compatibility Property Aliases**: `qr_scan_btn`, `add_btn`, `update_btn`, `delete_btn` (Lines 497–511).

### Observation 4: Controller & App Integration (`ui/app_controller.py` & `ui/main_window.py`)
- **`ui/app_controller.py:56–66`**: `get_tutorial_steps()` dynamically resolves steps from `tutorial_script.py`, and `start_tutorial()` launches the overlay via the view.
- **`ui/main_window.py:426–444`**: `get_tutorial_steps()` dynamically calls `build_tutorial_steps(self)` and `start_tutorial()` instantiates `InteractiveTutorialOverlay` with `notebook` awareness, registers the 4 steps, and launches overlay.

### Observation 5: Dynamic Test Execution Results
- **Command**: `pytest tests/test_tutorial_script.py tests/test_tutorial_overlay.py -v`
- **Result**:
```
============================= test session starts =============================
platform win32 -- Python 3.13.5, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\tvn183660\AppData\Local\Programs\Python\Python313\python.exe
cachedir: .pytest_cache
rootdir: D:\Sandbox\PM_in_lai_phieuhienvat
configfile: pytest.ini
plugins: anyio-4.11.0, cov-7.0.0, mock-3.15.1
collected 35 items

tests/test_tutorial_script.py::TestTutorialScriptStructure::test_build_tutorial_steps_headless_returns_four_steps PASSED [  2%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step_ids_and_order PASSED [  5%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_all_steps_target_tab_index_zero PASSED [  8%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step1_excel_import_vietnamese_content PASSED [ 11%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step2_qr_scanner_vietnamese_content PASSED [ 14%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step3_auto_po_vietnamese_content PASSED [ 17%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step4_pdf_generation_vietnamese_content PASSED [ 20%]
tests/test_tutorial_script.py::TestTutorialScriptStructure::test_step_tooltips_and_padding PASSED [ 22%]
tests/test_tutorial_script.py::TestWidgetGettersWithNoneAndMocks::test_widget_getters_return_none_when_app_none PASSED [ 25%]
tests/test_tutorial_script.py::TestWidgetGettersWithNoneAndMocks::test_widget_getters_with_mock_accessors PASSED [ 28%]
tests/test_tutorial_script.py::TestWidgetGettersWithNoneAndMocks::test_widget_getters_fallback_to_attribute_names PASSED [ 31%]
tests/test_tutorial_script.py::TestWidgetGettersWithNoneAndMocks::test_widget_getter_with_controller_wrapper PASSED [ 34%]
tests/test_tutorial_script.py::TestWidgetGettersWithNoneAndMocks::test_widget_getter_handles_exceptions_gracefully PASSED [ 37%]
tests/test_tutorial_script.py::TestSidebarAndDataTabAccessors::test_sidebar_and_data_tab_accessors_and_aliases PASSED [ 40%]
tests/test_tutorial_script.py::TestReExportAndControllerIntegration::test_reexport_from_tutorial_overlay PASSED [ 42%]
tests/test_tutorial_script.py::TestReExportAndControllerIntegration::test_controller_get_tutorial_steps_headless PASSED [ 45%]
tests/test_tutorial_script.py::TestReExportAndControllerIntegration::test_controller_get_tutorial_steps_with_view PASSED [ 48%]
tests/test_tutorial_script.py::TestReExportAndControllerIntegration::test_main_window_get_tutorial_steps PASSED [ 51%]
tests/test_tutorial_script.py::TestReExportAndControllerIntegration::test_real_app_hierarchy_steps_wiring PASSED [ 54%]
tests/test_tutorial_overlay.py::TestTutorialStep::test_step_initialization_defaults PASSED [ 57%]
tests/test_tutorial_overlay.py::TestTutorialStep::test_step_custom_properties PASSED [ 60%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_center_fallback_when_none PASSED [ 62%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_center_when_preferred_is_center PASSED [ 65%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_bottom_placement_when_fits PASSED [ 68%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_top_placement_when_fits PASSED [ 71%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_right_placement_when_fits PASSED [ 74%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_left_placement_when_fits PASSED [ 77%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_overflow_flip_bottom_to_top PASSED [ 80%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_boundary_clamping PASSED [ 82%]
tests/test_tutorial_overlay.py::TestGeometryAndPartitioning::test_4_rectangle_partition_area_conservation PASSED [ 85%]
tests/test_tutorial_overlay.py::TestTooltipCard::test_tooltip_card_creation_and_callbacks PASSED [ 88%]
tests/test_tutorial_overlay.py::TestTooltipCard::test_tooltip_card_update_content PASSED [ 91%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_lifecycle_and_navigation PASSED [ 94%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_skip PASSED [ 97%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_tab_sync PASSED [100%]

======================= 35 passed, 1 warning in 32.50s ========================
```

---

## 2. Logic Chain

1. **Static Analysis & Prohibited Pattern Check**:
   - Inspected `ui/components/tutorial_script.py`, `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/main_window.py`, and `ui/app_controller.py`.
   - No hardcoded test results, no dummy facade methods returning static mock values, and no fabricated log artifacts exist.
   - All widget accessor methods in `SidebarPanel` and `DataTabPanel` return genuine `CustomTkinter` and `Tkinter` widget instances.
   - The Vietnamese copy directly and accurately describes all required business workflows (Excel import with duplicate warnings, 3 QR scanning modes, Auto PO generation with PO Registry, and 4 slips/A4 PDF generation).

2. **Interface Contract & Architecture Adherence**:
   - `build_tutorial_steps()` instantiates `TutorialStep` conforming exactly to the interface contracts defined in `PROJECT.md`.
   - Step getters gracefully handle headless mode (`app=None`), controller wrappers (`app.view`), and live widget trees without throwing unhandled exceptions.

3. **Behavioral & Dynamic Execution**:
   - The test suite `tests/test_tutorial_script.py` and `tests/test_tutorial_overlay.py` executed live in 32.50 seconds.
   - All 35 unit and integration tests passed without failures or skips (100% pass rate).

4. **Integrity Mode Conformance**:
   - Under `development` integrity mode (and verified against higher strictness standards), zero integrity violations were detected.

---

## 3. Caveats

- Milestone 3 UI trigger button (`💡 Hướng dẫn` in the header) and persistence (`user_settings.json` first-launch hook) are planned for Milestone 3 and were not part of Milestone 2 scope. Milestone 2 scope is strictly the tutorial script, business flow integration, and widget accessors.
- No other caveats.

---

## 4. Conclusion

Milestone 2 is **CLEAN**. The implementation is genuine, robust, fully tested, and adheres to all user requirements and architectural constraints.

---

## 5. Verification Method

To independently verify this audit:
```powershell
pytest tests/test_tutorial_script.py tests/test_tutorial_overlay.py -v
```
All 35 tests must pass with exit code 0.
