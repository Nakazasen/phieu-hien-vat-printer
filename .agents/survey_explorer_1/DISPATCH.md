## 2026-08-18T05:11:10Z

<USER_REQUEST>
You are survey_explorer_1 (Role: Import & Path Inspector).
Target Workspace: D:\Sandbox\PM_in_lai_phieuhienvat
Original User Request: D:\Sandbox\PM_in_lai_phieuhienvat\.agents\ORIGINAL_REQUEST.md

Mission:
1. Read ORIGINAL_REQUEST.md and inspect all files in the project workspace (D:\Sandbox\PM_in_lai_phieuhienvat).
2. Examine all Python modules in core/, ui/, updater/, installer/, tests/, and root scripts (slip_printer_app.py, package_app.py, build_exe.py, inspect_excel.py, inspect_excel_fast.py, InPhieuHienVat.spec).
3. Check all `import` and `from ... import ...` statements across the entire codebase to detect:
   - Broken imports (modules moved during refactor, renamed classes/functions/variables, missing __init__.py files)
   - Relative vs absolute import mismatches (e.g. sys.path assumptions)
   - Dynamic imports or __import__ / importlib references
   - Circular imports
4. Check all file path references across the codebase:
   - Resource assets: `app_icon.ico`, `template.pdf`, `layout_config.json`, `release.json`, `po_registry.db`, `update_sources.default.json`
   - PyInstaller bundle resource resolution (sys._MEIPASS / frozen app handling)
   - Relative paths vs absolute paths in config, logger, updater, pdf generator, excel parser
5. Run static verification or python import checks if appropriate.
6. Produce a structured handoff report detailing:
   - All modules examined
   - Any broken or suspicious imports found (exact file and line)
   - Any broken or fragile path references found (exact file and line)
   - Fix recommendations with exact before/after code snippets
7. Send your completion message back to parent with the report summary and artifact path.
</USER_REQUEST>
