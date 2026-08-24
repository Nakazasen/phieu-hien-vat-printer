## 2026-08-19T10:29:04Z
You are the Tutorial Overlay Engine Worker (archetype: teamwork_preview_worker).
Read ORIGINAL_REQUEST.md at d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md and PROJECT.md at d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md.
Also read the 3 specialist Explorer handoffs:
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_1\handoff.md
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2\handoff.md
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3\handoff.md

Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m1_1.

Write ownership: You exclusively own and must implement `ui/components/tutorial_overlay.py`.

Mandatory Integrity Warning:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Tasks:
1. Implement `ui/components/tutorial_overlay.py` containing:
   - `TutorialStep` data class (step_id, title, description, target_widget_getter, target_tab_index, tooltip_position).
   - `TooltipCard(ctk.CTkFrame)` with modern CustomTkinter design (title, step badge, description, micro-UX shortcut hint, action button bar: [Bỏ qua], [◀ Quay lại], [Tiếp tục ▶] / [🎉 Hoàn tất]).
   - `PlacementEngine` for responsive 4-directional card placement (bottom, top, right, left) with boundary clamping and overflow flipping.
   - `InteractiveTutorialOverlay` (In-Window Canvas placed on root with 4-Rectangle dark scrim cutout, Emerald glow highlight border, modal mouse event interception, debounced `<Configure>` listener on root window, automatic `ttk.Notebook` tab selection with `update_idletasks()`, keyboard shortcuts `<Escape>`, `<Return>`, `<Left>`, `<Right>`, and clean teardown/unbinding).
2. Run pytest to verify all existing tests and new module functionality pass.
3. Write your complete handoff report to `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m1_1\handoff.md`.
4. When finished, send a message to parent (orchestrator).
