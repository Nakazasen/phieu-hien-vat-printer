# Detailed Technical Analysis & UI Architecture Report: Milestone 3

**File**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\explorer_m3_1\analysis.md`  
**Author**: `explorer_m3_1`  
**Target File**: `d:\Sandbox\PM_in_lai_phieuhienvat\ui\main_window.py`  
**Related Files**: `ui/app_controller.py`, `ui/components/tutorial_overlay.py`, `ui/components/tutorial_script.py`, `PROJECT.md`

---

## 1. Executive Summary

Milestone 3 completes the user-facing trigger and lifecycle integration for the Interactive Tutorial system in `InPhieuHienVat`. This analysis investigates:
1. The exact layout structure of `ui/main_window.py` (`_build_content` / header area).
2. The optimal placement and visual styling of the `💡 Hướng dẫn` (#F59E0B Amber / warm accent) button.
3. The bidirectional interaction model between `SlipPrinterApp` (view) and `AppController` (controller).
4. The persistence mechanism in `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` for tracking `has_seen_tutorial` and triggering first-launch onboarding.

---

## 2. Current Architecture & Header Layout Investigation

### 2.1 UI Component Tree in `ui/main_window.py`
In `ui/main_window.py`, `SlipPrinterApp` extends `ctk.CTk` and establishes a root horizontal splitter (`ttk.Panedwindow` at line 85):
- **Left pane**: `sidebar_host` enclosing `SidebarPanel` (width 360px).
- **Right pane**: `content` (`ctk.CTkFrame`, lines 94–100) populated by `_build_content(parent)`.

### 2.2 Header Grid Analysis (`_build_content`, lines 106–150)
Inside `_build_content(parent: ctk.CTkFrame)`:
- `header = ctk.CTkFrame(parent, fg_color="transparent")` is gridded at `row=0, column=0, sticky="ew", padx=16, pady=(10, 4)`.
- `header.grid_columnconfigure(0, weight=1)` allows the left-hand status/summary text to expand flexibly.

```
┌─ header (CTkFrame, padx=16, pady=(10, 4)) ────────────────────────────────────────────────────────┐
│                                                                                                    │
│  [Col 0, Row 0] Title / Summary (font=20, bold)         [Col 1, Rows 0-1] preview_controls         │
│  [Col 0, Row 1] Status Bar Text (font=12, gray40/60)    ┌────────────────────────────────────────┐ │
│                                                         │ Row 0: [Giao diện:] [Theme OptionMenu] │ │
│                                                         │        [Số dòng:]  [Limit ComboBox]   │ │
│                                                         │ Row 1: [Kiểm tra bản cập nhật Button]  │ │
│                                                         └────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### Detailed Breakdown of `preview_controls` (lines 118–150):
- **Row 0, Col 0**: `CTkLabel(preview_controls, text="Giao diện:", font=CTkFont(size=12))` (`padx=(0, 4)`)
- **Row 0, Col 1**: `self.theme_menu = CTkOptionMenu(preview_controls, width=115, height=28, ...)` (`padx=(0, 10)`)
- **Row 0, Col 2**: `CTkLabel(preview_controls, text="Số dòng:", font=CTkFont(size=12))` (`padx=(0, 4)`)
- **Row 0, Col 3**: `CTkComboBox(preview_controls, width=75, height=28, ...)`
- **Row 1, Cols 0–3**: `CTkButton(preview_controls, text="Kiểm tra bản cập nhật", width=150, height=28, command=self.controller.check_for_update)` (`columnspan=4, sticky="e", pady=(4, 0)`)

---

## 3. Placement & Styling Design for `💡 Hướng dẫn` Button

### 3.1 Layout Option Comparison

