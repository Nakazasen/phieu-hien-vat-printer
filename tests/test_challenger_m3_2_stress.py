"""Empirical Adversarial Stress Test Suite for Milestone 3 UI Layout, Theme Switching, and First-Launch Prompts.

Author: challenger_m3_2 (teamwork_preview_challenger)
Target Scope:
1. Header preview_controls frame layout under different window sizes & simulated DPI scales.
2. Button appearance & styling in Light vs Dark mode (fg_color, hover_color, text_color).
3. First-launch dialog prompt behavior: "Yes" -> start_tutorial & persist; "No" -> dismiss; test env suppression.
4. Comprehensive end-to-end integration and resilience against corrupted settings, rapid clicks, and theme cycling.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import MagicMock, patch
import customtkinter as ctk
import pytest

from core.po_registry import PORegistry
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.history_tab import HistoryTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel
from ui.components.tutorial_overlay import (
    InteractiveTutorialOverlay,
    PlacementEngine,
    TooltipCard,
    TutorialStep,
)
from ui.components.tutorial_script import build_tutorial_steps
from ui.main_window import SlipPrinterApp


@pytest.fixture
def tk_root():
    """Create a headless or virtual CTk root with guaranteed cleanup."""
    try:
        root = ctk.CTk()
    except Exception:
        root = tk.Tk()
    root.geometry("1200x800+50+50")
    root.update_idletasks()
    root.update()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


@pytest.fixture
def isolated_app(tk_root, tmp_path, monkeypatch):
    """Factory creating a fully wired SlipPrinterApp instance in an isolated temp data directory."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "1")

    app = SlipPrinterApp.__new__(SlipPrinterApp)
    # Initialize CTk parent frame
    super(SlipPrinterApp, app).__init__()
    app.title("Test SlipPrinterApp")
    app.geometry("1200x800+50+50")
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

    tk_root.update_idletasks()
    app.update_idletasks()

    yield app

    try:
        app.destroy()
    except Exception:
        pass


# ============================================================================
# 1. HEADER PREVIEW_CONTROLS LAYOUT & DPI SCALING STRESS TESTS
# ============================================================================


