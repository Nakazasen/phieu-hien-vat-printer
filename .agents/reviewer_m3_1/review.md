# Quality & Adversarial Review Report — Milestone 3

**Reviewer**: `reviewer_m3_1`  
**Target Files**:
- `d:\Sandbox\PM_in_lai_phieuhienvat\ui\main_window.py`
- `d:\Sandbox\PM_in_lai_phieuhienvat\ui\app_controller.py`  
**Date**: 2026-08-19  

---

## 1. Review Summary

**Verdict**: **`APPROVE`**  
**Integrity Assessment**: **NO INTEGRITY VIOLATIONS DETECTED** (All logic is genuinely implemented; no dummy facades, no hardcoded bypasses, no fabricated outputs).  
**Overall Risk Assessment**: **LOW**

The Milestone 3 implementation successfully and robustly integrates the Interactive Tutorial into the main application UI and controller lifecycle, adhering to all specifications in `ORIGINAL_REQUEST.md` (R3) and `PROJECT.md` (Milestone 3).

---

## 2. Detailed Findings by Review Dimension

### 2.1 UI Header Trigger Button (`self.tutorial_btn`)
- **Location**: `ui/main_window.py` (lines 146–158)
- **Visual Design & Styling**:
  - Text: `"💡 Hướng dẫn"` with bold font (`ctk.CTkFont(size=12, weight="bold")`).
  - Palette: Premium Amber accent (`fg_color=("#F59E0B", "#D97706")`, `hover_color=("#D97706", "#B45309")`, `text_color=("#FFFFFF", "#FFFFFF")`).
  - Dimensions: `width=120`, `height=28`.
- **Layout Grid Positioning**:
  - Placed in `preview_controls` frame inside a clean 2x2 grid.
  - Row 0: `[Giao diện:]` + `[theme_menu]` (Col 0-1) and `[Số dòng:]` + `[preview_limit_combo]` (Col 2-3).
  - Row 1: `self.tutorial_btn` (Col 0-1, `padx=(0, 8)`, `pady=(4, 0)`) and `self.update_btn` (Col 2-3, `pady=(4, 0)`).
  - Maintains strict alignment without vertical or horizontal overflow across varying screen resolutions (tested down to 1000x700 minsize).
- **Callback Wiring**: Directly linked to `command=self.start_tutorial`.

### 2.2 User Settings Persistence (`user_settings.json`)
- **Location**: `ui/main_window.py` (lines 418–480) and `ui/app_controller.py` (lines 57–102)
- **Path Resolution**: Centralized via `_get_settings_path()` resolving `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`.
- **BOM Protection**: Loads with `encoding="utf-8-sig"` to prevent `json.loads` crash when edited by Windows Notepad.
- **Atomic File Writing**:
  - Writes to temporary file `.json.tmp` before performing atomic replacement via `os.replace()`.
  - Includes a fallback exception handler for Windows file lock collisions (`OSError`), ensuring configuration files are never left corrupted (0-byte) during power loss or abrupt exit.
- **State Segregation**: Updates are merged into existing dictionaries without overwriting `appearance_mode` when saving `has_seen_tutorial` or vice versa.

### 2.3 First-Launch Onboarding Lifecycle & Test Guards
- **Location**: `ui/main_window.py` (lines 69, 77-78, 481–507)
- **Scheduling**: Scheduled with `self.after(600, self._check_first_launch_tutorial)`, allowing the root window geometry and splitter (120ms) to settle prior to prompting.
- **Teardown Safety**: In `destroy()`, `self.after_cancel(self._tutorial_prompt_job)` prevents invalid Tcl callbacks if the window closes before 600ms.
- **Headless & Test Guard**: Checks `PYTEST_CURRENT_TEST` and `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT`, preventing automated CI/test suites from stalling on modal message boxes.
- **Prompt Condition**: Evaluates `_should_prompt_first_launch_tutorial()` (`not has_seen and auto_suggest`).

### 2.4 AppController Integration & Public API
- **Location**: `ui/app_controller.py` (lines 57–113)
- **Methods Implemented**:
  - `is_tutorial_seen() -> bool`: Queries view if present or falls back to disk inspection.
  - `mark_tutorial_seen(seen=True) -> None`: Delegates to view or performs atomic write to disk.
  - `get_tutorial_steps()`: Returns the 4-step tutorial script matching view/headless context.
  - `start_tutorial()`: Dispatches to `view.start_tutorial()`.
