## 2026-08-19T10:55:01Z

You are worker_m2_1 (teamwork_preview_worker).
Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m2_1.

You exclusively own and modify:
- ui/components/tutorial_script.py (create new)
- ui/components/tutorial_overlay.py
- ui/components/sidebar.py
- ui/components/data_tab.py
- ui/main_window.py
- ui/app_controller.py
- tests/test_tutorial_script.py (create new)

MANDATORY FIRST STEP: Read the following files before taking any action:
1. d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md
2. d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md
3. d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m2_1\handoff.md
4. d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m2_1\handoff.md
5. d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m2_2\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

TASK OBJECTIVES:
Implement Milestone 2: Tutorial Script & Business Flow Integration:

1. Create `ui/components/tutorial_script.py`:
   - Implement `build_tutorial_steps(app: Optional[Any] = None) -> list[TutorialStep]` with all 4 steps per `ORIGINAL_REQUEST.md §R2` and `spec_miner_m2_1/handoff.md`:
     * Step 1 (`step_excel_import`): "1. Nạp dữ liệu từ Excel" -> explains required columns, validation, duplicate check; highlights sidebar Excel import button / frame; `target_tab_index=0`.
     * Step 2 (`step_qr_scanner`): "2. Quét mã QR thông minh" -> explains 3 QR modes (Phân tách, Hoàn kho, Bóc tách); highlights QR button on sidebar or data_tab; `target_tab_index=0`.
     * Step 3 (`step_auto_po`): "3. Tạo mã Auto PO & Thêm phiếu" -> explains automatic `11YYMMDDNN` PO incrementing; highlights Form frame / Add button; `target_tab_index=0`.
     * Step 4 (`step_pdf_generation`): "4. Tạo & In phiếu hiện vật PDF" -> explains 4 slips per A4 page, preview, export and direct print; highlights Generate PDF button / preview frame; `target_tab_index=0`.
   - Ensure widget getters handle `app=None` or unmapped widgets safely by returning `None`.

2. In `ui/components/tutorial_overlay.py`:
   - Import and re-export `build_tutorial_steps` from `ui.components.tutorial_script`.

3. In `ui/components/sidebar.py`:
   - Store instance attributes for `self.excel_frame`, `self.excel_entry`, `self.excel_import_button`, `self.qr_scan_button`, `self.generate_button`, `self.open_pdf_button`.
   - Add accessor methods: `get_excel_import_widget()`, `get_excel_path_widget()`, `get_excel_frame_widget()`, `get_qr_scan_widget()`, `get_generate_pdf_widget()`, `get_open_pdf_widget()`.
   - Add compatibility property aliases (`excel_import_btn`, `btn_import_excel`, `qr_scan_btn`, `btn_qr_scan`, `open_pdf_btn`, `btn_open_pdf`).

4. In `ui/components/data_tab.py`:
   - Store instance attributes for `self.btn_qr_scan`, `self.btn_add_record`, `self.btn_update_record`, `self.btn_delete_record`, `self.btn_refresh_preview`.
   - Add accessor methods: `get_form_frame()`, `get_auto_po_widget()`, `get_po_detail_widget()`, `get_po_sub_widget()`, `get_add_button_widget()`, `get_update_button_widget()`, `get_delete_button_widget()`, `get_qr_button_widget()`, `get_treeview_widget()`, `get_table_frame()`, `get_preview_frame()`, `get_preview_image_label()`, `get_qr_payload_box()`, `get_refresh_preview_button()`.

5. In `ui/main_window.py`:
   - In `_build_content()`, assign `self.notebook = notebook`.
   - Add methods `get_tutorial_steps(self)` (returns `build_tutorial_steps(self)`) and `start_tutorial(self)` (instantiates `InteractiveTutorialOverlay(self)` with `build_tutorial_steps(self)` and calls `.start()`).

6. In `ui/app_controller.py`:
   - Add `get_tutorial_steps(self)` (returns `build_tutorial_steps(self.view)` if `self.view` else `build_tutorial_steps(None)`) and `start_tutorial(self)`.

7. Create `tests/test_tutorial_script.py`:
   - Author comprehensive unit tests verifying that `build_tutorial_steps()` returns 4 valid steps with expected IDs, titles, Vietnamese keywords, tab index 0, and that widget getters work correctly on simulated / real app hierarchies and return None when app is None.

VERIFICATION:
Run pytest to verify all tests pass:
- `pytest tests/test_tutorial_overlay.py -v`
- `pytest tests/test_tutorial_script.py -v`
- `pytest tests/test_challenger_m1_overlay_stress.py -v`
- `pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f6" -v`

OUTPUT REQUIREMENTS:
Write your full report to `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m2_1\handoff.md` and send a completion message back.