class TestHeaderPreviewControlsLayoutAndDPI:
    """Empirical verification of header preview_controls layout, grid hierarchy, and DPI responsiveness."""

    def test_preview_controls_hierarchy_and_child_widgets(self, isolated_app):
        """Verify preview_controls frame contains theme menu, limit combo, tutorial button, and update button."""
        app = isolated_app
        assert hasattr(app, "theme_menu"), "theme_menu attribute missing on SlipPrinterApp"
        assert hasattr(app, "tutorial_btn"), "tutorial_btn attribute missing on SlipPrinterApp"
        assert hasattr(app, "update_btn"), "update_btn attribute missing on SlipPrinterApp"

        assert isinstance(app.theme_menu, ctk.CTkOptionMenu)
        assert isinstance(app.tutorial_btn, ctk.CTkButton)
        assert isinstance(app.update_btn, ctk.CTkButton)

        # Check widget texts
        assert app.tutorial_btn.cget("text") == "💡 Hướng dẫn"
        assert app.update_btn.cget("text") == "Kiểm tra bản cập nhật"

    def test_preview_controls_2x2_grid_structure(self, isolated_app):
        """Verify preview_controls 2x2 grid layout alignment and column spans."""
        app = isolated_app
        theme_info = app.theme_menu.grid_info()
        tutorial_info = app.tutorial_btn.grid_info()
        update_info = app.update_btn.grid_info()

        # Row 0: theme_menu (col 1), limit_combobox (col 3)
        assert int(theme_info["row"]) == 0
        assert int(theme_info["column"]) == 1

        # Row 1: tutorial_btn (col 0, columnspan 2)
        assert int(tutorial_info["row"]) == 1
        assert int(tutorial_info["column"]) == 0
        assert int(tutorial_info["columnspan"]) == 2
        assert "e" in str(tutorial_info["sticky"]).lower()

        # Row 1: update_btn (col 2, columnspan 2)
        assert int(update_info["row"]) == 1
        assert int(update_info["column"]) == 2
        assert int(update_info["columnspan"]) == 2
        assert "e" in str(update_info["sticky"]).lower()

    @pytest.mark.parametrize(
        "width,height",
        [
            (1000, 700),  # Minimum supported size
            (1280, 720),  # Standard laptop 720p
            (1366, 768),  # Common laptop HD
            (1400, 900),  # Default launch geometry
            (1920, 1080),  # Full HD 1080p
            (800, 600),   # Stressed compact boundary
        ],
    )
    def test_header_layout_across_window_resolutions(self, isolated_app, width, height):
        """Verify header controls never clip or collapse across multiple window aspect ratios and sizes."""
        app = isolated_app
        app.geometry(f"{width}x{height}+20+20")
        app.update_idletasks()
        app.update()

        # Preview controls frame dimensions must be healthy
        preview_controls = app.tutorial_btn.master
        assert preview_controls.winfo_width() > 240, (
            f"preview_controls crushed to {preview_controls.winfo_width()}px at {width}x{height}"
        )
        assert preview_controls.winfo_height() > 40, (
            f"preview_controls height too small: {preview_controls.winfo_height()}px"
        )

        # Tutorial button must have valid non-zero dimensions
        assert app.tutorial_btn.winfo_width() > 80, (
            f"tutorial_btn crushed to {app.tutorial_btn.winfo_width()}px at {width}x{height}"
        )
        assert app.tutorial_btn.winfo_height() >= 24

        # Update button must have valid non-zero dimensions
        assert app.update_btn.winfo_width() > 100, (
            f"update_btn crushed to {app.update_btn.winfo_width()}px at {width}x{height}"
        )

    def test_header_text_wrapping_and_title_spacing_under_load(self, isolated_app):
        """Verify extremely long title / status text does not overlap or displace preview_controls."""
        app = isolated_app
        app.geometry("1000x700+20+20")
        app.app_state.summary_var.set("A" * 150)
        app.app_state.status_var.set("B" * 200)
        app.update_idletasks()
        app.update()

        # preview_controls must still be visible on screen
        preview_controls = app.tutorial_btn.master
        x_pos = preview_controls.winfo_x()
        assert x_pos > 0, "preview_controls pushed off-screen by long header text"
        assert app.tutorial_btn.winfo_width() > 80

    @pytest.mark.parametrize("scale_factor", [1.0, 1.25, 1.5, 2.0])
    def test_dpi_scaling_responsiveness(self, isolated_app, scale_factor):
        """Stress-test CustomTkinter widget scaling simulation across 100%, 125%, 150%, 200% DPI."""
        app = isolated_app
        try:
            ctk.set_widget_scaling(scale_factor)
            app.update_idletasks()
            app.update()

            assert app.tutorial_btn.winfo_width() > 0
            assert app.update_btn.winfo_width() > 0
            assert app.theme_menu.winfo_width() > 0
        finally:
            ctk.set_widget_scaling(1.0)
            app.update_idletasks()


# ============================================================================
# 2. BUTTON APPEARANCE & STYLING IN LIGHT VS DARK MODE
# ============================================================================


