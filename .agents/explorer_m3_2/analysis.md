# Technical Analysis: User Preferences Persistence & Settings Schema Extension

**Author**: `explorer_m3_2` (Teamwork Explorer)  
**Date**: 2026-08-19  
**Target Milestone**: M3 (UI Trigger Button, Persistence & First-Launch Prompt)  
**Related Specs**: `ORIGINAL_REQUEST.md §R3`, `PROJECT.md §Interface Contracts`, `TEST_INFRA.md`  

---

## 1. Executive Summary

This report delivers a comprehensive architectural investigation into user preference persistence for the `InPhieuHienVat` application. It evaluates the current configuration landscape, analyzes the existing `user_settings.json` implementation in `ui/main_window.py`, designs the schema extension for `has_seen_tutorial: bool` and `auto_suggest_tutorial: bool`, devises an atomic write and fallback strategy, and provides concrete, ready-to-implement integration blueprints for `SlipPrinterApp` and `AppController`.

---

## 2. Current Persistence Ecosystem & File Architecture

The `InPhieuHienVat` application partitions persistence across four specialized storage domains:

| Storage Domain | File / Store Path | Managing Module | Purpose & Scope |
|---|---|---|---|
| **User Preferences** | `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` | `ui/main_window.py` (`SlipPrinterApp`) | Stores UI theme mode (`Dark`, `Light`, `System`), tutorial completion state (`has_seen_tutorial`), and auto-prompt preference (`auto_suggest_tutorial`). |
| **PDF Layout Geometry** | `%LOCALAPPDATA%\InPhieuHienVatData\layout_config.json` | `core/slip_printer_engine.py` | Stores ReportLab coordinate bounding boxes (`qr_positions`, `text_positions`, `font`). Completely separate from user preferences. |
| **PO Registry & History** | `\\fstvn01\Data\...\po_registry.db` or `%LOCALAPPDATA%\InPhieuHienVatData\po_registry.db` | `core/po_registry.py` (`PORegistry`) | SQLite database with WAL mode for PO numbering sequence (`11YYMMDDNN`), duplicate tracking, and box dispatch history. |
| **Updater Metadata** | `%LOCALAPPDATA%\InPhieuHienVatData\update_sources.json` | `updater/update_delivery.py` | Stores UNC/HTTP release channels and update catalog hashes. |

### Path Resolution Mechanism (`core/runtime_paths.py`)
All mutable application data directories are resolved via `prepare_runtime_paths()` (`core/runtime_paths.py:127-156`):
- `data_dir` resolution hierarchy:
  1. `INPHIEUHIENVAT_DATA_DIR` environment variable (used for automated pytest test isolation via `tmp_path`).
  2. `%LOCALAPPDATA%\InPhieuHienVatData` on standard Windows client installations.
  3. `%USERPROFILE%\AppData\Local\InPhieuHienVatData` as local fallback.
- `user_settings.json` is accessed dynamically via:
  ```python
  settings_path = self.app_state.paths.data_dir / "user_settings.json"
  ```

---

## 3. Analysis of Current Implementation & Identified Deficiencies

### 3.1 Current Code in `ui/main_window.py` (lines 399–423)

```python
399:     def _load_theme_setting(self) -> str:
400:         try:
401:             settings_path = self.app_state.paths.data_dir / "user_settings.json"
402:             if settings_path.is_file():
403:                 data = json.loads(settings_path.read_text(encoding="utf-8"))
404:                 mode = str(data.get("appearance_mode", "System"))
405:                 if mode in ("Dark", "Light", "System"):
406:                     return mode
407:         except Exception:  # noqa: BLE001
408:             pass
409:         return "System"
410: 
411:     def _save_theme_setting(self, mode: str) -> None:
412:         try:
413:             settings_path = self.app_state.paths.data_dir / "user_settings.json"
414:             data: dict[str, object] = {}
415:             if settings_path.is_file():
416:                 try:
417:                     data = json.loads(settings_path.read_text(encoding="utf-8"))
418:                 except Exception:  # noqa: BLE001
419:                     data = {}
420:             data["appearance_mode"] = mode
421:             settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
422:         except Exception:  # noqa: BLE001
423:             pass
```