| Layout Option | Structure | Pros | Cons | Decision |
|---|---|---|---|---|
| **Option 1: Symmetrical 2x2 Grid in `preview_controls`** *(Recommended)* | Row 0: `[Theme]` + `[Limit]`<br>Row 1: `[💡 Hướng dẫn]` + `[Kiểm tra bản cập nhật]` | • Perfect visual alignment & symmetry<br>• Combined width (120px + 8px + 150px = 278px) easily fits within Row 0 bounds (~315px)<br>• Zero layout shift on resize | None | **SELECTED** |
| **Option 2: Single-Row Extended Header** | Row 0: `[Theme]`, `[Limit]`, `[💡 Hướng dẫn]`, `[Check Update]` | Single row height | May crowd out Summary Title on minimum screen width (1000px) | Rejected |
| **Option 3: Left/Center Separate Action Button** | Column 1 between Title and `preview_controls` | High visibility | Creates uneven header gaps when resizing window | Rejected |

### 3.2 Symmetrical 2x2 Grid Placement Details
In `preview_controls`:
- **Row 1, Column 0..1**:
  `self.tutorial_btn = ctk.CTkButton(preview_controls, ...)`
  `self.tutorial_btn.grid(row=1, column=0, columnspan=2, sticky="e", padx=(0, 8), pady=(4, 0))`
- **Row 1, Column 2..3**:
  `self.update_btn = ctk.CTkButton(preview_controls, text="Kiểm tra bản cập nhật", ...)`
  `self.update_btn.grid(row=1, column=2, columnspan=2, sticky="e", pady=(4, 0))`

### 3.3 CustomTkinter Widget Styling Specification
Following `PROJECT.md` §8 and modern CustomTkinter design principles:
- **Text**: `"💡 Hướng dẫn"`
- **Accent Color (`fg_color`)**: `("#F59E0B", "#D97706")` (Amber 500 in Light mode / Amber 600 in Dark mode)
- **Hover Color (`hover_color`)**: `("#D97706", "#B45309")` (Amber 600 / Amber 700)
- **Text Color (`text_color`)**: `("#FFFFFF", "#FFFFFF")`
- **Font**: `ctk.CTkFont(size=12, weight="bold")`
- **Dimensions**: `width=120`, `height=28` (matches the 28px height of `theme_menu`, `preview_limit_combo`, and `update_btn`)
- **Corner Radius**: `corner_radius=6`
- **Command**: `self.start_tutorial` (or `self.controller.start_tutorial`)

---

## 4. Interaction Model: `SlipPrinterApp` ↔ `AppController`

### 4.1 Invocation Flow
1. **Manual User Click**:
   User clicks `self.tutorial_btn` on the header → invokes `self.start_tutorial()`.
2. **Controller Bridge**:
   If invoked from controller or external script (`self.controller.start_tutorial()`), `AppController` checks `if self.view and hasattr(self.view, "start_tutorial"): return self.view.start_tutorial()`.
3. **Idempotency & Re-entrancy**:
   If an overlay is already active (`self._tutorial_overlay.is_active`), calling `start_tutorial()` restarts the walkthrough at Step 0 (`self._tutorial_overlay.start(0)`) or cleanly destroys and recreates it without creating orphan canvas layers or conflicting keyboard bindings.
4. **Completion Callback (`on_finish`)**:
   When the user completes the final step (Step 4 "🎉 Hoàn tất"), `InteractiveTutorialOverlay` invokes `on_finish()`.
   `SlipPrinterApp._on_tutorial_finished()` is called, which calls `self._save_tutorial_seen_setting(True)` and logs a congratulatory message.

---

## 5. Persistence & First-Launch Prompt Design

### 5.1 JSON Schema in `user_settings.json`
Location: `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` (resolved via `self.app_state.paths.data_dir / "user_settings.json"`).

```json
{
  "appearance_mode": "System",
  "has_seen_tutorial": false,
  "auto_suggest_tutorial": true
}
```

### 5.2 Settings Helper Methods on `SlipPrinterApp`

