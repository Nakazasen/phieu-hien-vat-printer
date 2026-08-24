# Technical Specification & Feature Discovery Report: Milestone 3 First-Launch Tutorial Prompt & UI Trigger Button

## Executive Summary
This specification defines the exact behavioral, UX, architectural, and test-safety requirements for **Milestone 3: UI Trigger Button, Persistence & First-Launch Prompt** of the `InPhieuHienVat` application, derived from `ORIGINAL_REQUEST.md §R3`, `PROJECT.md`, and modern Windows desktop UX standards.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | UI / Header | Header Tutorial Button (`💡 Hướng dẫn`) | Accessible Amber button (#F59E0B) in main window header allowing users to manually launch the tutorial at any time | User mouse click or keyboard trigger | Invokes `controller.start_tutorial()`, rendering 4-step overlay | If overlay is already active, safely resets to step 0 or lifts without duplicating canvas | ORIGINAL_REQUEST.md §R3, PROJECT.md §Feature 8 |
| 2 | Persistence | User Settings Persistence (`user_settings.json`) | Read/write persistent JSON in `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` storing `has_seen_tutorial`, `auto_suggest_tutorial`, and `appearance_mode` | File path, JSON payload | Dictionary of user preferences | Recovers with safe defaults if JSON is missing, corrupted, or unreadable | PROJECT.md §Feature 9, ui/main_window.py |
| 3 | Lifecycle | First-Launch Trigger Flow & Lifecycle Timer | Delayed check scheduled via `after(600, ...)` upon app launch to determine if first-launch onboarding prompt should be displayed | `has_seen_tutorial`, `auto_suggest_tutorial`, test/headless flags | Displays modal prompt dialog or skips cleanly | Cancels pending `after()` timer if window is closed before 600ms settling time | ORIGINAL_REQUEST.md §R3, ui/main_window.py |
| 4 | Onboarding UX | First-Launch Onboarding Prompt Modal | Non-blocking CustomTkinter dialog (`TutorialPromptDialog`) welcoming first-time users and offering to start interactive guide | User selection: "Bắt đầu hướng dẫn (Khuyên dùng)" vs "Để sau / Không nhắc lại" | Launches walkthrough or dismisses dialog and persists choice | Graceful fallback if master window is minimized or unmapped | ORIGINAL_REQUEST.md §R3, modern desktop UX standards |
| 5 | Test Safety | Headless & CI Test Execution Guard | Safeguards preventing automated tests or CI environments from blocking on first-launch prompts or modal dialogs | `PYTEST_CURRENT_TEST`, `CI`, `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT`, or `auto_prompt=False` | Suppresses modal creation during automated test runs | Silent bypass; logs debug trace if needed | TEST_INFRA.md, tests/test_tutorial_overlay_e2e.py |
| 6 | Integration | Overlay Lifecycle & Completion State Sync | When walkthrough finishes or is skipped, application state updates `has_seen_tutorial = True` in memory and disk | User completes step 4 or clicks skip | `user_settings.json` updated with `has_seen_tutorial: true` | I/O exceptions during save are caught and logged without disrupting UI | ui/components/tutorial_overlay.py, PROJECT.md |

---

## Detailed System Design & Behavioral Specifications

### 1. Header Trigger Button (`💡 Hướng dẫn`)
- **Location**: In the header bar of `SlipPrinterApp` within `preview_controls` frame (adjacent to Appearance Mode dropdown and "Kiểm tra bản cập nhật").
- **Visual Styling**:
  - Button Text: `"💡 Hướng dẫn"` (or `"💡 Hướng dẫn (Tutorial)"`)
  - Accent Color: Amber (`fg_color="#F59E0B"`, `hover_color="#D97706"`, `text_color="#FFFFFF"`)
  - Font: `ctk.CTkFont(size=12, weight="bold")`
  - Dimensions: `height=28`, `width=115`
- **Behavioral Contract**:
  - Clicking invokes `self.controller.start_tutorial()` (or `self.start_tutorial()`).
  - Idempotent: If an overlay is already running, re-focuses/lifts the existing overlay or resets step to 0 without stacking canvases.
  - Can be triggered repeatedly throughout the application lifecycle.

### 2. User Settings Persistence (`user_settings.json`)
- **File Location**: `self.app_state.paths.data_dir / "user_settings.json"` (typically `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`).
- **Schema**:
```json
{
  "appearance_mode": "System",
  "has_seen_tutorial": false,
  "auto_suggest_tutorial": true
}
```
- **Field Semantics**:
  - `appearance_mode` (`str`): `"Dark"`, `"Light"`, or `"System"`. Default: `"System"`.
  - `has_seen_tutorial` (`bool`): `True` if user has completed or experienced the tutorial; `False` for fresh installations. Default: `False`.
  - `auto_suggest_tutorial` (`bool`): `True` if app should prompt on startup when `has_seen_tutorial == False`; `False` if user explicitly opted out. Default: `True`.
- **Atomic Read / Write Protocol**:
  - Reading: If file doesn't exist or JSON parsing fails, fallback to `{ "appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True }`.
  - Writing: Preserve existing keys (e.g. `appearance_mode`) when updating tutorial flags. Ensure `ensure_ascii=False` and `indent=2`.

### 3. First-Launch Trigger Flow & Scheduling
- **Trigger Condition**:
  ```python
  def _should_prompt_first_launch_tutorial(self) -> bool:
      if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT"):
          return False
      settings = self._load_user_settings()
      return not settings.get("has_seen_tutorial", False) and settings.get("auto_suggest_tutorial", True)
  ```
- **Execution Timing**:
  - Scheduled in `SlipPrinterApp.__init__` using `self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)`.
  - **Rationale for 600ms delay**:
    1. UI layout settles: Sash position `_apply_splitter_width` executes at 120ms; event queue starts at 150ms.
    2. Prevents visual flickering and geometry miscalculations during root window map.
    3. Guarantees that target widgets on the Sidebar and DataTab exist and have non-zero geometry before any overlay is spawned.
- **Teardown Safety**:
  - In `SlipPrinterApp.destroy()`, cancel `self._tutorial_prompt_job` if still pending:
    ```python
    if hasattr(self, "_tutorial_prompt_job") and self._tutorial_prompt_job:
        self.after_cancel(self._tutorial_prompt_job)
        self._tutorial_prompt_job = None
    ```

### 4. First-Launch Prompt Dialog UX (`TutorialPromptDialog`)
- **Dialog Architecture**:
  - Non-blocking `ctk.CTkToplevel` modal window centered over parent `SlipPrinterApp`.
  - Transient with `self.transient(parent)` and `self.grab_set()`.
  - Esc key and window close button ([X]) map cleanly to dismiss / decline.
- **UI Structure**:
  - **Header Icon & Title**:
    - Icon / Emoji: `"✨"` or `"💡"`
    - Title: `"Chào mừng bạn đến với In Phiếu Hiện Vật!"` (Font size: 16 bold)
    - Subtitle: `"Bạn có muốn xem hướng dẫn nhanh các tính năng cốt lõi không?"` (Font size: 13)
  - **Feature Highlights (Card List)**:
    - 📥 *Nạp dữ liệu từ file Excel bảng kê*
    - ⚡ *Quét mã QR thông minh (Phân tách & Hoàn kho)*
    - 🔢 *Tự động cấp phát số PO không trùng lặp*
    - 🖨️ *Xuất và in phiếu PDF chuẩn 4 tem/trang A4*
  - **Action Button Row**:
    - **Primary CTA**: `"✨ Bắt đầu hướng dẫn (Khuyên dùng)"`
      - Background: Emerald `#10B981` (hover `#059669`) or Amber `#F59E0B`
      - Action: Closes modal dialog, persists `has_seen_tutorial = True`, and starts `self.start_tutorial()`.
    - **Secondary CTA**: `"Để sau / Bỏ qua"`
      - Background: Transparent with gray border / subtle gray hover
      - Action: Closes modal dialog.
  - **Opt-out Checkbox**:
    - Text: `"Không tự động nhắc lại khi khởi động"`
    - Default state: Checked (`True`)
    - If checked upon clicking "Để sau", sets `auto_suggest_tutorial = False` and `has_seen_tutorial = True`.

---

## Edge Cases

| # | Feature | Input / Condition | Observed Behavior & Handling |
|---|---------|-------------------|-----------------------------|
| 1 | Settings Persistence | Missing or corrupted `user_settings.json` | Safely catches `JSONDecodeError` / `OSError`, creates default file with `has_seen_tutorial=False`, `auto_suggest_tutorial=True` |
| 2 | Prompt Scheduling | App closed/destroyed before 600ms timer fires | `destroy()` invokes `after_cancel(self._tutorial_prompt_job)` to prevent `TclError: invalid command name` |
| 3 | Automated Testing | Pytest runs test suite without GUI interaction | Detects `PYTEST_CURRENT_TEST` or `INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT=1` and bypasses first-launch prompt, preventing test suite freezes |
| 4 | Double Trigger | User clicks Header button while prompt dialog is open | Dialog brings itself to focus; clicking Primary CTA closes dialog before launching overlay |
| 5 | Overlay Conflict | User clicks Header button while tutorial overlay is already active | Idempotent: `start_tutorial()` cancels previous session and starts freshly at Step 0 without duplicate Canvas layers |
| 6 | Window Minimization | Window minimized or resized during first-launch prompt | Dialog stays anchored / transient to parent and restores properly on de-iconify |
| 7 | Skip / Early Exit | User starts tutorial from prompt but skips at Step 2 | Step 2 skip cleans up canvas/tooltip and records `has_seen_tutorial=True` so user is not re-prompted on next launch |
| 8 | Read-Only Disk | Data directory has restricted write permissions | `_save_user_settings()` catches `PermissionError` and allows application to run seamlessly in-memory |

---

## Interface Contracts & Code Specifications

### Contract 1: `SlipPrinterApp` Integration in `ui/main_window.py`

```python
class SlipPrinterApp(ctk.CTk):
    # ...
    def _init_tutorial_hooks(self) -> None:
        """Schedule first-launch prompt check if eligible."""
        self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)

    def _load_user_settings(self) -> dict:
        """Load user settings dictionary from user_settings.json with robust fallback."""
        settings_path = self.app_state.paths.data_dir / "user_settings.json"
        defaults = {
            "appearance_mode": "System",
            "has_seen_tutorial": False,
            "auto_suggest_tutorial": True,
        }
        if not settings_path.is_file():
            return defaults
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                defaults.update(data)
        except Exception:
            pass
        return defaults

    def _save_user_settings(self, updates: dict) -> None:
        """Atomically merge and persist updates into user_settings.json."""
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            current = self._load_user_settings()
            current.update(updates)
            settings_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def _should_prompt_first_launch_tutorial(self) -> bool:
        """Returns True if the first-launch tutorial prompt should be displayed."""
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT"):
            return False
        settings = self._load_user_settings()
        return not bool(settings.get("has_seen_tutorial", False)) and bool(settings.get("auto_suggest_tutorial", True))

    def _check_first_launch_tutorial(self) -> None:
        """Timer callback to display the first-launch onboarding prompt dialog."""
        self._tutorial_prompt_job = None
        if self._should_prompt_first_launch_tutorial():
            self._show_first_launch_tutorial_dialog()

    def _show_first_launch_tutorial_dialog(self) -> None:
        """Opens the First-Launch Tutorial Onboarding Dialog."""
        from ui.components.tutorial_prompt_dialog import TutorialPromptDialog
        TutorialPromptDialog(
            parent=self,
            on_start=self._on_tutorial_prompt_accept,
            on_dismiss=self._on_tutorial_prompt_decline,
        )

    def _on_tutorial_prompt_accept(self) -> None:
        """Callback when user accepts first-launch prompt."""
        self._save_user_settings({"has_seen_tutorial": True})
        self.start_tutorial()

    def _on_tutorial_prompt_decline(self, never_ask_again: bool = True) -> None:
        """Callback when user declines first-launch prompt."""
        updates = {"has_seen_tutorial": True} if never_ask_again else {"auto_suggest_tutorial": False}
        self._save_user_settings(updates)

    def start_tutorial(self):
        """Launch the interactive tutorial overlay over the main window."""
        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        # Mark seen upon launching
        self._save_user_settings({"has_seen_tutorial": True})

        if hasattr(self, "_tutorial_overlay") and self._tutorial_overlay and self._tutorial_overlay.is_active:
            self._tutorial_overlay.destroy()

        overlay = InteractiveTutorialOverlay(
            self,
            notebook=getattr(self, "notebook", None),
            on_finish=lambda: self._save_user_settings({"has_seen_tutorial": True}),
        )
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start()
        self._tutorial_overlay = overlay
        return overlay
```

---

## Verification & Acceptance Criteria Matrix

| Checkpoint | Target Behavior | Verification Method |
|---|---|---|
| 1. Header Button Display | `💡 Hướng dẫn` rendered in Amber (#F59E0B) on Header bar across themes | `test_t1_f7_01_header_tutorial_button_rendered` |
| 2. Header Button Click | Clicking header button launches `InteractiveTutorialOverlay` at Step 1 | `test_t1_f7_03_header_button_invokes_tutorial` |
| 3. Settings Persistence | `has_seen_tutorial` & `auto_suggest_tutorial` saved to `user_settings.json` | `test_t1_f8_01_settings_file_creation_with_tutorial_keys` |
| 4. First-Launch Auto Prompt | Fresh app launch displays onboarding dialog after 600ms settling | `test_t1_f8_04_first_launch_prompt_logic` |
| 5. Re-launch Suppression | App relaunch with `has_seen_tutorial=True` skips auto-prompt | `test_t1_f8_05_first_launch_prompt_suppressed_when_seen` |
| 6. Headless & Test Safety | Tests execute without blocking on modals or throwing Tcl errors | `test_t4_01_first_time_user_full_walkthrough_to_completion` |