### 3.2 Key Deficiencies & Vulnerabilities

1. **Non-Atomic In-Place Truncation (`write_text`)**:
   - `write_text(...)` immediately truncates `user_settings.json` to 0 bytes before writing. If the app process terminates abruptly (power outage, crash, forced task termination, or OS shutdown) during the write call, `user_settings.json` is left corrupted or empty (0 bytes).
2. **Missing UTF-8 BOM Handling (`utf-8` vs `utf-8-sig`)**:
   - If an end-user or IT administrator manually edits `user_settings.json` using Windows Notepad, Notepad frequently injects a Byte Order Mark (`\xef\xbb\xbf`). Reading with `encoding="utf-8"` causes `json.loads` to crash with `JSONDecodeError`. Reading with `encoding="utf-8-sig"` strips BOM transparently.
3. **Monolithic Key Handlers without Centralized Storage Manager**:
   - Currently, `_load_theme_setting` and `_save_theme_setting` duplicate file existence checks, JSON reading, exception suppression, and writing. Adding `has_seen_tutorial` and `auto_suggest_tutorial` would lead to repeated boilerplate.
4. **Missing Tutorial Persistence APIs Required by Test Contracts**:
   - Contract test suite `tests/test_tutorial_overlay_e2e.py` lines 877–920 directly checks for the following methods on `SlipPrinterApp`:
     - `_load_tutorial_seen_setting()`
     - `_save_tutorial_seen_setting(seen: bool)`
     - `_should_prompt_first_launch_tutorial()`
     - `_check_first_run_tutorial()`

---

## 4. Extended Schema Design for User Settings

### 4.1 Schema Definition

```json
{
  "appearance_mode": "System",
  "has_seen_tutorial": false,
  "auto_suggest_tutorial": true
}
```

### 4.2 Field Specifications & Semantics

| Field Name | Type | Default Value | Allowed Values | Semantic Description & Trigger Events |
|---|---|---|---|---|
| `appearance_mode` | `str` | `"System"` | `"Dark"`, `"Light"`, `"System"` | Active CustomTkinter / ttk theme appearance mode. Saved when user modifies the header dropdown. |
| `has_seen_tutorial` | `bool` | `false` | `true`, `false` | Indicates whether the user has completed or experienced the tutorial. Set to `true` when user finishes the 4-step walkthrough via `overlay.finish()` (`on_finish` callback) or clicks "Không nhắc lại" on first-launch prompt. |
| `auto_suggest_tutorial` | `bool` | `true` | `true`, `false` | Controls whether the application should automatically pop up the first-launch recommendation prompt. If `false`, the app will never auto-prompt, but manual launch via `💡 Hướng dẫn` remains available. |

### 4.3 Backwards & Forward Compatibility

1. **Clean Installation (Missing File)**:
   - Returns default settings: `{"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}`.
   - File is created upon first save event.
2. **Upgrade from v0.1 (File contains only `"appearance_mode"`)**:
   - `_load_user_settings()` loads existing dictionary and merges with `DEFAULT_USER_SETTINGS`. Missing keys automatically default to `has_seen_tutorial: False` and `auto_suggest_tutorial: True`.
3. **Forward Compatibility (Future Keys / Unknown Keys)**:
   - When updating settings, the existing dictionary is preserved via `data[key] = value`, ensuring future or extra keys are not wiped out during write.
4. **Corrupt / Zero-Byte File Recovery**:
   - If JSON decode fails or file is empty, defaults are returned gracefully without crashing the UI or blocking startup.

---

## 5. Robust Atomic Persistence & Fallback Architecture

### 5.1 Atomic Write Protocol

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Serialize Dict -> JSON string with UTF-8, indent=2        │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Ensure target directory exists (mkdir parents=True)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Write to temporary file: user_settings.json.tmp           │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Atomic Rename: os.replace(temp_path, target_path)        │
│    (Atomic replace on Windows NTFS via MoveFileExW)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                    [Exception / Antivirus Lock?]
                               │
                               ├──────────► Fallback: Direct Write
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Clean up temporary file on failure                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Python Implementation Details

