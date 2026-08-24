# BRIEFING — 2026-08-19T10:28:00Z

## Mission
Analyze and formulate the exact design and implementation plan for the floating Tooltip Card UI and Step Navigation controller.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: Tooltip UI & Navigation Specialist
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: M1_3 (Interactive Tutorial System - Tooltip UI & Step Navigation)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in production source code.
- Provide comprehensive design, concrete code architecture, edge-case math, and unbinding logic.
- Deliver structured handoff report in handoff.md.

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: 2026-08-19T10:28:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`, `PROJECT.md`
  - `ui/main_window.py`, `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/components/qr_scan_dialog.py`
  - `tests/test_ui_layout.py`, `tests/conftest.py`
  - `python-gui-design` skill guidelines
- **Key findings**:
  - `TooltipCard` layout with 8-point grid, Emerald glowing border (`#10B981`), step badge, and Von Restorff CTA button.
  - PlacementEngine algorithm handling 4 cardinal directions, overflow flipping, boundary clamping, and center modal fallback.
  - Keyboard accessibility bindings (`<Escape>`, `<Return>`, `<KP_Enter>`, `<Right>`, `<Left>`) with event swallowing (`return "break"`).
  - Clean teardown lifecycle canceling `after()` debouncers and unbinding root events.
- **Unexplored areas**: None for M1_3 scope.

## Key Decisions Made
- TooltipCard designed as a modular `ctk.CTkFrame` with dynamic placement via `.place(x, y)`.
- PlacementEngine formulated as a pure calculation utility for simple testing and zero UI side effects.
- Event bindings registered with explicit ID tracking to ensure safe unbinding.

## Artifact Index
- `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3\handoff.md` — Comprehensive analysis and production-ready code snippets.
- `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3\progress.md` — Liveness heartbeat and milestone status.