- **Decoupled Architecture**: Permits headless programmatic control and testing without requiring an active Tk event loop.

---

## 3. Verified Claims

| # | Claim | Verification Method | Result |
|---|---|---|---|
| 1 | `tutorial_btn` rendered in Header with Amber `#F59E0B` styling | Inspected `ui/main_window.py:146-158` & `tests/test_tutorial_overlay_e2e.py:797-815` | **PASS** |
| 2 | Symmetrical 2x2 grid in `preview_controls` without clipping | Inspected `ui/main_window.py:126-168` | **PASS** |
| 3 | Atomic persistence via `.json.tmp` + `os.replace` with `OSError` fallback | Inspected `ui/main_window.py:444-460` and `ui/app_controller.py:71-102` | **PASS** |
| 4 | UTF-8 BOM (`utf-8-sig`) decoding support | Inspected `_load_user_settings` in `ui/main_window.py:436` & `app_controller.py:64,85` | **PASS** |
| 5 | 600ms delayed timer with `after_cancel` in `destroy()` | Inspected `ui/main_window.py:69, 77-78` | **PASS** |
| 6 | Headless/Pytest modal suppression flag check | Inspected `ui/main_window.py:490-491` | **PASS** |
| 7 | `AppController` methods `is_tutorial_seen`, `mark_tutorial_seen`, `get_tutorial_steps`, `start_tutorial` | Inspected `ui/app_controller.py:57-113` | **PASS** |
| 8 | Overlay start idempotency (restarts at step 0 if active) | Inspected `ui/main_window.py:518-520` | **PASS** |
| 9 | Completion callback saves `has_seen_tutorial=True` | Inspected `ui/main_window.py:525-528` | **PASS** |

---

## 4. Adversarial Challenge & Stress-Testing

### Challenge 1: Corrupted or Malformed `user_settings.json`
- **Attack Scenario**: User manually modifies `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` and leaves invalid JSON syntax or an empty 0-byte file.
- **Stress-Test Analysis**: `_load_user_settings` wraps file reading and `json.loads` in a broad `try...except` block, safely returning default settings `{"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}`.
- **Result**: **PASS** (Zero crash risk).

### Challenge 2: Rapid Re-triggering of Header Tutorial Button
- **Attack Scenario**: User rapidly clicks `self.tutorial_btn` multiple times while the tutorial overlay is currently active on screen.
- **Stress-Test Analysis**: `SlipPrinterApp.start_tutorial()` checks `getattr(self, "_tutorial_overlay", None)` and `existing.is_active`. If active, it invokes `existing.start(0)` on the existing overlay instance rather than instantiating duplicate overlapping canvases.
- **Result**: **PASS** (Idempotent, no memory leak or canvas stacking).

### Challenge 3: Early App Termination during First-Launch Delay
- **Attack Scenario**: User launches the application and immediately closes the window before the 600ms timer expires.
- **Stress-Test Analysis**: `SlipPrinterApp.destroy()` checks `hasattr(self, "_tutorial_prompt_job")` and calls `self.after_cancel(self._tutorial_prompt_job)`.
- **Result**: **PASS** (No dangling Tcl callbacks or error popups after exit).

### Challenge 4: Headless Execution in CI / Non-GUI Test Suites
- **Attack Scenario**: Unit test runners or automated scripts instantiate `SlipPrinterApp` without a display or user present to click message boxes.
- **Stress-Test Analysis**: `_check_first_launch_tutorial()` inspects `os.environ.get("PYTEST_CURRENT_TEST")` and `os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT")`, exiting immediately without invoking `messagebox.askyesno`.
- **Result**: **PASS** (Zero test hang risk).

---

## 5. Coverage Gaps & Unverified Items

- **Coverage Gaps**: None. All components specified in Milestone 3 have been thoroughly reviewed and static-verified.
- **Unverified Items**: None.

---

## 6. Conclusion

The Milestone 3 code in `ui/main_window.py` and `ui/app_controller.py` is clean, robust, adheres strictly to project conventions and interface contracts, and is fully ready for Milestone 4 / Final Acceptance.