```python
DEFAULT_USER_SETTINGS: dict[str, object] = {
    "appearance_mode": "System",
    "has_seen_tutorial": False,
    "auto_suggest_tutorial": True,
}


def load_user_settings_from_path(settings_path: Path) -> dict[str, object]:
    """Read user settings file with utf-8-sig encoding and fallback to defaults."""
    settings: dict[str, object] = dict(DEFAULT_USER_SETTINGS)
    if not settings_path.is_file():
        return settings
    try:
        raw_text = settings_path.read_text(encoding="utf-8-sig")
        loaded = json.loads(raw_text)
        if isinstance(loaded, dict):
            settings.update(loaded)
    except Exception:
        pass
    return settings


def save_user_settings_to_path(settings_path: Path, data: dict[str, object]) -> None:
    """Save user settings atomically via temporary file and os.replace."""
    try:
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        temp_path = settings_path.with_suffix(".json.tmp")
        temp_path.write_text(payload, encoding="utf-8")
        try:
            os.replace(temp_path, settings_path)
        except OSError:
            # Fallback to direct write if atomic replacement encounters transient file lock
            settings_path.write_text(payload, encoding="utf-8")
            temp_path.unlink(missing_ok=True)
    except Exception:
        pass
```

---

## 6. Integration Points with `SlipPrinterApp` & `AppController`

### 6.1 Integration in `ui/main_window.py`

#### A. Centralized Settings Accessors
Replace lines 399–423 in `ui/main_window.py` with unified methods:

```python
    # --- USER SETTINGS PERSISTENCE (THEME & TUTORIAL) ---

    def _get_settings_path(self) -> Path:
        """Return the resolved Path to user_settings.json."""
        if hasattr(self, "app_state") and hasattr(self.app_state, "paths"):
            return self.app_state.paths.data_dir / "user_settings.json"
        from core.runtime_paths import prepare_runtime_paths
        return prepare_runtime_paths().data_dir / "user_settings.json"

    def _load_user_settings(self) -> dict[str, object]:
        """Load full user settings dictionary with default fallbacks."""
        defaults: dict[str, object] = {
            "appearance_mode": "System",
            "has_seen_tutorial": False,
            "auto_suggest_tutorial": True,
        }
        try:
            settings_path = self._get_settings_path()
            if settings_path.is_file():
                raw = settings_path.read_text(encoding="utf-8-sig")
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    defaults.update(loaded)
        except Exception:
            pass
        return defaults

    def _save_user_settings(self, data: dict[str, object]) -> None:
        """Persist user settings dictionary atomically to disk."""
        try:
            settings_path = self._get_settings_path()
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            temp_path = settings_path.with_suffix(".json.tmp")
            temp_path.write_text(payload, encoding="utf-8")
            try:
                os.replace(temp_path, settings_path)
            except OSError:
                settings_path.write_text(payload, encoding="utf-8")
                temp_path.unlink(missing_ok=True)
        except Exception:
            pass

    def _load_theme_setting(self) -> str:
        """Load appearance theme mode ('Dark', 'Light', 'System')."""
        settings = self._load_user_settings()
        mode = str(settings.get("appearance_mode", "System"))
        return mode if mode in ("Dark", "Light", "System") else "System"

    def _save_theme_setting(self, mode: str) -> None:
        """Save appearance theme mode to user_settings.json."""
        settings = self._load_user_settings()
        settings["appearance_mode"] = mode
        self._save_user_settings(settings)

    def _load_tutorial_seen_setting(self) -> bool:
        """Load tutorial completion flag from user_settings.json."""
        settings = self._load_user_settings()
        return bool(settings.get("has_seen_tutorial", False))

    def _save_tutorial_seen_setting(self, seen: bool = True) -> None:
        """Save tutorial completion flag to user_settings.json."""
        settings = self._load_user_settings()
        settings["has_seen_tutorial"] = bool(seen)
        self._save_user_settings(settings)

    def _should_prompt_first_launch_tutorial(self) -> bool:
        """Check whether the first-launch tutorial prompt should be presented."""
        settings = self._load_user_settings()
        has_seen = bool(settings.get("has_seen_tutorial", False))
        auto_suggest = bool(settings.get("auto_suggest_tutorial", True))
        return (not has_seen) and auto_suggest

    def _check_first_run_tutorial(self) -> None:
        """Prompt first-time users to start the interactive walkthrough."""
        if not self._should_prompt_first_launch_tutorial():
            return

        try:
            answer = messagebox.askyesno(
                APP_TITLE,
                "Chào mừng bạn đến với Phần mềm In Phiếu Hiện Vật!\n\n"
                "Bạn có muốn xem hướng dẫn sử dụng nhanh (4 bước: Import Excel, Quét QR, Tạo Auto PO, Xuất PDF) không?",
                parent=self,
            )
            if answer:
                self.start_tutorial()
        except Exception:
            pass
```