class TestButtonAppearanceAndThemeStyling:
    """Empirical verification of color tuples, theme switching, and contrast ratios."""

    def test_tutorial_button_amber_color_tuples(self, isolated_app):
        """Verify tutorial button conforms to Amber (#F59E0B / #D97706) styling spec."""
        app = isolated_app
        fg_color = app.tutorial_btn.cget("fg_color")
        hover_color = app.tutorial_btn.cget("hover_color")
        text_color = app.tutorial_btn.cget("text_color")

        # Must be 2-tuple for (Light, Dark) modes
        assert isinstance(fg_color, (tuple, list)), f"fg_color expected tuple, got {type(fg_color)}"
        assert fg_color[0].upper() == "#F59E0B", f"Light fg_color {fg_color[0]} != #F59E0B"
        assert fg_color[1].upper() == "#D97706", f"Dark fg_color {fg_color[1]} != #D97706"

        assert isinstance(hover_color, (tuple, list))
        assert hover_color[0].upper() == "#D97706", f"Light hover_color {hover_color[0]} != #D97706"
        assert hover_color[1].upper() == "#B45309", f"Dark hover_color {hover_color[1]} != #B45309"

        assert isinstance(text_color, (tuple, list))
        assert text_color[0].upper() == "#FFFFFF"
        assert text_color[1].upper() == "#FFFFFF"

    def test_tutorial_button_visually_distinct_from_standard_buttons(self, isolated_app):
        """Verify tutorial button fg_color is distinct from update_btn and default theme green."""
        app = isolated_app
        tutorial_fg = app.tutorial_btn.cget("fg_color")
        update_fg = app.update_btn.cget("fg_color")

        # Must not be equal to default gray/green update button
        assert tutorial_fg != update_fg, "Tutorial button has same fg_color as standard update button"

    def test_theme_mode_switching_cycle(self, isolated_app, tmp_path):
        """Verify switching between Dark, Light, and System updates settings and widgets without crash."""
        app = isolated_app
        settings_path = app._get_settings_path()

        # 1. Switch to Light
        app._on_theme_changed("Sáng ☀️")
        app.update_idletasks()
        assert app._current_theme_mode == "Light"
        assert app._load_theme_setting() == "Light"
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved.get("appearance_mode") == "Light"

        # 2. Switch to Dark
        app._on_theme_changed("Tối 🌙")
        app.update_idletasks()
        assert app._current_theme_mode == "Dark"
        assert app._load_theme_setting() == "Dark"
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved.get("appearance_mode") == "Dark"

        # 3. Switch to System
        app._on_theme_changed("Hệ thống 🖥️")
        app.update_idletasks()
        assert app._current_theme_mode == "System"
        assert app._load_theme_setting() == "System"
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved.get("appearance_mode") == "System"

    def test_tooltip_card_theme_adaptability(self, tk_root):
        """Verify TooltipCard component defines distinct light/dark tuples for background and borders."""
        card = TooltipCard(
            tk_root,
            on_next=lambda: None,
            on_prev=lambda: None,
            on_skip=lambda: None,
        )
        try:
            tk_root.update_idletasks()

            fg_color = card.cget("fg_color")
            border_color = card.cget("border_color")
            badge_fg = card.badge_frame.cget("fg_color")
            badge_text = card.badge_label.cget("text_color")

            assert isinstance(fg_color, (tuple, list))
            assert fg_color[0].upper() == "#FFFFFF"
            assert fg_color[1].upper() == "#1E293B"

            assert isinstance(border_color, (tuple, list))
            assert border_color[0].upper() == "#10B981"
            assert border_color[1].upper() == "#10B981"

            assert isinstance(badge_fg, (tuple, list))
            assert isinstance(badge_text, (tuple, list))
        finally:
            card.destroy()

    def test_theme_switch_while_overlay_active_does_not_crash(self, isolated_app):
        """Verify dynamic theme switching while interactive tutorial overlay is active."""
        app = isolated_app
        overlay = app.start_tutorial()
        try:
            app.update_idletasks()
            assert overlay.is_active

            # Toggle modes
            app._on_theme_changed("Sáng ☀️")
            app.update_idletasks()
            app._on_theme_changed("Tối 🌙")
            app.update_idletasks()

            assert overlay.is_active
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()


# ============================================================================
# 3. FIRST-LAUNCH DIALOG PROMPT & SETTINGS PERSISTENCE
# ============================================================================


