# Handoff Report: Milestone 3 Header Trigger Button & Tutorial Architecture

**Agent**: `explorer_m3_1`  
**Handoff Type**: Hard (Investigation & Design Complete)  
**Date**: 2026-08-19  
**Working Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1`  

---

## 1. Observation

1. **`ui/main_window.py` Header Layout**:
   - `_build_content(self, parent: ctk.CTkFrame)` at lines 103–150 creates:
     - `header = ctk.CTkFrame(parent, fg_color="transparent")` at row 0, col 0 (`padx=16, pady=(10, 4)`).
     - Left area (Col 0, weight=1):
       - Row 0: `CTkLabel(header, textvariable=self.app_state.summary_var, font=CTkFont(size=20, weight="bold"))` (lines 111–113)
       - Row 1: `CTkLabel(header, textvariable=self.app_state.status_var, font=CTkFont(size=12), text_color=("gray40", "gray60"))` (lines 114–116)
     - Right area `preview_controls = ctk.CTkFrame(header, fg_color="transparent")` at row 0, col 1, rowspan 2, sticky="e" (lines 118–150):
       - Row 0: `CTkLabel("Giao diện:")` + `self.theme_menu` (width=115) + `CTkLabel("Số dòng:")` + `CTkComboBox` (width=75)
       - Row 1: `CTkButton(text="Kiểm tra bản cập nhật", width=150, height=28)` gridded at `row=1, column=0, columnspan=4, sticky="e", pady=(4, 0)`.

2. **`ui/app_controller.py` Integration**:
   - `AppController` at lines 56–65 defines:
     - `get_tutorial_steps(self)`: delegates to `ui.components.tutorial_script.build_tutorial_steps(self.view if self.view else None)`.
     - `start_tutorial(self)`: calls `self.view.start_tutorial()` if view is present and has the method.

3. **`ui/main_window.py` Tutorial Methods & Settings**:
   - Lines 425–443 define initial `get_tutorial_steps()` and `start_tutorial()`.
   - Lines 400–424 define `_load_theme_setting()` and `_save_theme_setting()`, storing to `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`.

4. **`tests/test_tutorial_overlay_e2e.py` Interface Expectations**:
   - Lines 797–857 test Feature 7 (Header button rendered, amber styling `#F59E0B` / warm accent, triggers tutorial start, idempotent re-launch).
   - Lines 859–921 test Feature 8 (Persistence in `user_settings.json`, `_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`).

---

## 2. Logic Chain

1. **Grid Compatibility**:
   - In `preview_controls`, Row 0 uses columns 0, 1, 2, 3 with total width ≈ 315px.
   - Row 1 currently uses `columnspan=4` for the 150px update button.
   - By dividing Row 1 into `columns 0-1` (`self.tutorial_btn`, width=120px) and `columns 2-3` (`self.update_btn`, width=150px), both buttons sit side-by-side with total width 278px ≤ 315px.
   - This creates a clean, symmetrical 2x2 control matrix aligned to the right margin (`sticky="e"`), avoiding any resizing jitter or overlap with the Summary title on minimum window sizes (1000px).

2. **CustomTkinter Styling**:
   - Using `fg_color=("#F59E0B", "#D97706")` (Amber 500/600) and `hover_color=("#D97706", "#B45309")` satisfies the Amber accent requirement specified in `PROJECT.md` §8 and `ORIGINAL_REQUEST.md` §R3.
   - Setting `font=ctk.CTkFont(size=12, weight="bold")`, `text_color=("#FFFFFF", "#FFFFFF")`, `height=28`, and `corner_radius=6` matches the exact visual theme of the application.

3. **Controller & View Separation**:
   - `self.tutorial_btn` binds `command=self.start_tutorial`.
   - `AppController.start_tutorial()` delegates to `self.view.start_tutorial()`.
   - Calling `start_tutorial()` checks `_tutorial_overlay.is_active` to safely restart without leaking Tk event handlers.
   - Completing the walkthrough triggers `_on_tutorial_finished()`, which calls `_save_tutorial_seen_setting(True)` and logs completion.

4. **Persistence & First-Launch Logic**:
   - `_should_prompt_first_launch_tutorial()` returns `True` only when `has_seen_tutorial` is `False` and `auto_suggest_tutorial` is `True`.
   - Scheduled via `self.after(600, self._check_first_launch_tutorial)` so it runs after full UI layout stabilization.
   - Safe cancellation is handled in `destroy()` via `self.after_cancel(self._tutorial_job)`.

---

## 3. Caveats

1. **No direct code edit in worker phase**: As explorer, no source files were modified. Full drop-in patches are provided in `analysis.md` for implementer execution.
2. **Dialog modal during headless CI**: In non-interactive test runs, Tkinter messageboxes (`messagebox.askyesno`) must be mocked or handled gracefully as already done in `test_tutorial_overlay_e2e.py`.

---

## 4. Conclusion

1. The proposed 2x2 grid placement in `preview_controls` (lines 142–150 of `ui/main_window.py`) provides the cleanest, most responsive layout for `self.tutorial_btn`.
2. The Amber styling (`fg_color=("#F59E0B", "#D97706")`, `hover_color=("#D97706", "#B45309")`, `text="💡 Hướng dẫn"`) fully complies with `ORIGINAL_REQUEST.md` and `PROJECT.md`.
3. The persistence helpers (`_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`, `_check_first_launch_tutorial`) and lifecycle hooks in `__init__` / `destroy` fulfill all Milestone 3 requirements and unblock full E2E test passage.

---

## 5. Verification Method

1. **Inspect Artifacts**:
   - Read `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1\analysis.md` for exact before/after code blocks and line numbers.
2. **Test Command (once implemented)**:
   ```powershell
   pytest tests/test_tutorial_overlay_e2e.py -k "f7 or f8" -v
   pytest tests/test_tutorial_overlay_e2e.py -v
   ```
3. **Invalidation Condition**:
   - If `test_t1_f7_01_header_tutorial_button_rendered` or `test_t1_f8_02_default_settings_values` fails or skips after applying the proposed changes.
