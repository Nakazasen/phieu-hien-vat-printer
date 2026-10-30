"""Tests for the 6-chapter Real-User Visual Guide (VisualUserGuideWindow, ImageZoomDialog, and assets)."""
from __future__ import annotations

import tkinter as tk
from unittest.mock import patch
import customtkinter as ctk
import pytest

from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.user_guide_content import USER_GUIDE_CHAPTERS, get_user_guide_assets_dir
from ui.components.user_guide_dialog import ImageZoomDialog, VisualUserGuideWindow
from ui.main_window import SlipPrinterApp


@pytest.fixture
def tk_root():
    try:
        root = ctk.CTk()
    except Exception:
        root = tk.Tk()
    root.geometry("1200x800+40+40")
    root.update_idletasks()
    root.update()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def isolated_app(tk_root, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    app = SlipPrinterApp.__new__(SlipPrinterApp)
    super(SlipPrinterApp, app).__init__()
    app.title("Test SlipPrinterApp")
    app.geometry("1200x800+40+40")
    app.minsize(1000, 700)

    app.app_state = AppState(app)
    app.controller = AppController(app.app_state)
    app.controller.set_view(app)
    app.sidebar_width = 360
    app._init_theme_mode()
    app._build_layout()
    app.protocol("WM_DELETE_WINDOW", app.controller.on_close)
    app._drain_job = app.after(150, app._drain_event_queue)
    app._tutorial_prompt_job = None
    app._user_guide_window = None

    app.update_idletasks()
    yield app
    try:
        app.destroy()
    except Exception:
        pass


def test_user_guide_assets_and_chapters_complete():
    """Verify all 6 chapters, annotated PNG screenshots, HTML manual, and PDF manual exist and are non-empty."""
    assets_dir = get_user_guide_assets_dir()
    assert assets_dir.is_dir(), f"Missing user_guide assets directory: {assets_dir}"
    assert len(USER_GUIDE_CHAPTERS) == 6

    for idx, ch in enumerate(USER_GUIDE_CHAPTERS):
        assert ch["id"] == f"ch0{idx + 1}"
        assert ch["title"]
        assert ch["summary"]
        assert len(ch["steps"]) >= 3
        assert len(ch["tips"]) >= 2
        img_path = assets_dir / ch["image_filename"]
        assert img_path.is_file(), f"Missing screenshot for {ch['id']}: {img_path}"
        assert img_path.stat().st_size > 50_000, f"Screenshot too small: {img_path}"

    html_path = assets_dir / "huong_dan_su_dung.html"
    pdf_path = assets_dir / "Huong_Dan_Su_Dung_InPhieuHienVat.pdf"
    assert html_path.is_file() and html_path.stat().st_size > 100_000
    assert pdf_path.is_file() and pdf_path.stat().st_size > 100_000


def test_visual_user_guide_window_navigation_and_search(isolated_app):
    """Verify VisualUserGuideWindow opens via tutorial_btn, navigates chapters, filters via search, and jumps tabs."""
    app = isolated_app
    assert app._tutorial_prompt_job is None

    app.tutorial_btn.invoke()
    app.update_idletasks()

    guide: VisualUserGuideWindow = app._user_guide_window
    assert isinstance(guide, VisualUserGuideWindow)
    assert guide.is_active is True
    assert guide.current_chapter_index == 0

    # Master window must never be disabled
    try:
        disabled_flag = int(app.attributes("-disabled"))
    except Exception:
        disabled_flag = 0
    assert disabled_flag == 0

    # Navigate forward and backward
    guide.next_chapter()
    app.update_idletasks()
    assert guide.current_chapter_index == 1

    guide.select_chapter(2)  # Chapter 3: QR Scan (target_tab_index = 3)
    app.update_idletasks()
    assert guide.current_chapter_index == 2
    guide.jump_to_target_tab()
    app.update_idletasks()
    assert app.notebook.index(app.notebook.select()) == 3

    # Search filter
    guide.search_var.set("Tách CAV")
    guide._on_search_changed()
    app.update_idletasks()
    assert 1 in guide.filtered_indices

    # Clear search
    guide.search_var.set("")
    guide._on_search_changed()
    app.update_idletasks()
    assert len(guide.filtered_indices) == 6

    # Zoom dialog
    guide.open_zoom_dialog()
    app.update_idletasks()
    assert isinstance(guide._zoom_dialog, ImageZoomDialog)
    assert guide._zoom_dialog.winfo_exists()
    guide._zoom_dialog._set_zoom(1.25)
    app.update_idletasks()
    guide._zoom_dialog.destroy()

    # HTML / PDF launchers with mocked webbrowser/startfile
    with patch("webbrowser.open", return_value=True) as mock_wb:
        assert guide.open_html_manual() is True
        mock_wb.assert_called_once()

    guide.close_guide()
    app.update_idletasks()
    assert guide.is_active is False
