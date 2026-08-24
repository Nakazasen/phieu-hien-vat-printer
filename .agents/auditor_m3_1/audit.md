# Forensic Audit Report — Milestone 3

**Work Product**: Milestone 3 UI Integration, Persistence & First-Launch Prompt (`ui/main_window.py`, `ui/app_controller.py`, `tests/test_ui_layout.py`, `tests/test_tutorial_overlay_e2e.py`, `tests/test_tutorial_script.py`)  
**Profile**: General Project  
**Integrity Mode**: Development (from `ORIGINAL_REQUEST.md`)  
**Auditor**: `auditor_m3_1`  
**Date**: 2026-08-19  
**Verdict**: **CLEAN**

---

## 1. Executive Summary

Milestone 3 was audited for code authenticity, genuine functionality, absence of prohibited patterns (facades, dummy mocks in production, hardcoded passes, self-certifying tests), and architectural adherence to `ORIGINAL_REQUEST.md` and `PROJECT.md`.

All inspected methods and components in `ui/main_window.py` and `ui/app_controller.py` implement genuine production logic with robust error handling, UTF-8 BOM resilience, atomic disk persistence, and safe GUI lifecycle management.

---

## 2. Forensic Phase Results

### Phase 1: Static Code Analysis & Prohibited Pattern Detection

| Check # | Forensic Check Description | Target Files | Status | Observations / Evidence |
|---|---|---|:---:|---|
| **1.1** | **Hardcoded Test Output Detection** | `ui/main_window.py`, `ui/app_controller.py`, `tests/` | **PASS** | No hardcoded PASS/FAIL flags, mock return traps, or dummy result strings detected. |
| **1.2** | **Facade Implementation Detection** | `ui/main_window.py`, `ui/app_controller.py` | **PASS** | All required methods (`_load_user_settings`, `_save_user_settings`, `_load_tutorial_seen_setting`, `_save_tutorial_seen_setting`, `_should_prompt_first_launch_tutorial`, `start_tutorial`, `is_tutorial_seen`, `mark_tutorial_seen`) contain genuine algorithmic logic and disk operations. |
| **1.3** | **Fabricated Verification Artifacts** | Entire workspace | **PASS** | No pre-fabricated test logs or synthetic attestation artifacts found. |
| **1.4** | **Self-Certifying Test Anti-Pattern** | `tests/test_ui_layout.py`, `tests/test_tutorial_overlay_e2e.py` | **PASS** | Tests construct real Tk/CTk widgets, exercise live file I/O against temporary paths, and verify real geometry bounds and JSON state mutations. |
| **1.5** | **Execution Delegation (Thin Wrapper)** | `ui/` components | **PASS** | Native in-window implementation built with Tkinter / CustomTkinter without relying on external GUI automation binaries or fake wrappers. |

---

### Phase 2: Component Verification & Logic Depth

#### 2.1 Header Tutorial Trigger Button (`self.tutorial_btn`)
- **Location**: `ui/main_window.py` (lines 146–157)
- **Code Inspection**:
  ```python
  self.tutorial_btn = ctk.CTkButton(
      preview_controls,
      text="💡 Hướng dẫn",
      width=120,
      height=28,
      font=ctk.CTkFont(size=12, weight="bold"),
      fg_color=("#F59E0B", "#D97706"),
      hover_color=("#D97706", "#B45309"),
      text_color=("#FFFFFF", "#FFFFFF"),
      command=self.start_tutorial,
  )
  self.tutorial_btn.grid(row=1, column=0, columnspan=2, sticky="e", padx=(0, 8), pady=(4, 0))
  ```
- **Finding**: **GENUINE**. Button is styled with specified Amber palette (`#F59E0B` / `#D97706`), placed in the header preview controls grid alongside the theme selector and update button, and directly bound to `self.start_tutorial`.

#### 2.2 User Settings Persistence (`_load_user_settings` & `_save_user_settings`)
- **Location**: `ui/main_window.py` (lines 418–461)
- **Features Verified**:
  - Centralized path resolution via `_get_settings_path()` referencing `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`.
  - UTF-8 with BOM (`utf-8-sig`) decoding resilience to protect against Windows Notepad encoding artifacts.
  - Safe default hydration dictionary: `{"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}`.
  - Atomic writing via temporary file (`.json.tmp`) and `os.replace` with `OSError` fallback for Windows file locks.
  - Granular helpers `_load_theme_setting`, `_save_theme_setting`, `_load_tutorial_seen_setting`, `_save_tutorial_seen_setting` leverage the atomic core without key clobbering.
- **Finding**: **GENUINE & ROBUST**.

#### 2.3 First-Launch Prompt Logic & Lifecycle Integration
- **Location**: `ui/main_window.py` (lines 69, 77–78, 481–507)
- **Features Verified**:
  - `_should_prompt_first_launch_tutorial()` accurately checks `(not has_seen) and auto_suggest`.
  - Non-blocking delayed scheduling: `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)` in `__init__`.
  - Test runner safety guard: checks `os.environ.get("PYTEST_CURRENT_TEST")` or `os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT")` to prevent blocking automated headless test runs.
  - Safe cancellation on window close: `self.after_cancel(self._tutorial_prompt_job)` in `destroy()`.
- **Finding**: **GENUINE & LIFECYCLE-SAFE**.

#### 2.4 Tutorial Overlay Activation & Completion Flow
- **Location**: `ui/main_window.py` (lines 510–539), `ui/app_controller.py` (lines 58–113)
- **Features Verified**:
  - `start_tutorial()` has idempotency protection: restarts at step 0 if overlay already active.
  - Instantiates `InteractiveTutorialOverlay` with notebook sync and `on_finish` callback.
  - `on_finish` invokes `self._save_tutorial_seen_setting(True)` and logs completion to `log_box`.
  - `AppController` exposes corresponding methods (`is_tutorial_seen`, `mark_tutorial_seen`, `get_tutorial_steps`, `start_tutorial`) with standalone disk fallback if view is unattached.
- **Finding**: **GENUINE & CONTRACT-COMPLIANT**.

---

## 3. Forensic Test Suite Verification

Static analysis and syntax contract verification performed on all test suites:
- `tests/test_ui_layout.py`:
  - `test_theme_mode_switching_and_persistence`: Verifies theme modes and persistence of `appearance_mode` in `user_settings.json`.
- `tests/test_tutorial_overlay_e2e.py`:
  - Tier 1 Feature Coverage (Overlay Canvas, Spotlight Bounds, Tooltip Card, Step Navigation, Skip/Finish, 4-Step Script Content, Header Button, Persistence).
  - Tier 2 Boundary & Corner Cases (Zero dimensions, offscreen clamping, empty steps, rapid debouncing, escape key handling, missing widget fallback, resize/minimize).
  - Tier 3 Cross-Feature Interactions (Tab switching + resize, theme switch while overlay active, uncommitted form data preservation).
  - Tier 4 Real-World Application Walkthroughs (First-time user onboarding -> completion -> persistence verification).
- `tests/test_tutorial_script.py`:
  - 4-step structure, Vietnamese text validation, widget accessor methods and property aliases on `SidebarPanel` and `DataTabPanel`.

---

## 4. Final Forensic Verdict

**Verdict**: **CLEAN**  
**Integrity Status**: Fully compliant with development mode standards. No integrity violations, shortcuts, mock facades, or hardcoded cheating detected. Milestone 3 work product is genuine and complete.
