# BRIEFING — 2026-08-19T10:53:20Z

## Mission
Discover, probe, and draft the complete specification and factory function `build_tutorial_steps(app)` for the Interactive Tutorial Overlay in the Slip Printer Application.

## 🔒 My Identity
- Archetype: teamwork_preview_spec_miner
- Roles: Specification Miner
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m2_1
- Original parent: 48b28a83-49b0-4457-ba30-bc76ebdc88b8
- Milestone: Milestone 2 - Tutorial System & UI Polish

## 🔒 Key Constraints
- Authoritative specification discovery (do not implement production code, read-only/spec design mode).
- Follow Vietnamese UI copy standards for user-friendliness and clarity.
- Ground step definitions in exact widgets from `ui/main_window.py` and `ui/tabs/` components.

## Current Parent
- Conversation ID: 48b28a83-49b0-4457-ba30-bc76ebdc88b8
- Updated: 2026-08-19T10:53:20Z

## Task Summary
- **What to build**: Vietnamese tutorial script and factory function `build_tutorial_steps(app)` for `ui/components/tutorial_overlay.py` / `tutorial_script.py` with 4 complete steps covering Excel import, QR scanning modes, Auto PO & Add, and PDF generation & preview.
- **Success criteria**: Detailed spec table, edge cases, target widget resolution logic, exact attributes for all 4 steps, integration guide.
- **Interface contracts**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `ui/components/tutorial_overlay.py`.
- **Code layout**: `ui/components/tutorial_overlay.py`, `ui/components/tutorial_script.py`, `ui/main_window.py`, `ui/app_controller.py`.

## Key Decisions Made
- All 4 business steps drafted in Vietnamese copy adhering strictly to `ORIGINAL_REQUEST.md` §R2 and `tests/test_tutorial_overlay_e2e.py` Feature 6 assertions.
- Widget getters designed with cascading fallbacks to handle `SlipPrinterApp`, `AppController`, unmapped widgets, and `None` (headless testing).
- Integration plan clearly specifies named widget references to be exposed in `SidebarPanel` and `DataTabPanel`.

## Artifact Index
- `.agents/spec_miner_m2_1/DISPATCH.md` — Dispatch prompt and assignments
- `.agents/spec_miner_m2_1/BRIEFING.md` — Agent briefing and persistent state
- `.agents/spec_miner_m2_1/progress.md` — Progress tracker
- `.agents/spec_miner_m2_1/handoff.md` — Final handoff report
