## 2026-08-19T10:25:32Z
You are a Tooltip UI & Navigation Specialist (archetype: teamwork_preview_explorer).
Read ORIGINAL_REQUEST.md at d:\Sandbox\PM_in_lai_phieuhienvat\ORIGINAL_REQUEST.md and PROJECT.md at d:\Sandbox\PM_in_lai_phieuhienvat\PROJECT.md.
Your working directory is d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3.
Task:
Analyze and formulate the exact design and implementation plan for the floating Tooltip Card UI and Step Navigation controller:
1. `CTkFrame` card layout: Title with icon, Step badge (e.g. `Bước 1 / 4`), descriptive body text, action button bar.
2. Navigation buttons: [◀ Quay lại], [Tiếp tục ▶] / [🎉 Hoàn tất], and [Bỏ qua (Skip)].
3. Intelligent tooltip placement logic (calculating whether to place tooltip below, above, left, or right of the spotlight based on root window boundaries and available screen space).
4. Keybindings: `Escape` to skip/close, `Return` / `Right` to advance step, `Left` to go back.
5. Clean destruction & unbinding logic to ensure zero dangling handlers, timers, or memory leaks on finish/skip.
6. Provide clear, concrete code snippets and technical recommendations for the Worker.
Write your analysis to d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_3\handoff.md.
When finished, send a message to parent.
