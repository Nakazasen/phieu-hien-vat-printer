# Milestone 3 Changes Report: UI Integration, First-Launch Trigger & Persistence

**Worker**: `worker_m3_1`  
**Milestone**: Milestone 3  
**Date**: 2026-08-19  
**Target Files Modified**:
1. `d:\Sandbox\PM_in_lai_phieuhienvat\ui\main_window.py`
2. `d:\Sandbox\PM_in_lai_phieuhienvat\ui\app_controller.py`

---

## 1. Summary of Modifications

### 1.1 `ui/main_window.py`
1. **Header Tutorial Button (`self.tutorial_btn`)**:
   - Added `self.tutorial_btn` in `_build_content` within the `preview_controls` frame alongside `self.update_btn`.
   - Applied Amber styling:
     - `text="💡 Hướng dẫn"`
     - `fg_color=("#F59E0B", "#D97706")`
     - `hover_color=("#D97706", "#B45309")`
     - `text_color=("#FFFFFF", "#FFFFFF")`
     - `font=ctk.CTkFont(size=12, weight="bold")`
     - `width=120`, `height=28`
     - `command=self.start_tutorial`
   - Positioned in 2x2 grid in `preview_controls`:
     - Row 0: `[Giao diện:]` + `[theme_menu]` (Col 0-1), `[Số dòng:]` + `[preview_limit_combo]` (Col 2-3)
     - Row 1: `self.tutorial_btn` (Col 0-1, `padx=(0, 8)`, `pady=(4, 0)`), `self.update_btn` (Col 2-3, `pady=(4, 0)`)
2. **Robust User Settings Persistence**:
   - Implemented centralized path resolver: `_get_settings_path(self) -> Path`.
   - Implemented `_load_user_settings(self) -> dict[str, Any]` with `utf-8-sig` BOM handling and robust fallback defaults (`{"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}`).
   - Implemented atomic writer `_save_user_settings(self, updates: dict[str, Any]) -> None` writing via `.json.tmp` + `os.replace` with fallback to direct write on Windows lock exceptions.
   - Refactored `_load_theme_setting(self) -> str` and `_save_theme_setting(self, mode: str) -> None` to use centralized persistence.
   - Implemented `_load_tutorial_seen_setting(self) -> bool` and `_save_tutorial_seen_setting(self, seen: bool = True) -> None`.
3. **First-Launch Prompt Logic & Lifecycle Scheduling**:
   - Implemented `_should_prompt_first_launch_tutorial(self) -> bool` returning True when `has_seen_tutorial == False` and `auto_suggest_tutorial == True`.
   - Implemented `_check_first_launch_tutorial(self) -> None` and alias `_check_first_run_tutorial(self) -> None`, checking test environment guards (`PYTEST_CURRENT_TEST`, `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT`) and displaying an onboarding prompt message box.
   - Scheduled `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)` in `SlipPrinterApp.__init__`.
   - Safely canceled `self.after_cancel(self._tutorial_prompt_job)` in `SlipPrinterApp.destroy()`.
4. **Tutorial Engine Integration**:
   - Implemented `get_tutorial_steps(self=None)` supporting instance or class/static invocation.
   - Implemented `start_tutorial(self)` with idempotency protection (restarts at step 0 if overlay active) and wiring completion callback to `self._save_tutorial_seen_setting(True)`.

### 1.2 `ui/app_controller.py`
1. **Import `json`**: Added `import json` to module header.
2. **Exposed Tutorial Helpers**:
   - `is_tutorial_seen(self) -> bool`: Delegates to `view._load_tutorial_seen_setting()` or directly inspects `user_settings.json`.
   - `mark_tutorial_seen(self, seen: bool = True) -> None`: Delegates to `view._save_tutorial_seen_setting(seen)` or performs atomic disk update to `user_settings.json`.
   - Verified `get_tutorial_steps(self)` and `start_tutorial(self)` for controller-level access.

---

## 2. Interface Contracts and Method Signatures Verified

| Class | Method | Signature | Behavior |
|---|---|---|---|
| `SlipPrinterApp` | `tutorial_btn` | `ctk.CTkButton` | Amber-accented header button launching tutorial |
| `SlipPrinterApp` | `_load_user_settings` | `(self) -> dict[str, Any]` | Returns loaded dict or defaults with `utf-8-sig` |
| `SlipPrinterApp` | `_save_user_settings` | `(self, updates: dict[str, Any]) -> None` | Merges updates, writes atomically via `.tmp` + `os.replace` |
| `SlipPrinterApp` | `_load_theme_setting` | `(self) -> str` | Returns `"Dark"`, `"Light"`, or `"System"` |
| `SlipPrinterApp` | `_save_theme_setting` | `(self, mode: str) -> None` | Persists theme mode without overwriting other keys |
| `SlipPrinterApp` | `_load_tutorial_seen_setting` | `(self) -> bool` | Returns bool `has_seen_tutorial` |
| `SlipPrinterApp` | `_save_tutorial_seen_setting` | `(self, seen: bool = True) -> None` | Persists bool `has_seen_tutorial` |
| `SlipPrinterApp` | `_should_prompt_first_launch_tutorial` | `(self) -> bool` | Returns True if not seen & auto-suggest enabled |
| `SlipPrinterApp` | `_check_first_launch_tutorial` | `(self) -> None` | Scheduled 600ms prompt callback |
| `SlipPrinterApp` | `_check_first_run_tutorial` | `(self) -> None` | Alias for `_check_first_launch_tutorial` |
| `SlipPrinterApp` | `start_tutorial` | `(self) -> InteractiveTutorialOverlay` | Launches overlay and binds `on_finish` to persist seen flag |
| `AppController` | `is_tutorial_seen` | `(self) -> bool` | State query for tutorial completion |
| `AppController` | `mark_tutorial_seen` | `(self, seen: bool = True) -> None` | Persists completion flag |
| `AppController` | `get_tutorial_steps` | `(self) -> list[TutorialStep]` | Returns 4-step tutorial script |
| `AppController` | `start_tutorial` | `(self) -> Any` | Triggers overlay via attached view |
