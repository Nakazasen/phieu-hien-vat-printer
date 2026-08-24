# Handoff Report — Milestone 3 First-Launch Tutorial Prompt & UI Trigger Specification

**Agent**: `spec_miner_m3_1`  
**Working Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m3_1`  
**Milestone**: Milestone 3 — UI Trigger Button, Persistence & First-Launch Prompt  
**Date**: 2026-08-19  

---

## 1. Observation

1. **User Requirement**: In `ORIGINAL_REQUEST.md:29-31` (§R3):
   > "Thêm một nút "💡 Hướng dẫn (Tutorial)" ở vị trí dễ thấy trên màn hình chính (ví dụ: góc trên cùng). Đồng thời, lưu trạng thái vào file cấu hình (ví dụ `layout_config.json` hoặc config riêng) để phần mềm tự động gợi ý chạy tutorial trong lần mở app đầu tiên của người dùng mới."

2. **Project Architecture Contract**: In `PROJECT.md:25, 38-39, 71-77`:
   > - Persistence Layer: `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` stores user preferences including `has_seen_tutorial` and `auto_suggest_tutorial`.
   > - Feature 8: `💡 Hướng dẫn` button on Header bar (#F59E0B Amber) for manual tutorial launch.
   > - Feature 9: `user_settings.json` persistence for `has_seen_tutorial` and first-launch auto-prompt dialog.
   > - Schema:
   > ```json
   > {
   >   "appearance_mode": "System",
   >   "has_seen_tutorial": false,
   >   "auto_suggest_tutorial": true
   > }
   > ```

3. **Current Implementation in `ui/main_window.py`**:
   - `_init_theme_mode()` (`main_window.py:50`, `360-424`) currently loads/saves `appearance_mode` directly from `self.app_state.paths.data_dir / "user_settings.json"`.
   - `start_tutorial()` (`main_window.py:432-442`) creates and starts `InteractiveTutorialOverlay`, but does not currently update `has_seen_tutorial` or hook into a first-launch prompt.
   - Header controls (`main_window.py:118-150`) have `preview_controls` frame with theme selector and update check button, but no `💡 Hướng dẫn` button yet.
   - Post-render jobs: `_drain_job = self.after(150, ...)` and `_update_job = self.after(1200, ...)` exist in `main_window.py:66-67`.

4. **Test Suite Baseline in `tests/test_tutorial_overlay_e2e.py`**:
   - Tier 1 Feature 7 tests (`test_t1_f7_01_header_tutorial_button_rendered` through `05`) expect `💡 Hướng dẫn` button with Amber styling (`#F59E0B`) in header and idempotent launching.
   - Tier 1 Feature 8 tests (`test_t1_f8_01_settings_file_creation_with_tutorial_keys` through `05`) expect `_load_user_settings`, `_save_user_settings`, `_should_prompt_first_launch_tutorial`, and persistence of `has_seen_tutorial=True`.
   - Tier 4 Scenario 1 (`test_t4_01_first_time_user_full_walkthrough_to_completion`) simulates a first-time user seeing the prompt, completing all 4 steps, and persisting `has_seen_tutorial=True`.

---

## 2. Logic Chain

1. **Scheduling & Visual Stability**:
   - Spawning a dialog directly inside `__init__` before the window geometry settles causes visual clipping, layout stuttering, and unmapped widget lookups.
   - In `main_window.py`, `_apply_splitter_width` is called at 120ms, and event queue polling starts at 150ms.
   - Therefore, scheduling the first-launch check at **600ms** via `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)` guarantees that the window is fully mapped, splitters settled, and widgets mapped without UI flicker.

2. **Dialog Options & User Agency**:
   - To align with §R3 and modern desktop UX standards:
     - Primary CTA: `"✨ Bắt đầu hướng dẫn (Khuyên dùng)"` (Amber/Emerald accent) immediately marks `has_seen_tutorial = True` and triggers `self.start_tutorial()`.
     - Secondary CTA: `"Để sau / Bỏ qua"` dismisses the modal.
     - Checkbox: `"Không tự động nhắc lại khi khởi động"` (default checked) updates `has_seen_tutorial = True` / `auto_suggest_tutorial = False` so subsequent launches do not annoy the user.

3. **Headless & Automated Test Safety**:
   - Tests instantiate `SlipPrinterApp` or `AppController` in headless / automated environments. If the first-launch check unconditionally opens a blocking modal, tests will hang or freeze.
   - Checking `os.environ.get("PYTEST_CURRENT_TEST")` or `os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT")` inside `_should_prompt_first_launch_tutorial()` cleanly bypasses the auto-prompt in test suites while allowing unit tests to explicitly invoke the dialog methods.
   - Teardown safety is ensured by canceling `self._tutorial_prompt_job` via `after_cancel` inside `SlipPrinterApp.destroy()`.

4. **Integration with `start_tutorial()` and Persistence**:
   - When the user starts or completes the tutorial (either from the prompt dialog or the header button), `_save_user_settings({"has_seen_tutorial": True})` is executed atomically, preserving other keys like `appearance_mode`.

---

## 3. Caveats

- **No Caveats**: All specifications directly match the requirements in `ORIGINAL_REQUEST.md §R3`, `PROJECT.md`, and the existing architecture in `ui/main_window.py`, `ui/components/tutorial_overlay.py`, and `ui/components/tutorial_script.py`.

---

## 4. Conclusion

The specification report in `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\spec_miner_m3_1\analysis.md` provides complete, unambiguous, and test-safe blueprints for Milestone 3 implementation:
1. **Header Trigger Button**: Amber `#F59E0B` `💡 Hướng dẫn` button in `preview_controls`.
2. **User Settings Persistence**: Unified `user_settings.json` storing `appearance_mode`, `has_seen_tutorial`, and `auto_suggest_tutorial`.
3. **First-Launch Trigger Engine**: 600ms delayed timer with headless/test guards and `destroy()` cancellation.
4. **Onboarding Dialog**: Polished `TutorialPromptDialog` with clear options and non-blocking callbacks.

---

## 5. Verification Method

To verify this specification upon implementation:
1. **Settings Persistence**: Verify `user_settings.json` is created with default `has_seen_tutorial: false`, `auto_suggest_tutorial: true`, and updated to `true` upon tutorial launch/completion.
2. **Header Button**: Verify `SlipPrinterApp` renders `💡 Hướng dẫn` button in header bar across light and dark modes.
3. **Automated Test Suite**: Run `pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f7 or test_t1_f8 or test_t4_01"` to verify all Milestone 3 features pass.