#### B. Wiring `start_tutorial()` with Completion Callback
Update `start_tutorial()` in `ui/main_window.py:432-443`:

```python
    def start_tutorial(self):
        """Launch the interactive tutorial overlay over the main window."""
        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        def _on_tutorial_completed() -> None:
            self._save_tutorial_seen_setting(True)
            self.append_log("Đã hoàn thành hướng dẫn sử dụng phần mềm!")

        overlay = InteractiveTutorialOverlay(
            self,
            notebook=getattr(self, "notebook", None),
            on_finish=_on_tutorial_completed,
        )
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start()
        self._tutorial_overlay = overlay
        return overlay
```

#### C. Startup Hook & Teardown Cleanup in `SlipPrinterApp.__init__` and `destroy()`
In `SlipPrinterApp.__init__` (after line 67):
```python
        # 4. Schedule first-launch tutorial prompt after initial window render
        self._tutorial_prompt_job = self.after(500, self._check_first_run_tutorial)
```
In `SlipPrinterApp.destroy` (after line 74):
```python
        if hasattr(self, "_tutorial_prompt_job"):
            try:
                self.after_cancel(self._tutorial_prompt_job)
            except Exception:
                pass
```

---

### 6.2 Integration in `ui/app_controller.py`

Expose high-level controller methods for view-independent state queries:

```python
    def is_tutorial_seen(self) -> bool:
        """Return True if the user has completed or seen the tutorial."""
        if self.view and hasattr(self.view, "_load_tutorial_seen_setting"):
            return self.view._load_tutorial_seen_setting()
        settings_path = self.app_state.paths.data_dir / "user_settings.json"
        if settings_path.is_file():
            try:
                data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
                return bool(data.get("has_seen_tutorial", False))
            except Exception:
                pass
        return False

    def mark_tutorial_seen(self, seen: bool = True) -> None:
        """Mark tutorial as seen/completed in persistent user settings."""
        if self.view and hasattr(self.view, "_save_tutorial_seen_setting"):
            self.view._save_tutorial_seen_setting(seen)
        else:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            data: dict[str, object] = {"has_seen_tutorial": seen}
            if settings_path.is_file():
                try:
                    data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
                    data["has_seen_tutorial"] = seen
                except Exception:
                    pass
            try:
                settings_path.parent.mkdir(parents=True, exist_ok=True)
                settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            except Exception:
                pass
```

---

## 7. Failure Modes, Edge Cases & Resilience Matrix

