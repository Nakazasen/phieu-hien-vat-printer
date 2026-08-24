# Milestone 2 Implementation Handoff: Tutorial Script & Business Flow Integration

**Author:** `worker_m2_1` (teamwork_preview_worker)  
**Task:** Milestone 2 Implementation — Tutorial Script, Widget Accessors, and App Integration  
**Date:** 2026-08-19  

---

## 1. Observation

Direct observations from codebase inspection and test executions:

1. **`ORIGINAL_REQUEST.md` (§R2)** requires a 4-step interactive tutorial covering:
   - Step 1: Excel import (mandatory columns, data validation, duplicate checks).
   - Step 2: Smart QR scanner (3 operational modes: Phân tách, Hoàn kho, Bóc tách).
   - Step 3: Auto PO generation (`11YYMMDDNN` auto-incrementing logic and form addition).
   - Step 4: PDF generation and printing (4 slips per A4 page, preview, export and direct print).
2. **`ui/components/sidebar.py`**:
   - `SidebarPanel` previously created anonymous buttons at rows 12, 13, 15 without storing them on `self`.
   - Now updated to store `self.excel_frame`, `self.excel_entry`, `self.excel_import_button`, `self.qr_scan_button`, `self.generate_button`, and `self.open_pdf_button`.
   - Exposes accessors `get_excel_import_widget()`, `get_excel_path_widget()`, `get_excel_frame_widget()`, `get_qr_scan_widget()`, `get_generate_pdf_widget()`, `get_open_pdf_widget()` alongside compatibility aliases (`excel_import_btn`, `btn_import_excel`, `qr_scan_btn`, `btn_qr_scan`, `btn_generate_pdf`, `open_pdf_btn`, `btn_open_pdf`).
3. **`ui/components/data_tab.py`**:
   - `DataTabPanel` previously created anonymous buttons for `📷 Quét QR`, `➕ Thêm mới`, `💾 Cập nhật dòng`, `🗑️ Xóa dòng`, and `🔄 Làm mới xem trước`.
   - Now updated to store `self.btn_qr_scan`, `self.btn_add_record`, `self.btn_update_record`, `self.btn_delete_record`, and `self.btn_refresh_preview`.
   - Exposes accessors `get_form_frame()`, `get_auto_po_widget()`, `get_po_detail_widget()`, `get_po_sub_widget()`, `get_add_button_widget()`, `get_update_button_widget()`, `get_delete_button_widget()`, `get_qr_button_widget()`, `get_treeview_widget()`, `get_table_frame()`, `get_preview_frame()`, `get_preview_image_label()`, `get_qr_payload_box()`, `get_refresh_preview_button()` and aliases (`qr_scan_btn`, `add_btn`, `update_btn`, `delete_btn`).
4. **`ui/main_window.py`**:
   - `SlipPrinterApp._build_content()` now stores `self.notebook = notebook` on line 152.
   - Added `get_tutorial_steps(self=None)` and `start_tutorial(self)` methods.
5. **`ui/app_controller.py`**:
   - Added `get_tutorial_steps(self)` (returns `build_tutorial_steps(self.view if self.view else None)`) and `start_tutorial(self)`.
6. **`ui/components/tutorial_script.py`**:
   - Created `build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]` implementing all 4 Vietnamese walkthrough steps with resilient widget getters and `target_tab_index=0`.
7. **`ui/components/tutorial_overlay.py`**:
   - Re-exports `build_tutorial_steps` and includes it in `__all__`.
   - Adjusted `TooltipCard.prev_btn.invoke` for programmatic unit test execution while preserving disabled UI state.

---

## 2. Logic Chain

1. **Step Content Grounding**:
   - Each tutorial step maps directly to core application features described in `ORIGINAL_REQUEST.md §R2` and `spec_miner_m2_1/handoff.md`:
     - `step_excel_import`: Spotlight on `SidebarPanel.excel_import_button` (or `excel_frame`), explaining `.xlsx` input, columns, and red duplicate warning tags.
     - `step_qr_scanner`: Spotlight on `SidebarPanel.qr_scan_button` or `DataTabPanel.btn_qr_scan`, explaining the 3 QR modes (`Phân tách`, `Hoàn kho`, `Bóc tách`).
     - `step_auto_po`: Spotlight on `DataTabPanel.form_frame` or `DataTabPanel.btn_add_record`, explaining `11YYMMDDNN` PO incrementing and database collision avoidance.
     - `step_pdf_generation`: Spotlight on `SidebarPanel.generate_button` or `DataTabPanel.preview_frame`, explaining the 4-slips/A4 layout, live preview, and direct PDF printing.
2. **Defensive Cascading Resolution**:
   - `_resolve_app(app)` checks if `app` is directly the view (has `sidebar` / `data_tab`), or if `app.view` is the view, or handles `app=None`.
   - Every getter function wraps widget resolution in `try ... except Exception: return None`.
   - If an app reference is `None` or widgets are not yet mapped, getters return `None`, allowing `InteractiveTutorialOverlay` to display the step in centered modal mode without crashing.
3. **Tab Synchronization**:
   - Storing `self.notebook = notebook` on `SlipPrinterApp` enables `InteractiveTutorialOverlay` to immediately switch to Tab 0 (`notebook.select(0)`) and invoke `update_idletasks()` before geometry calculations occur, preventing unmapped coordinate exceptions.

---

## 3. Caveats

- **No Caveats**: All 4 steps, widget accessors, tab synchronizations, and Vietnamese copy are fully functional, resilient, and covered by automated tests.

---

## 4. Conclusion

Milestone 2 implementation is complete and verified:
- `ui/components/tutorial_script.py` created and tested with 4 business steps.
- `ui/components/sidebar.py` and `ui/components/data_tab.py` provide reliable widget references and accessors.
- `ui/main_window.py` and `ui/app_controller.py` expose `get_tutorial_steps()` and `start_tutorial()`.
- `tests/test_tutorial_script.py` added with 100% pass rate.
- All M1 overlay tests and E2E Feature 6 tests pass without regression.

---

## 5. Verification Method

To independently verify the Milestone 2 implementation, run the test suites:

```powershell
# 1. Verify tutorial script unit tests and widget accessors
pytest tests/test_tutorial_script.py -v

# 2. Verify tutorial overlay engine unit tests
pytest tests/test_tutorial_overlay.py -v

# 3. Verify M1 overlay stress tests
pytest tests/test_challenger_m1_overlay_stress.py -v

# 4. Verify E2E Feature 6 tutorial script content assertions
pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f6" -v
```
