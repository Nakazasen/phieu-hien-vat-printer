# Handoff Report: Milestone 3 Adversarial Challenge & Verification

- **Agent**: `challenger_m3_1` (Roles: critic, specialist)
- **Target**: Milestone 3 — UI Integration, Header Trigger, Persistence & First-Launch Prompt
- **Date**: 2026-08-19
- **Type**: Hard Handoff (Task Complete)
- **Verdict**: **APPROVE**

---

## 1. Observation

1. **Header Trigger Button**:
   - Location: `ui/main_window.py:146-158`
   - Rendered as `self.tutorial_btn = ctk.CTkButton(preview_controls, text="💡 Hướng dẫn", width=120, height=28, font=ctk.CTkFont(size=12, weight="bold"), fg_color=("#F59E0B", "#D97706"), hover_color=("#D97706", "#B45309"), text_color=("#FFFFFF", "#FFFFFF"), command=self.start_tutorial)`.
   - Placed in `preview_controls` on Header bar with amber styling and direct binding to `self.start_tutorial`.

2. **User Settings Persistence & Fault Tolerance**:
   - Location: `ui/main_window.py:418-486`, `ui/app_controller.py:57-102`
   - `_load_user_settings()`: Reads `user_settings.json` using `encoding="utf-8-sig"`. Checks `isinstance(loaded, dict)` and returns defaults (`has_seen_tutorial=False`, `appearance_mode="System"`, `auto_suggest_tutorial=True`) if file is missing, empty, truncated, non-dict, or corrupted.
   - `_save_user_settings()`: Performs atomic save via temporary file (`.json.tmp`) and `os.replace`. Includes fallback direct write and `temp_path.unlink(missing_ok=True)` on `OSError`.
   - `AppController.is_tutorial_seen()` & `AppController.mark_tutorial_seen()`: Synchronized with `_load_tutorial_seen_setting()` and `_save_tutorial_seen_setting()` when view is attached, or directly writes/reads atomically in headless mode.

3. **Overlay Idempotency & Re-entrancy**:
   - Location: `ui/main_window.py:515-539`
   - `start_tutorial()`: Checks `existing = getattr(self, "_tutorial_overlay", None)`. If `existing is not None and getattr(existing, "is_active", False)`, invokes `existing.start(0)` to reset active tutorial to Step 0 instead of duplicating canvas layers.
   - Sets `_on_finish` callback to automatically invoke `self._save_tutorial_seen_setting(True)` and log `"Đã hoàn tất xem hướng dẫn sử dụng."`.

4. **Timer Management & `destroy()` Cleanup**:
   - Location: `ui/main_window.py:67-79`
   - Scheduled timers tracked:
     - `self._drain_job = self.after(150, self._drain_event_queue)`
     - `self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))`
     - `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)`
   - `destroy()` cancels all three timers using `self.after_cancel(...)` before calling `super().destroy()`.

5. **First-Launch Prompt Suppression**:
   - Location: `ui/main_window.py:488-507`
   - Suppresses dialog popup when `PYTEST_CURRENT_TEST` or `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT` is set.
   - Evaluates `(not has_seen) and auto_suggest`. If confirmed, launches `self.start_tutorial()`.

6. **Adversarial Stress Test Suite**:
   - Created `tests/test_challenger_m3_stress.py` containing 25 comprehensive test cases covering corrupt JSON syntax, empty files, random bytes, UTF-8 BOM, non-dict JSON types, missing keys, IO error fallbacks, 100 rapid save merges, 50 rapid start clicks, immediate 0ms `destroy()`, 50 consecutive `destroy()` calls, state transition cycles, and prompt truth tables.

---

## 2. Logic Chain

1. **Robust Persistence & Fault Handling**:
   - *Observation 2* demonstrates that `_load_user_settings` and `_save_user_settings` handle corrupt syntax, 0-byte files, random binary bytes, UTF-8 BOM, and invalid non-dict payloads by falling back to default values without raising unhandled exceptions.
   - *Observation 2* demonstrates atomic writes with `os.replace` and fallback error handling, preventing data corruption during concurrent or interrupted write operations.

2. **UI Stability & Idempotent Navigation**:
   - *Observation 1 & 3* show that the `💡 Hướng dẫn` Header button is accessible, styled consistently in Amber (`#F59E0B`), and wired to `start_tutorial()`.
   - *Observation 3* verifies that repeated clicks or re-launching mid-walkthrough safely resets the active overlay to Step 0 without creating multiple canvases, widget collisions, or memory leaks.

3. **Lifecycle Cleanliness & Zero Timer Leaks**:
   - *Observation 4* shows that all asynchronous timer callbacks (`_drain_job`, `_update_job`, `_tutorial_prompt_job`) are tracked and cancelled in `destroy()`.
   - *Observation 4 & 6* demonstrate that immediate `destroy()` (0ms) or consecutive `destroy()` invocations do not leave orphaned timers or raise `TclError`.

4. **State Machine & First-Launch Consistency**:
   - *Observation 2, 5 & 6* demonstrate that state transitions (`False -> True -> False -> True`) persist accurately across sessions and headless controller instances.
   - Completing the 4-step walkthrough automatically persists `has_seen_tutorial: True`, preventing unwanted prompts on subsequent launches while keeping the manual Header button functional.

---

## 3. Caveats

- In headless test environments lacking an active X11/Win32 display server, tests relying on live Tk window rendering require `xvfb` or Tk display fallback, which is handled gracefully by pytest fixtures.
- The first-launch onboarding prompt uses native `tkinter.messagebox.askyesno`, which is bypassed in automated test runs via the `PYTEST_CURRENT_TEST` environment variable.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- **Assessment**:
  The Milestone 3 implementation satisfies all requirements (R3) from `ORIGINAL_REQUEST.md` and fulfills the architecture and interface contracts in `PROJECT.md`. It has been thoroughly stress-tested against hostile inputs, file-system IO errors, rapid UI interactions, and lifecycle boundary conditions with zero failures.

---

## 5. Verification Method

To independently verify the Milestone 3 implementation and stress tests:

```bash
# 1. Run the dedicated Milestone 3 adversarial stress test suite
pytest tests/test_challenger_m3_stress.py -v

# 2. Run the full tutorial E2E test suite (Tiers 1-4)
pytest tests/test_tutorial_overlay_e2e.py -v

# 3. Run the tutorial script content and accessor tests
pytest tests/test_tutorial_script.py -v

# 4. Run the UI layout and theme persistence tests
pytest tests/test_ui_layout.py -v
```

### Invalidation Conditions
- Any `json.JSONDecodeError` or unhandled exception raised when `user_settings.json` contains malformed bytes or non-dict payloads.
- Any crash or multiple overlapping canvas instances when clicking `💡 Hướng dẫn` repeatedly.
- Any `TclError: bad window path` or orphaned callback firing after `destroy()` is called.
