# 5-Component Handoff Report: User Settings Persistence & Schema Extension

**Agent**: `explorer_m3_2` (Teamwork Explorer)  
**Date**: 2026-08-19  
**Recipient**: `orchestrator_2` / `worker_m3_1`  
**Milestone**: M3 (UI Integration, Trigger Button & Persistence)  
**Detailed Report**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_2\analysis.md`  

---

## 1. Observation

1. **Path Resolution & Isolation (`core/runtime_paths.py`)**:
   - Lines 52–60: `_local_app_data()` resolves `%LOCALAPPDATA%\InPhieuHienVatData` or falls back to `Path.home() / "AppData" / "Local" / "InPhieuHienVatData"`. Environment variable `INPHIEUHIENVAT_DATA_DIR` overrides this for isolated test execution in `tests/conftest.py` (lines 58–68).
   - Lines 127–155: `prepare_runtime_paths()` returns `RuntimePaths` containing `data_dir`. `user_settings.json` lives at `paths.data_dir / "user_settings.json"`.

2. **Existing User Settings Implementation (`ui/main_window.py`)**:
   - Lines 399–423: Current theme persistence:
     ```python
     399:     def _load_theme_setting(self) -> str:
     400:         try:
     401:             settings_path = self.app_state.paths.data_dir / "user_settings.json"
     402:             if settings_path.is_file():
     403:                 data = json.loads(settings_path.read_text(encoding="utf-8"))
     404:                 mode = str(data.get("appearance_mode", "System"))
     405:                 if mode in ("Dark", "Light", "System"):
     406:                     return mode
     407:         except Exception:  # noqa: BLE001
     408:             pass
     409:         return "System"
     410: 
     411:     def _save_theme_setting(self, mode: str) -> None:
     412:         try:
     413:             settings_path = self.app_state.paths.data_dir / "user_settings.json"
     414:             data: dict[str, object] = {}
     415:             if settings_path.is_file():
     416:                 try:
     417:                     data = json.loads(settings_path.read_text(encoding="utf-8"))
     418:                 except Exception:  # noqa: BLE001
     419:                     data = {}
     420:             data["appearance_mode"] = mode
     421:             settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
     422:         except Exception:  # noqa: BLE001
     423:             pass
     ```
   - Lines 432–443: Current `start_tutorial()` launches `InteractiveTutorialOverlay` without passing an `on_finish` callback to persist tutorial completion.
   - Lines 65–68: Startup initialization sets window handlers and update check timer (`self.after(1200, ...)`), but lacks a scheduled hook for first-run tutorial check.

3. **Storage Segregation Across Subsystems**:
   - `core/slip_printer_engine.py` lines 321–337 manages `layout_config.json` (ReportLab coordinate bounding boxes only).
   - `core/po_registry.py` manages `po_registry.db` (SQLite PO records only).
   - `updater/update_delivery.py` and `updater/app_updates.py` manage update JSON metadata.

4. **Test Suite Contract Expectations (`tests/test_tutorial_overlay_e2e.py`)**:
   - Lines 862–921:
     - `test_t1_f8_01_settings_file_creation_with_tutorial_keys` verifies `user_settings.json` contains `has_seen_tutorial` and `auto_suggest_tutorial`.
     - `test_t1_f8_02_default_settings_values` verifies `_load_tutorial_seen_setting()`.
     - `test_t1_f8_03_saving_tutorial_completed_state` verifies `_save_tutorial_seen_setting()`.
     - `test_t1_f8_04_first_launch_prompt_logic` and `test_t1_f8_05_first_launch_prompt_suppressed_when_seen` verify `_should_prompt_first_launch_tutorial()`.
   - Lines 1860–1940: `test_t4_01_first_time_user_full_walkthrough_to_completion` verifies full walkthrough sets `has_seen_tutorial = True` in `user_settings.json`.

---

## 2. Logic Chain

1. **Storage Selection**: Based on Observation 3, `user_settings.json` under `%LOCALAPPDATA%\InPhieuHienVatData` is the dedicated store for user preferences. Storing tutorial completion flags here maintains the Single Responsibility Principle and avoids polluting PDF layout geometry (`layout_config.json`).
2. **Schema Extension**: Based on Observation 4 (`PROJECT.md` & `TEST_INFRA.md`), the schema must support:
   ```json
   {
     "appearance_mode": "System",
     "has_seen_tutorial": false,
     "auto_suggest_tutorial": true
   }
   ```
   - `has_seen_tutorial: bool` tracks whether the tutorial was completed or dismissed with "do not show again".
   - `auto_suggest_tutorial: bool` controls whether the first-launch recommendation prompt pops up automatically.
3. **Atomic Persistence & Fallback**: Based on Observation 2, direct `write_text` risks 0-byte corruption during unexpected termination. Staging the write to `user_settings.json.tmp` followed by `os.replace` guarantees atomic commits on Windows NTFS. Reading with `utf-8-sig` prevents failure when users edit files with Windows Notepad (BOM).
4. **Integration Wiring**:
   - `SlipPrinterApp` must expose `_load_user_settings()`, `_save_user_settings()`, `_load_theme_setting()`, `_save_theme_setting()`, `_load_tutorial_seen_setting()`, `_save_tutorial_seen_setting()`, `_should_prompt_first_launch_tutorial()`, and `_check_first_run_tutorial()`.
   - `SlipPrinterApp.__init__` schedules `self.after(500, self._check_first_run_tutorial)` and `destroy()` cancels it.
   - `start_tutorial()` passes `on_finish=lambda: self._save_tutorial_seen_setting(True)`.
   - `AppController` exposes `is_tutorial_seen()` and `mark_tutorial_seen()`.

---

## 3. Caveats

- **No Caveats**. All required contract methods, path resolution mechanics, test cases, and atomic persistence failure modes have been thoroughly mapped and documented with exact line numbers.

---

## 4. Conclusion

The persistence architecture for user preferences in `InPhieuHienVat` is fully analyzed and designed:
- Store location: `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`.
- Schema: extended with `has_seen_tutorial: bool` (default `False`) and `auto_suggest_tutorial: bool` (default `True`).
- Write safety: atomic temp file + `os.replace` with fallback to direct write.
- Read safety: `utf-8-sig` encoding, corrupt JSON fallback to safe defaults.
- All code proposals with exact line mappings for `ui/main_window.py` and `ui/app_controller.py` are documented in `analysis.md`.

---

## 5. Verification Method

To verify the persistence design and implementation once applied:

1. **Run Unit & Layout Tests**:
   ```bash
   pytest tests/test_ui_layout.py -v
   ```
2. **Run E2E Tutorial Persistence Feature Tests**:
   ```bash
   pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f8" -v
   ```
3. **Run Full Lifecycle User Journey Tests**:
   ```bash
   pytest tests/test_tutorial_overlay_e2e.py -k "test_t4" -v
   ```
4. **Inspect Files**:
   - Verify `ui/main_window.py` contains `_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`, and `_check_first_run_tutorial`.
   - Verify that completing the tutorial updates `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` with `"has_seen_tutorial": true`.
