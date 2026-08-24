# BRIEFING — 2026-08-19T08:06:30Z

## Mission
Deep exploration and codebase survey of PM_in_lai_phieuhienvat for packaging, updater, network paths, Tkinter architecture, versioning, assets, and tests.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey_explorer_2, read-only investigator, synthesis
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\survey_explorer_2
- Original parent: 496a12d8-5a64-4409-b089-6abdc4ab595d
- Milestone: milestone-1-survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement code changes in the main project
- Document findings rigorously with exact paths and lines in handoff.md

## Current Parent
- Conversation ID: 496a12d8-5a64-4409-b089-6abdc4ab595d
- Updated: 2026-08-19T08:06:30Z

## Investigation State
- **Explored paths**:
  - Entry points: `slip_printer_app.py`, `updater/update_launcher.py`
  - Core engine: `core/runtime_paths.py`, `core/po_registry.py`, `core/slip_printer_engine.py`
  - UI components: `ui/main_window.py`, `ui/app_controller.py`, `ui/app_state.py`, `ui/components/data_tab.py`, `ui/components/sidebar.py`, `ui/components/history_tab.py`, `ui/components/layout_tab.py`, `ui/components/qr_scan_dialog.py`
  - Updater: `updater/app_updates.py`, `updater/update_delivery.py`, `updater/update_security.py`
  - Packaging & Metadata: `package_app.py`, `installer/InPhieuHienVat.iss`, `release.json`, `update_sources.default.json`, `layout_config.json`, `requirements.txt`, `pytest.ini`, `docs/ONBOARDING.md`
  - Test suites: `tests/test_po_registry.py`, `tests/test_engine.py`, `tests/test_import_duplicate_check.py`, `tests/test_runtime_paths.py`, `tests/test_updater.py`, `tests/test_qr_operations.py`
- **Key findings**:
  1. Entrypoint `slip_printer_app.py` supports CLI `--health-check` and `--wait-for-pid` for smooth launcher transition.
  2. UI runs CustomTkinter + sv_ttk with event queue draining every 150ms (`_drain_event_queue()`) for thread safety.
  3. Single Source of Truth for version is `release.json` (currently `0.1.1`), enforced to match `installer/InPhieuHienVat.iss`.
  4. Shared DB path configured at `\\fstvn01\Data\...\db\po_registry.db` with DELETE journal mode (safe for UNC) and 4-tier fallback to AppData.
  5. Auto-updater release source configured at `\\fstvn01\Data\...\release_update` with transactional staging and anti-Zip-Slip validation.
  6. Bundled assets: `template.pdf`, `layout_config.json`, `release.json`, `update_sources.default.json`, `app_icon.ico`. User data in `%LOCALAPPDATA%\InPhieuHienVatData`.
  7. Test suite is comprehensive with fixtures for Tkinter stability and AppData isolation.
- **Unexplored areas**: None. Full survey complete.

## Key Decisions Made
- Completed full mapping and structured findings into 5-component report in `handoff.md`.

## Artifact Index
- `DISPATCH.md` — Dispatch log
- `BRIEFING.md` — Persistent working memory
- `progress.md` — Liveness & step progress
- `handoff.md` — Comprehensive findings report
