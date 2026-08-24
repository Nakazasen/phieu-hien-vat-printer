# BRIEFING — 2026-08-19T11:21:10Z

## Mission
Explore `ui/main_window.py` header layout, locate summary/status, theme switch, check button, and design the `💡 Hướng dẫn` (#F59E0B Amber) button placement and callback. Analyze interaction between `SlipPrinterApp` and `AppController`, and produce a detailed analysis report with exact code proposals.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigation, synthesis
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1
- Original parent: cc85c184-3d9f-483d-8142-cde146093bfe
- Milestone: milestone_3 (Interactive Tutorial & Guidance System)

## 🔒 Key Constraints
- Read-only investigation — do NOT implement directly in source code.
- Provide exact line numbers, code snippets, and rationale in analysis.md and handoff.md.

## Current Parent
- Conversation ID: cc85c184-3d9f-483d-8142-cde146093bfe
- Updated: 2026-08-19T11:21:10Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `ui/main_window.py`, `ui/app_controller.py`, `ui/components/tutorial_script.py`, `ui/components/tutorial_overlay.py`, `tests/test_tutorial_overlay_e2e.py`
- **Key findings**:
  1. Header right-side `preview_controls` frame allows a symmetrical 2x2 grid (Row 0: Theme + Limit, Row 1: Tutorial Button + Update Check Button).
  2. `self.tutorial_btn` styled as Amber `fg_color=("#F59E0B", "#D97706")`, `hover_color=("#D97706", "#B45309")`, `width=120`, `height=28`, `font=ctk.CTkFont(size=12, weight="bold")`.
  3. `SlipPrinterApp` persistence methods (`_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`, `_check_first_launch_tutorial`) handle user settings in `user_settings.json` and first-launch auto-prompt.
- **Unexplored areas**: None. Investigation complete.

## Key Decisions Made
- Selected Option 1 (2x2 grid inside `preview_controls`) for optimal responsive layout without resizing jitter.
- Detailed before/after code proposals recorded in `analysis.md` and summarized in `handoff.md`.

## Artifact Index
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1\analysis.md — Detailed analysis and code proposal
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1\handoff.md — 5-component handoff report
