## 2026-08-19T10:51:26Z

You are spec_miner_m2_1 (teamwork_preview_spec_miner).
Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m2_1.

MANDATORY FIRST STEP: Read the following files:
1. d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md
2. d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md
3. d:\Sandbox\PM_in_lai_phieuhienvat\ui\components\tutorial_overlay.py
4. d:\Sandbox\PM_in_lai_phieuhienvat\ui\main_window.py
5. d:\Sandbox\PM_in_lai_phieuhienvat\ui\app_controller.py

TASK OBJECTIVES:
Draft the complete, user-friendly Vietnamese tutorial script and factory function `build_tutorial_steps(app)` for `ui/components/tutorial_overlay.py` (or a dedicated `ui/components/tutorial_script.py`):
1. Draft all 4 steps specified in ORIGINAL_REQUEST.md §R2:
   - Step 1: "Nạp dữ liệu từ Excel" (Highlight Excel import widget; explain required columns, data validation, and duplicate checking).
   - Step 2: "Quét mã QR thông minh" (Highlight QR scan button; explain 3 scanning modes: Phân tách, Hoàn kho, Bóc tách).
   - Step 3: "Tạo mã Auto PO & Thêm phiếu" (Tab 0 DataTab; highlight PO entry/auto button and Add button; explain automatic `11YYMMDDNN` PO incrementation).
   - Step 4: "Tạo & In phiếu hiện vật PDF" (Highlight Generate PDF button / Preview; explain 4 slips per A4 page, direct printing & PDF export).
2. Specify exact `TutorialStep` attributes: `step_id`, `title`, `description`, `target_widget_getter`, `target_tab_index`, `tooltip_position`.
3. Provide a clear integration plan for how `SlipPrinterApp` or `AppController` registers and starts these steps.
4. Write your specification handoff to `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m2_1\handoff.md`.
