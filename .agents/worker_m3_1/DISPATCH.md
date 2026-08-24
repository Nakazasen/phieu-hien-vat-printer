## 2026-08-19T11:21:20Z
Implement Milestone 3: UI Integration, First-Launch Trigger & Persistence:
1. In `ui/main_window.py`:
   - In `_build_content` (`preview_controls` frame), add the `💡 Hướng dẫn` CTkButton (`self.tutorial_btn`) with Amber styling (`fg_color=("#F59E0B", "#D97706")`, `hover_color=("#D97706", "#B45309")`, `font=ctk.CTkFont(size=12, weight="bold")`, `command=self.start_tutorial`). Position it cleanly alongside the update check button.
   - Implement robust JSON user settings persistence functions:
     * `_load_user_settings(self) -> dict[str, Any]`
     * `_save_user_settings(self, updates: dict[str, Any]) -> None` (with atomic write via `.tmp` + `os.replace` and `utf-8-sig` compatibility)
     * `_load_theme_setting(self) -> str`
     * `_save_theme_setting(self, mode: str) -> None`
     * `_load_tutorial_seen_setting(self) -> bool`
     * `_save_tutorial_seen_setting(self, seen: bool = True) -> None`
     * `_should_prompt_first_launch_tutorial(self) -> bool`
     * `_check_first_launch_tutorial(self) -> None` (or `_check_first_run_tutorial(self) -> None`)
   - In `__init__`, schedule `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)` and in `destroy()`, safely cancel `self.after_cancel(self._tutorial_prompt_job)`.
   - Update `start_tutorial(self)` to pass `on_finish=lambda: self._save_tutorial_seen_setting(True)`.
2. In `ui/app_controller.py`:
   - Expose helper methods: `is_tutorial_seen() -> bool`, `mark_tutorial_seen(seen: bool = True) -> None`, `get_tutorial_steps()`, `start_tutorial()`.
3. Verification:
   - Run tests:
     `pytest tests/test_ui_layout.py -v`
     `pytest tests/test_tutorial_overlay.py -v`
     `pytest tests/test_tutorial_script.py -v`
     `pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f7 or test_t1_f8" -v`
     `pytest tests/test_tutorial_overlay_e2e.py -v`
   - Ensure all tests pass.
