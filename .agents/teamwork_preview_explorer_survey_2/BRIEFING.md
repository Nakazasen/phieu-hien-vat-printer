# BRIEFING — 2026-08-19T17:30:00+07:00

## Mission
Survey core business workflows and target widgets for the 4 core tutorial steps (Excel Data Loading, QR Scanner tool & 3 modes, Auto PO creation, PDF generation & printing) in the application codebase.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: Business Workflow Explorer, Read-only investigation
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_survey_2
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: Survey & UI Widget Mapping for Interactive Tutorial

## 🔒 Key Constraints
- Read-only investigation — do NOT implement / modify source code
- Strictly write files only to working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_survey_2
- Evidence chain completeness: exact file paths, line numbers, variable names, widget hierarchy

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: 2026-08-19T17:30:00+07:00

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`
  - `slip_printer_app.py`, `ui/main_window.py`, `ui/app_controller.py`, `ui/app_state.py`
  - `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/components/qr_scan_dialog.py`
  - `ui/components/history_tab.py`, `ui/components/layout_tab.py`
  - `core/slip_printer_engine.py`, `core/po_registry.py`
- **Key findings**:
  - Step 1 (Excel): `sidebar.py:34, 45`, `data_tab.py:177`, OpenXML reading from row 28 (`START_ROW = 28`), duplicate red highlighting via tag `"duplicate"`.
  - Step 2 (QR Scanner): `qr_scan_dialog.py:24-496`, 3 modes (Phân tách `split` -> `10010`..`90010`, Hoàn kho `return` -> `11010`..`91010`, Bóc tách `decode`), 129-char payload slicing & real-time preview.
  - Step 3 (Auto PO): `data_tab.py:86-106`, `po_registry.py:177-234`, Format `11YYMMDDNN` (prefix 11, year, month, day, sequence 01-99), multi-box batch series sharing 1 PO.
  - Step 4 (PDF Generation): `sidebar.py:64, 76`, `data_tab.py:216`, `slip_printer_engine.py:827-1012`, ReportLab overlay + batch merge (500/batch) + 4-label imposition on A4 (2x2 grid) with fitz compression.
- **Unexplored areas**: None. All 4 steps fully mapped with exact widget identifiers, variables, callbacks, and backend logic.

## Key Decisions Made
- Detailed 5-component report written to `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_survey_2\handoff.md`.

## Artifact Index
- DISPATCH.md — Recorded dispatch prompt
- BRIEFING.md — Situational awareness
- progress.md — Liveness & heartbeat
- handoff.md — Comprehensive 5-component report
