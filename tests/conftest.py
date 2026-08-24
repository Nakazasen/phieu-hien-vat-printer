import os
import sys
from pathlib import Path
import pytest

# Ensure Tcl/Tk library paths are set for Windows Python environment
tcl_dir = os.path.join(sys.prefix, "tcl", "tcl8.6")
tk_dir = os.path.join(sys.prefix, "tcl", "tk8.6")
if os.path.isdir(tcl_dir):
    os.environ["TCL_LIBRARY"] = tcl_dir
if os.path.isdir(tk_dir):
    os.environ["TK_LIBRARY"] = tk_dir

# Isolate runtime paths and test fixtures for robust testing


@pytest.fixture(autouse=True)
def configure_tkinter_test_stability(monkeypatch: pytest.MonkeyPatch):
    """Patch CustomTkinter background timer callbacks and isolate Tkinter default root."""
    import gc
    import time
    import tkinter as tk
    import customtkinter as ctk

    # Prevent uncancelled 200ms titlebar icon after-timers from executing into destroyed Tcl interpreters
    monkeypatch.setattr(ctk.CTk, "_windows_set_titlebar_icon", lambda self: None)

    tk._default_root = None
    yield
    tk._default_root = None
    gc.collect()
    time.sleep(0.05)


@pytest.fixture
def tk_root():
    """Shared and reliably isolated CTk root window fixture for GUI tests."""
    import tkinter as tk
    import customtkinter as ctk

    try:
        root = ctk.CTk()
        root.geometry("1400x900+50+50")
        root.update_idletasks()
        root.update()
    except Exception as e:
        pytest.skip(f"Tkinter/Tcl display not available in this environment: {e}")

    yield root
    try:
        if root.winfo_exists():
            root.destroy()
    except Exception:
        pass



@pytest.fixture(autouse=True)
def isolate_test_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Isolate runtime data and output directories for every test to prevent lock contention."""
    data_dir = tmp_path / "isolated_app_data"
    output_dir = tmp_path / "isolated_app_output"
    data_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setenv("INPHIEUHIENVAT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("INPHIEUHIENVAT_OUTPUT_DIR", str(output_dir))


@pytest.fixture(autouse=True)
def mock_tkinter_messagebox(monkeypatch: pytest.MonkeyPatch):
    """Mock all tkinter.messagebox modal dialogs to prevent tests from hanging on user input."""
    import tkinter.messagebox as msgbox

    monkeypatch.setattr(msgbox, "showerror", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(msgbox, "showwarning", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(msgbox, "showinfo", lambda *args, **kwargs: "ok")
    monkeypatch.setattr(msgbox, "askyesno", lambda *args, **kwargs: True)
    monkeypatch.setattr(msgbox, "askokcancel", lambda *args, **kwargs: True)
    monkeypatch.setattr(msgbox, "askquestion", lambda *args, **kwargs: "yes")

