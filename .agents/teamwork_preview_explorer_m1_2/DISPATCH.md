## 2026-08-19T10:25:31Z
You are a Coordinate Geometry & Resize Specialist (archetype: teamwork_preview_explorer).
Read ORIGINAL_REQUEST.md at d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md and PROJECT.md at d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md.
Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2.
Task:
Analyze and formulate the exact coordinate math, DPI scaling handling, window resizing, and tab synchronization for the tutorial engine:
1. Exact calculation of relative coordinates `(x1, y1, x2, y2)` from target widget to root window across different DPI scaling configurations.
2. `<Configure>` event handling on the root window with debounce timer (e.g. 50-100ms) to recalculate spotlight bounds and move tooltip when the user resizes or drags the window.
3. Handling target widgets inside different Notebook tabs (auto switching tabs with `notebook.select()`, `update_idletasks()` synchronization).
4. Fallback behavior when target widget is None, hidden, or not yet mapped.
5. Provide clear, concrete code snippets and technical recommendations for the Worker.
Write your analysis to d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_2\handoff.md.
When finished, send a message to parent.
