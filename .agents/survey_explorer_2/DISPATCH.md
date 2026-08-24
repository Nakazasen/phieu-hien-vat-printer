## 2026-08-19T08:01:06Z

You are survey_explorer_2, an exploration subagent.
Your working directory is: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\survey_explorer_2
Your parent is orchestrator_pkg (conv ID: 496a12d8-5a64-4409-b089-6abdc4ab595d).

You must first read the user request at:
`d:\Sandbox\PM_in_lai_phieuhienvat\.agents\ORIGINAL_REQUEST.md`

Task:
Deeply inspect the target project `D:\Sandbox\PM_in_lai_phieuhienvat`:
1. Map the codebase structure, entry points (`main.py`, `app.py`, etc.), core modules, UI views, controllers, and models.
2. Inspect the UI framework and main event loop: how Tkinter / UI runs, how background threads dispatch events or call `after()`, how dialogs/messageboxes are handled.
3. Check versioning: how the application currently tracks its version (e.g., `__version__`, constants, config files), or where version metadata should be defined.
4. Check network storage configurations: inspect `po_registry.py` and other modules for network share paths (such as `\\fstvn01\Data\...`), credentials/timeouts, and determine the standard network location for updater releases.
5. Identify all assets, templates, icons, databases, and dependencies needed for packaging into a standalone executable.
6. Survey existing tests and test runner setups.

Document all findings with concrete file paths, code references, and architecture details in your handoff report at:
`d:\Sandbox\PM_in_lai_phieuhienvat\.agents\survey_explorer_2\handoff.md`
Maintain `progress.md` in your working directory.
When finished, send a completion message back to your parent.
