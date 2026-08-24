# BRIEFING — 2026-08-19T10:28:45Z

## Mission
Analyze and formulate coordinate geometry, DPI handling, window resizing, debounce mechanism, tab synchronization, and fallback behaviors for the interactive tutorial engine.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: Coordinate Geometry & Resize Specialist
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: m1_coordinate_geometry_and_resize

## 🔒 Key Constraints
- Read-only investigation — do NOT implement source code in project src/
- Synthesize findings into handoff.md with 5-section protocol
- Provide concrete math formulas and robust code snippets for Worker implementation

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: 2026-08-19T10:28:45Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `PROJECT.md`, `ui/main_window.py`, `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/components/layout_tab.py`, `scripts/verify_ui_resize.py`.
- **Key findings**:
  1. Coordinate calculation uses relative projection `(target.winfo_rootx() - root.winfo_rootx())` which maps 1:1 to canvas pixel space across all DPI scaling settings.
  2. Window `<Configure>` requires origin filtering (`event.widget == master_window`) and an 80ms `after_cancel` debounce timer to eliminate resize stutter.
  3. Notebook tab switching requires `notebook.select()`, immediate `root.update_idletasks()`, and a 25ms micro-frame stabilization before spotlight rendering.
  4. Complete fallback handling matrix formulated for `None`, unmapped, zero-size, or off-screen widgets (Modal Card Mode + Center Tooltip).
  5. 4-rectangle scrim math + Emerald highlight border + smart 4-quadrant tooltip placement (`auto`, `bottom`, `top`, `left`, `right`) fully specified with ready-to-use Python code.
- **Unexplored areas**: None. Investigation complete.

## Key Decisions Made
- Formulated `GeometryHelper`, `DebounceManager`, `TabSyncHelper`, `SpotlightRenderer` classes ready for direct adoption by Worker in M1.

## Artifact Index
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2\handoff.md — Complete technical handoff report
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2\progress.md — Progress heartbeat
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2\DISPATCH.md — Dispatch log