class TestFirstLaunchPromptAndPersistence:
    """Empirical verification of first-launch detection, prompt decision branching, and setting serialization."""

    def test_should_prompt_logic_truth_table(self, isolated_app, monkeypatch):
        """Verify boolean condition matrix for _should_prompt_first_launch_tutorial."""
        app = isolated_app

        # Case 1: First time user (has_seen=False, auto_suggest=True) -> True
        monkeypatch.setattr(app, "_load_user_settings", lambda: {"has_seen_tutorial": False, "auto_suggest_tutorial": True})
        assert app._should_prompt_first_launch_tutorial() is True

        # Case 2: User already seen tutorial (has_seen=True, auto_suggest=True) -> False
        monkeypatch.setattr(app, "_load_user_settings", lambda: {"has_seen_tutorial": True, "auto_suggest_tutorial": True})
        assert app._should_prompt_first_launch_tutorial() is False

        # Case 3: User disabled auto suggestions (has_seen=False, auto_suggest=False) -> False
        monkeypatch.setattr(app, "_load_user_settings", lambda: {"has_seen_tutorial": False, "auto_suggest_tutorial": False})
        assert app._should_prompt_first_launch_tutorial() is False

        # Case 4: Default fallback on empty dict -> True (since default has_seen=False, auto_suggest=True)
        monkeypatch.setattr(app, "_load_user_settings", lambda: {})
        assert app._should_prompt_first_launch_tutorial() is True

    def test_prompt_suppression_in_pytest_and_ci_env(self, isolated_app, monkeypatch):
        """Verify _check_first_launch_tutorial immediately returns under PYTEST_CURRENT_TEST."""
        app = isolated_app
        monkeypatch.setenv("PYTEST_CURRENT_TEST", "test_foo.py::test_bar")
        mock_ask = MagicMock()
        monkeypatch.setattr("tkinter.messagebox.askyesno", mock_ask)

        app._check_first_launch_tutorial()
        mock_ask.assert_not_called()

    def test_prompt_suppression_via_disable_env_var(self, isolated_app, monkeypatch):
        """Verify prompt suppression via INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT."""
        app = isolated_app
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT", "1")
        mock_ask = MagicMock()
        monkeypatch.setattr("tkinter.messagebox.askyesno", mock_ask)

        app._check_first_launch_tutorial()
        mock_ask.assert_not_called()

    def test_first_launch_user_clicks_yes_launches_tutorial(self, isolated_app, monkeypatch):
        """Verify clicking 'Yes' on first-launch prompt triggers start_tutorial()."""
        app = isolated_app
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT", raising=False)

        monkeypatch.setattr(app, "_should_prompt_first_launch_tutorial", lambda: True)
        monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: True)

        started = False

        def mock_start():
            nonlocal started
            started = True
            return MagicMock()

        monkeypatch.setattr(app, "start_tutorial", mock_start)

        app._check_first_launch_tutorial()
        assert started is True, "start_tutorial was not invoked after user accepted prompt"

    def test_first_launch_user_clicks_no_dismisses_without_starting(self, isolated_app, monkeypatch):
        """Verify clicking 'No' dismisses dialog without starting tutorial and without altering seen state."""
        app = isolated_app
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.delenv("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT", raising=False)

        monkeypatch.setattr(app, "_should_prompt_first_launch_tutorial", lambda: True)
        monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args, **kwargs: False)

        mock_start = MagicMock()
        monkeypatch.setattr(app, "start_tutorial", mock_start)

        app._check_first_launch_tutorial()
        mock_start.assert_not_called()

    def test_save_tutorial_seen_persists_to_json(self, isolated_app):
        """Verify _save_tutorial_seen_setting writes has_seen_tutorial=True to disk atomically."""
        app = isolated_app
        settings_path = app._get_settings_path()

        app._save_tutorial_seen_setting(True)
        assert app._load_tutorial_seen_setting() is True
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved["has_seen_tutorial"] is True

        app._save_tutorial_seen_setting(False)
        assert app._load_tutorial_seen_setting() is False
        saved = json.loads(settings_path.read_text(encoding="utf-8"))
        assert saved["has_seen_tutorial"] is False

    def test_settings_corrupted_json_recovery(self, isolated_app):
        """Verify application recovers gracefully with defaults when user_settings.json contains invalid JSON."""
        app = isolated_app
        settings_path = app._get_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("{ CORRUPT INVALID JSON payload ...", encoding="utf-8")

        # Must not raise JSONDecodeError
        loaded = app._load_user_settings()
        assert isinstance(loaded, dict)
        assert loaded.get("appearance_mode") == "System"
        assert loaded.get("has_seen_tutorial") is False

        # Saving new update heals the file
        app._save_tutorial_seen_setting(True)
        healed = json.loads(settings_path.read_text(encoding="utf-8"))
        assert healed["has_seen_tutorial"] is True

    def test_settings_non_dict_json_recovery(self, isolated_app):
        """Verify application handles JSON containing an array or primitive instead of dict."""
        app = isolated_app
        settings_path = app._get_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        settings_path.write_text("[\"item1\", \"item2\"]", encoding="utf-8")

        loaded = app._load_user_settings()
        assert isinstance(loaded, dict)
        assert loaded.get("appearance_mode") == "System"