```python
def _load_tutorial_seen_setting(self) -> bool:
    """Read has_seen_tutorial flag from user_settings.json (default: False)."""
    try:
        settings_path = self.app_state.paths.data_dir / "user_settings.json"
        if settings_path.is_file():
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            return bool(data.get("has_seen_tutorial", False))
    except Exception:
        pass
    return False

def _save_tutorial_seen_setting(self, seen: bool = True) -> None:
    """Persist has_seen_tutorial flag to user_settings.json."""
    try:
        settings_path = self.app_state.paths.data_dir / "user_settings.json"
        data: dict[str, object] = {}
        if settings_path.is_file():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        data["has_seen_tutorial"] = seen
        settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass

def _should_prompt_first_launch_tutorial(self) -> bool:
    """Returns True if the user has not seen the tutorial and auto_suggest is enabled."""
    try:
        settings_path = self.app_state.paths.data_dir / "user_settings.json"
        if settings_path.is_file():
            data = json.loads(settings_path.read_text(encoding="utf-8"))
            has_seen = bool(data.get("has_seen_tutorial", False))
            auto_suggest = bool(data.get("auto_suggest_tutorial", True))
            return (not has_seen) and auto_suggest
    except Exception:
        pass
    return True
```

### 5.3 First-Launch Lifecycle Hook
- In `SlipPrinterApp.__init__()`:
  ```python
  self._tutorial_job = self.after(600, self._check_first_launch_tutorial)
  ```
- In `SlipPrinterApp.destroy()`:
  ```python
  if hasattr(self, "_tutorial_job"):
      self.after_cancel(self._tutorial_job)
  ```
- Implementation of `_check_first_launch_tutorial()`:
  ```python
  def _check_first_launch_tutorial(self) -> None:
      if not self._should_prompt_first_launch_tutorial():
          return
      prompt_msg = (
          "👋 Chào mừng bạn lần đầu sử dụng phần mềm In Phiếu Hiện Vật!\n\n"
          "👉 Bạn có muốn xem hướng dẫn tương tác nhanh (4 bước cơ bản) để làm quen với các tính năng chính không?"
      )
      if messagebox.askyesno("Hướng dẫn sử dụng", prompt_msg):
          self.start_tutorial()
      else:
          # Mark as seen or preserve preference without showing prompt again
          pass
  ```

---

## 6. Proposed Exact Code Changes in `ui/main_window.py`

### 6.1 Change 1: Lifecycle Scheduling & Cleanup in `__init__` and `destroy()`
**Target**: `ui/main_window.py` lines 65–78

```python
<<<<
        self.protocol("WM_DELETE_WINDOW", self.controller.on_close)
        self._drain_job = self.after(150, self._drain_event_queue)
        self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))

    def destroy(self) -> None:
        try:
            if hasattr(self, "_drain_job"):
                self.after_cancel(self._drain_job)
            if hasattr(self, "_update_job"):
                self.after_cancel(self._update_job)
====
        self.protocol("WM_DELETE_WINDOW", self.controller.on_close)
        self._drain_job = self.after(150, self._drain_event_queue)
        self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))
        self._tutorial_job = self.after(600, self._check_first_launch_tutorial)

    def destroy(self) -> None:
        try:
            if hasattr(self, "_drain_job"):
                self.after_cancel(self._drain_job)
            if hasattr(self, "_update_job"):
                self.after_cancel(self._update_job)
            if hasattr(self, "_tutorial_job"):
                self.after_cancel(self._tutorial_job)
>>>>
```

### 6.2 Change 2: Header Grid & `self.tutorial_btn` Construction in `_build_content`
**Target**: `ui/main_window.py` lines 142–150

```python
<<<<
        ctk.CTkButton(
            preview_controls,
            text="Kiểm tra bản cập nhật",
            width=150,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self.controller.check_for_update,
        ).grid(row=1, column=0, columnspan=4, sticky="e", pady=(4, 0))
====
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

        self.update_btn = ctk.CTkButton(
            preview_controls,
            text="Kiểm tra bản cập nhật",
            width=150,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self.controller.check_for_update,
        )
        self.update_btn.grid(row=1, column=2, columnspan=2, sticky="e", pady=(4, 0))
>>>>
```

### 6.3 Change 3: Persistence & Tutorial Engine Helper Methods
**Target**: `ui/main_window.py` lines 425–443

