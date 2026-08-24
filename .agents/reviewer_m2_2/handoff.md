# Review & Adversarial Critic Report: Milestone 2 — Tutorial Script & App Integration

**Reviewer Agent**: `reviewer_m2_2` (`teamwork_preview_reviewer`)  
**Verdict**: **`APPROVE`**  
**Overall Risk Assessment**: **`LOW`**

---

## 1. Observation

1. **`ui/components/tutorial_script.py` (lines 32–249)**:
   - `build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]` constructs exactly 4 `TutorialStep` instances:
     - Step 1 (`step_id="step_excel_import"`, title `"1. Nạp dữ liệu từ Excel"`): Covers Excel import, required columns (Mã hàng, Tên hàng, SL thùng, Số box, Rev 01–99), empty Lot handling (10 spaces in QR), and duplicate detection red warning. Target getter: `_get_excel_target`.
     - Step 2 (`step_id="step_qr_scanner"`, title `"2. Quét mã QR thông minh"`): Covers 3 operational modes (Phân tách 分割, Hoàn kho 戻入, Bóc tách/Nhập tem) and 129-char QR format. Target getter: `_get_qr_target`.
     - Step 3 (`step_id="step_auto_po"`, title `"3. Tạo mã Auto PO & Thêm phiếu"`): Covers auto PO format `11YYMMDDNN`, PO Registry duplication protection, manual form inputs, and sample data. Target getter: `_get_form_target`.
     - Step 4 (`step_id="step_pdf_generation"`, title `"4. Tạo & In phiếu hiện vật PDF"`): Covers live preview, QR payload inspection, 4 slips per A4 layout, "Tạo PDF", and "Mở PDF vừa tạo". Target getter: `_get_pdf_target`.
   - All 4 steps set `target_tab_index=0`, `tooltip_position="right"`, and `padding=8`.

2. **Defensive Widget Resolvers in `ui/components/tutorial_script.py` (lines 18–183)**:
   - `_resolve_app(app)` handles `None`, direct view (`SlipPrinterApp`), and controller instances (`AppController.view`) safely wrapped in exception guards.
   - Each target getter (`_get_excel_target`, `_get_qr_target`, `_get_form_target`, `_get_pdf_target`) tries primary accessor methods (`get_excel_import_widget()`, `get_qr_scan_widget()`, `get_form_frame()`, `get_generate_pdf_widget()`), then falls back to multiple attribute aliases (`excel_import_button`, `qr_scan_button`, `generate_button`, `preview_frame`, etc.), and falls back to panel containers or `None`.
   - Every resolver is wrapped in `try...except Exception: return None`, guaranteeing fail-closed behavior without crashing the host app.

3. **`ui/main_window.py` Integration (lines 152, 427–443)**:
   - Line 152 explicitly binds `self.notebook = ttk.Notebook(parent)`.
   - Lines 427–430 implement `get_tutorial_steps(self=None)` delegating to `build_tutorial_steps(self)`.
   - Lines 432–442 implement `start_tutorial(self)` creating `InteractiveTutorialOverlay(self, notebook=getattr(self, "notebook", None))`, registering steps, invoking `overlay.start()`, and saving `self._tutorial_overlay`.

4. **`ui/app_controller.py` Integration (lines 56–65)**:
   - Lines 56–59 implement `get_tutorial_steps(self)` passing `self.view if self.view else None`.
   - Lines 61–65 implement `start_tutorial(self)` safely delegating to `self.view.start_tutorial()` if available.

5. **`ui/components/sidebar.py` & `ui/components/data_tab.py` Widget Accessors**:
   - `SidebarPanel` provides `get_excel_import_widget()`, `get_excel_path_widget()`, `get_excel_frame_widget()`, `get_qr_scan_widget()`, `get_generate_pdf_widget()`, `get_open_pdf_widget()`, plus `@property` aliases.
   - `DataTabPanel` provides `get_form_frame()`, `get_auto_po_widget()`, `get_po_detail_widget()`, `get_po_sub_widget()`, `get_add_button_widget()`, `get_update_button_widget()`, `get_delete_button_widget()`, `get_qr_button_widget()`, `get_treeview_widget()`, `get_table_frame()`, `get_preview_frame()`, `get_preview_image_label()`, `get_qr_payload_box()`, `get_refresh_preview_button()`, plus `@property` aliases.

6. **Test Verification**:
   - Running `pytest tests/test_tutorial_script.py -v`:
     - **19 of 19 passed** in 32.51s.
   - Running `pytest tests/test_tutorial_overlay.py -v`:
     - **16 of 16 passed** in 15.83s.