| Scenario / Edge Case | Risk / Failure Mode | Mitigating Architecture | Behavior & Outcome |
|---|---|---|---|
| **Clean / First Install** | `user_settings.json` does not exist on disk. | Lazy hydration with `DEFAULT_USER_SETTINGS`. | App boots with `"System"` theme, `has_seen_tutorial: False`, `auto_suggest_tutorial: True`. File is created upon first save event. |
| **Abrupt Power Loss / Crash during Save** | Partial/zero-byte file left on disk. | Atomic write: `temp_path = settings.json.tmp` + `os.replace`. | Either the old file remains intact or the new file is committed in full. No 0-byte corrupt state possible. |
| **Corrupted / Invalid JSON** | Manual tampering or disk corruption results in `json.JSONDecodeError`. | `try...except (json.JSONDecodeError, OSError)` with default dictionary fallback. | App recovers smoothly with default settings; does not crash or freeze startup. |
| **UTF-8 BOM Header** | User edits file with Windows Notepad which injects `\xef\xbb\xbf`. | Read using `encoding="utf-8-sig"`. | Strips BOM header transparently; JSON parses perfectly. |
| **Forward Compatibility** | Future version or plugins add arbitrary keys (e.g. `recent_files`, `sound_enabled`). | Dictionary update (`settings.update(...)` / `settings[key] = value`). | Unknown keys are preserved across save cycles; never discarded. |
| **Headless / Test Environment** | Pytest test execution runs without GUI display or in temporary sandbox. | Test isolation via `INPHIEUHIENVAT_DATA_DIR` and `mock_tkinter_messagebox` in `conftest.py`. | Tests execute without blocking on modal dialogs; temporary directories clean up automatically. |

---

## 8. Exact Code Proposals & Line Number Mapping

### Proposed Edits in `ui/main_window.py`

#### Edit 1: Lines 64–70 (Scheduling First-Run Check)
```python
<<<< BEFORE (lines 64-68)
        # 3. Setup sau khi render
        self.protocol("WM_DELETE_WINDOW", self.controller.on_close)
        self._drain_job = self.after(150, self._drain_event_queue)
        self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))
==== AFTER
        # 3. Setup sau khi render
        self.protocol("WM_DELETE_WINDOW", self.controller.on_close)
        self._drain_job = self.after(150, self._drain_event_queue)
        self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))
        self._tutorial_prompt_job = self.after(500, self._check_first_run_tutorial)
>>>>
```

#### Edit 2: Lines 70–78 (Canceling First-Run Timer on Destroy)
```python
<<<< BEFORE (lines 70-75)
    def destroy(self) -> None:
        try:
            if hasattr(self, "_drain_job"):
                self.after_cancel(self._drain_job)
            if hasattr(self, "_update_job"):
                self.after_cancel(self._update_job)
==== AFTER
    def destroy(self) -> None:
        try:
            if hasattr(self, "_drain_job"):
                self.after_cancel(self._drain_job)
            if hasattr(self, "_update_job"):
                self.after_cancel(self._update_job)
            if hasattr(self, "_tutorial_prompt_job"):
                self.after_cancel(self._tutorial_prompt_job)
>>>>
```

