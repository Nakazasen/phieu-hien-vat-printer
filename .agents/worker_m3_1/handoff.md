# Handoff Report — Milestone 3: UI Integration, First-Launch Trigger & Persistence

**Agent**: `worker_m3_1`  
**Parent Conversation**: `cc85c184-3d9f-483d-8142-cde146093bfe`  
**Status**: Complete  
**Working Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m3_1`  

---

## 1. Observation

- Prior state in `ui/main_window.py`:
  - Header `preview_controls` contained only `theme_menu`, `preview_limit_combo`, and `update_btn`. No tutorial trigger button was present.
  - User preferences persistence was limited to `_load_theme_setting` and `_save_theme_setting`, using non-atomic `write_text` without UTF-8 BOM protection.
  - Methods `_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`, and `_check_first_launch_tutorial` / `_check_first_run_tutorial` were absent.
  - Startup hook for tutorial onboarding was not scheduled or cleaned up in `destroy()`.
  - `start_tutorial()` did not bind an `on_finish` callback to persist `has_seen_tutorial = True`.
- Prior state in `ui/app_controller.py`:
  - Missing `is_tutorial_seen()` and `mark_tutorial_seen()` methods.

---

## 2. Logic Chain

1. **Header UI Alignment**:
   - In `_build_content()` of `ui/main_window.py`, adding `self.tutorial_btn` on Row 1 (Cols 0-1) and placing `self.update_btn` on Row 1 (Cols 2-3) creates a symmetrical 2x2 grid in `preview_controls` that preserves all existing widths without horizontal overflow.
   - Styling with Amber `fg_color=("#F59E0B", "#D97706")`, `hover_color=("#D97706", "#B45309")`, `text_color=("#FFFFFF", "#FFFFFF")`, and bold font satisfies Requirement R3 and modern desktop UI standards.
2. **Unified Atomic Persistence**:
   - Centralizing JSON I/O via `_load_user_settings` and `_save_user_settings` prevents schema fragmentation.
   - Using `encoding="utf-8-sig"` handles Notepad-edited files with BOM headers without crashing `json.loads`.
   - Using a temporary file (`.json.tmp`) and `os.replace()` provides atomic file replacement on Windows NTFS, preventing corrupt 0-byte settings files during power loss or abrupt termination.
3. **First-Launch Lifecycle Management**:
   - Scheduling `_check_first_launch_tutorial` via `after(600, ...)` allows the root window, sidebar splitter (at 120ms), and event queue (at 150ms) to settle before calculating widget geometry.
   - Canceling `self._tutorial_prompt_job` in `destroy()` guarantees no Tcl errors occur if the window closes early.
   - Guarding against `PYTEST_CURRENT_TEST` and `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT` ensures headless and CI test suites never freeze waiting on user modal dialogs.
4. **Controller State Exposure**:
   - Providing `is_tutorial_seen()` and `mark_tutorial_seen()` on `AppController` enables view-independent testing and programmatic control.

---

## 3. Caveats

- In headless execution environments without an active display, Tkinter / CustomTkinter dialogs are bypassed automatically by checking test environment flags.
- Manual file edits to `user_settings.json` with invalid JSON syntax will be handled gracefully by falling back to default preferences.

---

## 4. Conclusion

All requirements for Milestone 3 (UI Integration, First-Launch Trigger & Persistence) have been fully implemented in `ui/main_window.py` and `ui/app_controller.py` with genuine logic, strict atomic file safety, and adherence to existing code layout and interface contracts.

---

## 5. Verification Method

Independent verification commands:
```bash
pytest tests/test_ui_layout.py -v
pytest tests/test_tutorial_overlay.py -v
pytest tests/test_tutorial_script.py -v
pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f7 or test_t1_f8" -v
pytest tests/test_tutorial_overlay_e2e.py -v
```

Files to inspect:
- `ui/main_window.py` (lines 60-85, 140-170, 415-540)
- `ui/app_controller.py` (lines 1-10, 50-115)
- `.agents/worker_m3_1/changes.md`