```python
<<<<
    # --- TUTORIAL ENGINE INTEGRATION ---

    def get_tutorial_steps(self=None):
        """Constructs and returns the 4-step tutorial script."""
        from ui.components.tutorial_script import build_tutorial_steps
        return build_tutorial_steps(self)

    def start_tutorial(self):
        """Launch the interactive tutorial overlay over the main window."""
        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        overlay = InteractiveTutorialOverlay(self, notebook=getattr(self, "notebook", None))
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start()
        self._tutorial_overlay = overlay
        return overlay
====
    # --- TUTORIAL PERSISTENCE & LIFECYCLE ---

    def _load_tutorial_seen_setting(self) -> bool:
        """Read has_seen_tutorial flag from user_settings.json."""
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            if settings_path.is_file():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                return bool(data.get("has_seen_tutorial", False))
        except Exception:  # noqa: BLE001
            pass
        return False

    def _save_tutorial_seen_setting(self, seen: bool = True) -> None:
        """Persist has_seen_tutorial flag to user_settings.json."""
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            data: dict[str, object] = {}
            if settings_path.is_file():
                try:
                    data = json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    data = {}
            data["has_seen_tutorial"] = seen
            settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

    def _should_prompt_first_launch_tutorial(self) -> bool:
        """Returns True if the tutorial should be suggested to a first-time user."""
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            if settings_path.is_file():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                has_seen = bool(data.get("has_seen_tutorial", False))
                auto_suggest = bool(data.get("auto_suggest_tutorial", True))
                return (not has_seen) and auto_suggest
        except Exception:  # noqa: BLE001
            pass
        return True

    def _check_first_launch_tutorial(self) -> None:
        """Scheduled startup prompt for first-time users."""
        if not self._should_prompt_first_launch_tutorial():
            return
        prompt_msg = (
            "👋 Chào mừng bạn lần đầu sử dụng phần mềm In Phiếu Hiện Vật!\n\n"
            "👉 Bạn có muốn xem hướng dẫn tương tác nhanh (4 bước cơ bản) để làm quen với các tính năng chính không?"
        )
        if messagebox.askyesno("Hướng dẫn sử dụng", prompt_msg):
            self.start_tutorial()

    def _on_tutorial_finished(self) -> None:
        """Callback executed upon full completion of the walkthrough."""
        self._save_tutorial_seen_setting(True)
        self.append_log("Đã hoàn tất xem hướng dẫn sử dụng.")

    # --- TUTORIAL ENGINE INTEGRATION ---

    def get_tutorial_steps(self=None):
        """Constructs and returns the 4-step tutorial script."""
        from ui.components.tutorial_script import build_tutorial_steps
        return build_tutorial_steps(self)

    def start_tutorial(self):
        """Launch or restart the interactive tutorial overlay over the main window."""
        existing = getattr(self, "_tutorial_overlay", None)
        if existing is not None and getattr(existing, "is_active", False):
            existing.start(0)
            return existing

        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        overlay = InteractiveTutorialOverlay(
            self,
            notebook=getattr(self, "notebook", None),
            on_finish=self._on_tutorial_finished,
        )
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start(0)
        self._tutorial_overlay = overlay
        return overlay
>>>>
```

---

## 7. Verification & Testing Strategy

1. **Automated Unit & E2E Tests**:
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f7_01_header_tutorial_button_rendered`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f7_02_header_button_amber_styling`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f7_03_header_button_invokes_tutorial`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f8_01_settings_file_creation_with_tutorial_keys`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f8_02_default_settings_values`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f8_03_saving_tutorial_completed_state`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f8_04_first_launch_prompt_logic`
   - `tests/test_tutorial_overlay_e2e.py::TestTier1FeatureCoverage::test_t1_f8_05_first_launch_prompt_suppressed_when_seen`
2. **Visual & Responsive Verification**:
   - Verify that `self.tutorial_btn` renders with distinct Amber accent (#F59E0B) in both Light and Dark themes.
   - Verify that clicking the button immediately darkens the screen and spotlights Step 1 without throwing any mainloop exceptions.