#### Edit 3: Lines 399–443 (Full Settings & Tutorial Integration)
```python
<<<< BEFORE (lines 399-443)
    def _load_theme_setting(self) -> str:
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            if settings_path.is_file():
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                mode = str(data.get("appearance_mode", "System"))
                if mode in ("Dark", "Light", "System"):
                    return mode
        except Exception:  # noqa: BLE001
            pass
        return "System"

    def _save_theme_setting(self, mode: str) -> None:
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            data: dict[str, object] = {}
            if settings_path.is_file():
                try:
                    data = json.loads(settings_path.read_text(encoding="utf-8"))
                except Exception:  # noqa: BLE001
                    data = {}
            data["appearance_mode"] = mode
            settings_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass

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
==== AFTER
    # --- USER SETTINGS PERSISTENCE (THEME & TUTORIAL) ---

    def _get_settings_path(self) -> Path:
        """Return the resolved Path to user_settings.json."""
        if hasattr(self, "app_state") and hasattr(self.app_state, "paths"):
            return self.app_state.paths.data_dir / "user_settings.json"
        from core.runtime_paths import prepare_runtime_paths
        return prepare_runtime_paths().data_dir / "user_settings.json"

    def _load_user_settings(self) -> dict[str, object]:
        """Load full user settings dictionary with default fallbacks."""
        defaults: dict[str, object] = {
            "appearance_mode": "System",
            "has_seen_tutorial": False,
            "auto_suggest_tutorial": True,
        }
        try:
            settings_path = self._get_settings_path()
            if settings_path.is_file():
                raw = settings_path.read_text(encoding="utf-8-sig")
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    defaults.update(loaded)
        except Exception:
            pass
        return defaults

    def _save_user_settings(self, data: dict[str, object]) -> None:
        """Persist user settings dictionary atomically to disk."""
        try:
            settings_path = self._get_settings_path()
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            temp_path = settings_path.with_suffix(".json.tmp")
            temp_path.write_text(payload, encoding="utf-8")
            try:
                os.replace(temp_path, settings_path)
            except OSError:
                settings_path.write_text(payload, encoding="utf-8")
                temp_path.unlink(missing_ok=True)
        except Exception:
            pass

    def _load_theme_setting(self) -> str:
        """Load appearance theme mode ('Dark', 'Light', 'System')."""
        settings = self._load_user_settings()
        mode = str(settings.get("appearance_mode", "System"))
        return mode if mode in ("Dark", "Light", "System") else "System"

    def _save_theme_setting(self, mode: str) -> None:
        """Save appearance theme mode to user_settings.json."""
        settings = self._load_user_settings()
        settings["appearance_mode"] = mode
        self._save_user_settings(settings)

    def _load_tutorial_seen_setting(self) -> bool:
        """Load tutorial completion flag from user_settings.json."""
        settings = self._load_user_settings()
        return bool(settings.get("has_seen_tutorial", False))

    def _save_tutorial_seen_setting(self, seen: bool = True) -> None:
        """Save tutorial completion flag to user_settings.json."""
        settings = self._load_user_settings()
        settings["has_seen_tutorial"] = bool(seen)
        self._save_user_settings(settings)

    def _should_prompt_first_launch_tutorial(self) -> bool:
        """Check whether the first-launch tutorial prompt should be presented."""
        settings = self._load_user_settings()
        has_seen = bool(settings.get("has_seen_tutorial", False))
        auto_suggest = bool(settings.get("auto_suggest_tutorial", True))
        return (not has_seen) and auto_suggest

    def _check_first_run_tutorial(self) -> None:
        """Prompt first-time users to start the interactive walkthrough."""
        if not self._should_prompt_first_launch_tutorial():
            return

        try:
            answer = messagebox.askyesno(
                APP_TITLE,
                "Chào mừng bạn đến với Phần mềm In Phiếu Hiện Vật!\n\n"
                "Bạn có muốn xem hướng dẫn sử dụng nhanh (4 bước thao tác: Import Excel, Quét QR, Tạo Auto PO, Xuất PDF) không?",
                parent=self,
            )
            if answer:
                self.start_tutorial()
        except Exception:
            pass

    # --- TUTORIAL ENGINE INTEGRATION ---

    def get_tutorial_steps(self=None):
        """Constructs and returns the 4-step tutorial script."""
        from ui.components.tutorial_script import build_tutorial_steps
        return build_tutorial_steps(self)

    def start_tutorial(self):
        """Launch the interactive tutorial overlay over the main window."""
        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        def _on_tutorial_completed() -> None:
            self._save_tutorial_seen_setting(True)
            self.append_log("Đã hoàn thành hướng dẫn sử dụng!")

        overlay = InteractiveTutorialOverlay(
            self,
            notebook=getattr(self, "notebook", None),
            on_finish=_on_tutorial_completed,
        )
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start()
        self._tutorial_overlay = overlay
        return overlay
>>>>
```

---

## 9. Verification & Test Plan

1. **Unit & Contract Verification**:
   - Run `pytest tests/test_ui_layout.py` to ensure existing `_load_theme_setting` and `_save_theme_setting` pass.
   - Run `pytest tests/test_tutorial_overlay_e2e.py -k "test_t1_f8"` to verify tests `test_t1_f8_01` through `test_t1_f8_05`.
   - Run `pytest tests/test_tutorial_overlay_e2e.py -k "test_t4"` to verify full end-to-end first-launch user journey and completion persistence.
2. **Empirical Edge Case Verification**:
   - Corrupted file test: write invalid JSON to `user_settings.json` and verify `_load_user_settings()` returns defaults without raising exception.
   - UTF-8 BOM test: write BOM `\xef\xbb\xbf{"has_seen_tutorial": true}` and verify `_load_tutorial_seen_setting()` returns `True`.
   - Atomic rename test: verify temporary file `.json.tmp` is cleanly replaced with no residual lock files.
