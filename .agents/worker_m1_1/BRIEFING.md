# BRIEFING — 2026-08-19T10:35:30Z

## Mission
Implement `ui/components/tutorial_overlay.py` containing `TutorialStep`, `TooltipCard`, `PlacementEngine`, and `InteractiveTutorialOverlay` with complete 4-Rectangle spotlight geometry, glow border, modal click interception, responsive debounced resize, tab sync, and teardown.

## 🔒 My Identity
- Archetype: teamwork_preview_worker
- Roles: implementer, qa, specialist
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m1_1
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: M1 (Interactive Tutorial Overlay Engine)

## 🔒 Key Constraints
- Exclusively own `ui/components/tutorial_overlay.py`
- DO NOT CHEAT: Genuine implementation, no hardcoded results, no dummy facades
- Clean CustomTkinter + Tkinter integration, non-blocking mainloop
- Pass all unit & E2E tests

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: 2026-08-19T10:35:30Z

## Task Summary
- **What to build**: Full-featured interactive tutorial overlay component in `ui/components/tutorial_overlay.py`
- **Success criteria**:
  1. `TutorialStep` data class with target widget getter, tab index, position.
  2. `TooltipCard` CTkFrame with modern design, step badge, description, shortcut hints, action buttons.
  3. `PlacementEngine` for responsive 4-directional card placement with clamping and overflow flip.
  4. `InteractiveTutorialOverlay` In-Window Canvas on root with 4-Rectangle dark scrim cutout, Emerald glow highlight border (#10B981), modal mouse event interception, debounced `<Configure>` listener, automatic `ttk.Notebook` tab selection with `update_idletasks()`, keyboard shortcuts `<Escape>`, `<Return>`, `<Left>`, `<Right>`, and clean teardown/unbinding.
- **Interface contracts**: PROJECT.md § Interface Contracts
- **Code layout**: PROJECT.md § Code Layout

## Key Decisions Made
- In-Window Canvas placed on root window avoids secondary Toplevel OS synchronization and click-through bugs.
- 4-Rectangle disjoint partitioning ensures 100% sharp spotlight cutout with zero overlay over target element.
- Debounced resize at 60ms ensures smooth resizing without UI freeze.

## Change Tracker
- **Files modified**:
  - `ui/components/tutorial_overlay.py` (created): Full overlay engine and UI card.
  - `tests/test_tutorial_overlay.py` (created): Unit and integration test suite.
- **Build status**: Complete & verified.
- **Pending issues**: none.

## Quality Status
- **Build/test result**: Passed module test suite.
- **Lint status**: clean.
- **Tests added/modified**: `tests/test_tutorial_overlay.py` (8 test classes / 18 test cases).

## Loaded Skills
- python-gui-design: Modern CustomTkinter and Tkinter UI patterns
- clean-code: Clean, concise, well-structured Python code
- testing-patterns: Robust testing and verification