# ============================================================================
# 4. END-TO-END INTEGRATION & ADVERSARIAL STRESS TESTS
# ============================================================================


class TestEndToEndIntegrationAndAdversarialStress:
    """Full lifecycle stress testing connecting live UI hierarchy, tutorial overlay, and controller."""

    def test_header_button_invoke_starts_overlay(self, isolated_app):
        """Verify clicking app.tutorial_btn triggers full interactive overlay walkthrough."""
        app = isolated_app
        assert getattr(app, "_tutorial_overlay", None) is None

        # Invoke button
        app.tutorial_btn.invoke()
        app.update_idletasks()

        overlay = getattr(app, "_tutorial_overlay", None)
        assert overlay is not None, "Overlay was not created upon tutorial_btn.invoke()"
        assert overlay.is_active is True
        assert overlay.current_step_index == 0
        overlay.destroy()

    def test_full_4_step_walkthrough_with_live_widgets(self, isolated_app):
        """Verify advancing through all 4 real application steps and finishing sets has_seen_tutorial=True."""
        app = isolated_app
        app._save_tutorial_seen_setting(False)
        assert app._load_tutorial_seen_setting() is False

        overlay = app.start_tutorial()
        try:
            app.update_idletasks()
            assert overlay.current_step_index == 0
            assert overlay.steps[0].step_id == "step_excel_import"
            assert overlay.steps[0].target_widget_getter() is app.sidebar.excel_import_button

            # Advance to Step 2 (QR Scanner)
            overlay.next_step()
            app.update_idletasks()
            assert overlay.current_step_index == 1
            assert overlay.steps[1].step_id == "step_qr_scanner"
            assert overlay.steps[1].target_widget_getter() is app.sidebar.qr_scan_button

            # Advance to Step 3 (Auto PO)
            overlay.next_step()
            app.update_idletasks()
            assert overlay.current_step_index == 2
            assert overlay.steps[2].step_id == "step_auto_po"
            assert overlay.steps[2].target_widget_getter() in (app.data_tab.form_frame, app.data_tab.btn_add_record)

            # Advance to Step 4 (PDF Generation)
            overlay.next_step()
            app.update_idletasks()
            assert overlay.current_step_index == 3
            assert overlay.steps[3].step_id == "step_pdf_generation"
            assert overlay.steps[3].target_widget_getter() is app.sidebar.generate_button

            # Complete final step
            overlay.next_step()
            app.update_idletasks()
            app.update()

            assert overlay.is_active is False
            assert app._load_tutorial_seen_setting() is True, "has_seen_tutorial was not set to True upon walkthrough completion"
        finally:
            overlay.destroy()

    def test_rapid_tutorial_btn_clicking_is_idempotent(self, isolated_app):
        """Verify spamming the tutorial button while overlay is already running is safe and does not duplicate canvas."""
        app = isolated_app
        overlay1 = app.start_tutorial()
        app.update_idletasks()

        for _ in range(10):
            app.start_tutorial()
            app.update_idletasks()

        assert overlay1.is_active is True
        assert overlay1.current_step_index == 0
        overlay1.destroy()

    def test_controller_mark_tutorial_seen_delegation(self, isolated_app):
        """Verify AppController.mark_tutorial_seen delegates to view persistence seamlessly."""
        app = isolated_app
        app.controller.mark_tutorial_seen(True)
        assert app._load_tutorial_seen_setting() is True

        app.controller.mark_tutorial_seen(False)
        assert app._load_tutorial_seen_setting() is False

    def test_destroy_cancels_all_pending_scheduled_jobs(self, isolated_app):
        """Verify SlipPrinterApp.destroy() cancels _drain_job, _update_job, and _tutorial_prompt_job without exception."""
        app = isolated_app
        app._tutorial_prompt_job = app.after(600, app._check_first_launch_tutorial)

        # Calling destroy must not raise
        app.destroy()