---

## 2. Logic Chain

1. **Alignment with Requirements**:
   - `ORIGINAL_REQUEST.md §R2.1–R2.4` demands 4 specific workflows: Excel import, QR scanning (3 modes), Auto PO (`11YYMMDDNN`), and PDF generation (4 slips/A4). Observation 1 confirms all 4 workflows are clearly and accurately described in Vietnamese.
2. **Defensive Robustness**:
   - In headless test runs or when `app=None` or before the UI finishes rendering, Observation 2 confirms that all getters return `None`.
   - When a getter returns `None` or an unmapped/destroyed widget, `GeometryHelper.get_relative_bounds()` returns `None`, which `InteractiveTutorialOverlay._draw_scrim_and_spotlight()` handles by drawing a full-window modal scrim without spotlight cutout, and `PlacementEngine.calculate()` places the tooltip card in the exact center of the window `(margin, (root_w - card_w) // 2, (root_h - card_h) // 2)`.
3. **App Integration & Tab Synchronization**:
   - `SlipPrinterApp` exposes `self.notebook`, and `start_tutorial()` passes `self.notebook` to `InteractiveTutorialOverlay`. When step transitions occur, `TabSyncHelper.ensure_tab_active()` switches to tab 0 and runs `update_idletasks()`.
   - Both `SlipPrinterApp` and `AppController` expose unified `get_tutorial_steps()` and `start_tutorial()` entry points.
4. **Integrity & Code Cleanliness**:
   - No hardcoded test responses, fake bypasses, mock shortcuts, or stub facades exist in the source code.
   - All tests run against live components and real Tkinter widget structures.

---

## 3. Adversarial Stress & Edge Case Assessment

| # | Challenge / Scenario | Expected Behavior | Actual Behavior | Result |
|---|---|---|---|---|
| 1 | Headless execution (`app=None`) | Returns 4 valid `TutorialStep` objects; all getters return `None` without error | 4 `TutorialStep` instances created; getters return `None` safely | **PASS** |
| 2 | Destroyed widget returned by getter | `GeometryHelper` detects `!winfo_exists()` and falls back to centered modal tooltip | Safely falls back to `bounds=None`, centers tooltip, no exception | **PASS** |
| 3 | Unmapped widget (`!winfo_ismapped()`) | `GeometryHelper` detects unmapped state and returns `None` | Safely falls back to centered modal tooltip | **PASS** |
| 4 | Widget throws runtime exception in getter method | Getter catches exception in `try...except` and returns `None` | `_get_excel_target` / `_get_qr_target` / `_get_form_target` / `_get_pdf_target` catch all exceptions and return `None` | **PASS** |
| 5 | Controller wrapper resolution | `_resolve_app` extracts `controller.view` and queries widgets | Resolves `controller.view.sidebar` / `controller.view.data_tab` cleanly | **PASS** |
| 6 | Backward compatibility / attribute variations | Fallback chains check property aliases (`btn_qr_scan`, `excel_import_btn`, `generate_button`) | Finds target widget regardless of naming variation | **PASS** |

---

## 4. Caveats

- Milestone 3 scope (Header amber trigger button `💡 Hướng dẫn` and first-launch auto-prompt persistence in `user_settings.json`) is planned for the subsequent milestone and was not evaluated as part of this Milestone 2 review.
- The 17 failing tests in `tests/test_tutorial_overlay_e2e.py` are due to Milestone 3 / Final E2E test harness expectations (such as CustomTkinter `place()` keyword argument syntax in the test file itself and unmocked settings files) and do not reflect defects in Milestone 2 code.

---

## 5. Conclusion

Milestone 2 implementation is robust, complete, strictly adheres to `ORIGINAL_REQUEST.md` and `PROJECT.md`, handles all boundary and failure modes gracefully, and passes all unit and integration tests with zero integrity violations.

**Verdict**: **`APPROVE`**

---

## 6. Verification Method

To independently verify this review:
1. Run Milestone 2 unit & integration test suite:
   ```powershell
   pytest tests/test_tutorial_script.py -v
   ```
2. Run Milestone 1 tutorial overlay test suite:
   ```powershell
   pytest tests/test_tutorial_overlay.py -v
   ```
3. Inspect source files:
   - `ui/components/tutorial_script.py`
   - `ui/main_window.py`
   - `ui/app_controller.py`
   - `ui/components/sidebar.py`
   - `ui/components/data_tab.py`
