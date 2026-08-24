"""Empirical Stress Test Suite by Challenger for Milestone 3 (UI Integration & Persistence).

Targeted Stress Areas:
1. Corrupt JSON data in `user_settings.json` (syntax errors, empty files, random bytes, UTF-8 BOM, non-dict types, missing keys).
2. Atomic save resilience under simulated IO errors, unwritable directory, and fallback mechanisms.
3. Idempotency and re-entrancy of `start_tutorial()` under rapid clicking and active overlay state.
4. Timer cancellation when `destroy()` is invoked immediately after window initialization.
5. Verification of `is_tutorial_seen()` and `mark_tutorial_seen()` state transitions (headless and live UI).
"""

from __future__ import annotations

import codecs
import json
import os
import time
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch
import pytest
import tkinter as tk
import customtkinter as ctk

from core.runtime_paths import AppPaths
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.tutorial_overlay import InteractiveTutorialOverlay
from ui.main_window import SlipPrinterApp


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def temp_paths(tmp_path: Path) -> AppPaths:
    """Create isolated AppPaths in a temporary directory."""
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "template.pdf").write_bytes(b"%PDF-1.4 mock")
    (bundle / "app_icon.ico").write_bytes(b"\x00\x00\x01\x00")
    (bundle / "user_guide.pptx").write_bytes(b"PK mock pptx")

    data = tmp_path / "data"
    data.mkdir()

    output = tmp_path / "output"
    output.mkdir()

    install = tmp_path / "install"
    install.mkdir()

    return AppPaths(
        bundle_dir=bundle,
        data_dir=data,
        output_dir=output,
        installation_dir=install,
        template_path=bundle / "template.pdf",
        layout_path=data / "layout_config.json",
        registry_path=data / "po_registry.db",
    )



@pytest.fixture
def headless_controller(temp_paths: AppPaths) -> tuple[AppController, AppState]:
    """Create an AppController and AppState without a live Tk root."""
    try:
        root = tk.Tk()
        root.withdraw()
    except Exception:
        pytest.skip("Tkinter display environment unavailable")
    state = AppState(root=root, paths=temp_paths)
    controller = AppController(state)
    yield controller, state
    state.po_registry.close()
    try:
        root.destroy()
    except Exception:
        pass



@pytest.fixture
def tk_app(temp_paths: AppPaths):
    """Create a live SlipPrinterApp with isolated temp paths."""
    with patch("ui.main_window.prepare_runtime_paths", return_value=temp_paths):
        # Disable update checking and tutorial prompt during fixture creation
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1", "INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT": "1"}):
            try:
                app = SlipPrinterApp()
            except Exception:
                pytest.skip("Tkinter/CustomTkinter display environment unavailable")
            app.update_idletasks()
            yield app
            try:
                app.destroy()
            except Exception:
                pass


# ============================================================================
# 1. CORRUPT JSON DATA IN user_settings.json
# ============================================================================


class TestCorruptJsonSettingsResilience:
    """Stress tests loading corrupt, malformed, or unusual user_settings.json files."""

    def test_settings_load_defaults_when_file_missing(self, headless_controller: tuple[AppController, AppState]):
        """Verify defaults are loaded when user_settings.json does not exist."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        assert not settings_file.exists()

        assert controller.is_tutorial_seen() is False

    def test_settings_load_with_corrupt_syntax_trailing_comma(self, headless_controller: tuple[AppController, AppState]):
        """Verify JSON syntax error (trailing comma) falls back to defaults without crash."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        settings_file.write_text('{\n  "has_seen_tutorial": true,\n}', encoding="utf-8")

        assert controller.is_tutorial_seen() is False

    def test_settings_load_with_corrupt_truncated_json(self, headless_controller: tuple[AppController, AppState]):
        """Verify truncated/half-written JSON file safely falls back to defaults."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        settings_file.write_text('{"has_seen_tutorial": tru', encoding="utf-8")

        assert controller.is_tutorial_seen() is False

    def test_settings_load_with_empty_zero_byte_file(self, headless_controller: tuple[AppController, AppState]):
        """Verify 0-byte empty file safely falls back to defaults."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        settings_file.write_bytes(b"")

        assert controller.is_tutorial_seen() is False

    def test_settings_load_with_random_binary_garbage(self, headless_controller: tuple[AppController, AppState]):
        """Verify arbitrary binary garbage falls back to defaults."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        settings_file.write_bytes(b"\x00\xff\xfe\x12\x89\xab\xcd\xef\x00\x00\x01\x00")

        assert controller.is_tutorial_seen() is False

    def test_settings_load_with_utf8_bom(self, headless_controller: tuple[AppController, AppState]):
        """Verify UTF-8 BOM encoded JSON is parsed correctly (has_seen_tutorial=True)."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"
        payload = json.dumps({"has_seen_tutorial": True, "appearance_mode": "Dark"}).encode("utf-8")
        settings_file.write_bytes(codecs.BOM_UTF8 + payload)

        assert controller.is_tutorial_seen() is True

    def test_settings_load_with_valid_json_non_dict_types(self, headless_controller: tuple[AppController, AppState]):
        """Verify valid JSON literals that are not dicts (list, string, int, boolean, null) fall back to defaults."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"

        non_dict_payloads = [
            json.dumps(["has_seen_tutorial", True]),
            json.dumps("some string"),
            json.dumps(12345),
            json.dumps(True),
            json.dumps(None),
        ]

        for payload in non_dict_payloads:
            settings_file.write_text(payload, encoding="utf-8")
            assert controller.is_tutorial_seen() is False, f"Failed on payload: {payload}"

    def test_settings_load_with_missing_keys_preserves_defaults(self, tk_app: SlipPrinterApp):
        """Verify loading JSON with partial keys retains default values for missing keys."""
        settings_file = tk_app._get_settings_path()
        settings_file.write_text(json.dumps({"appearance_mode": "Light"}), encoding="utf-8")

        loaded = tk_app._load_user_settings()
        assert loaded["appearance_mode"] == "Light"
        assert loaded["has_seen_tutorial"] is False
        assert loaded["auto_suggest_tutorial"] is True

    def test_settings_load_with_invalid_theme_mode_fallback(self, tk_app: SlipPrinterApp):
        """Verify invalid appearance_mode values fallback to 'System'."""
        settings_file = tk_app._get_settings_path()
        settings_file.write_text(json.dumps({"appearance_mode": "UltraVioletNeon"}), encoding="utf-8")

        mode = tk_app._load_theme_setting()
        assert mode == "System"


# ============================================================================
# 2. ATOMIC SAVE RESILIENCE & IO ERROR SIMULATION
# ============================================================================


class TestAtomicSaveResilience:
    """Stress tests persistence layer under simulated IO failures and concurrent operations."""

    def test_atomic_save_creates_clean_file(self, tk_app: SlipPrinterApp):
        """Verify saving settings produces a valid, pretty-printed JSON file."""
        tk_app._save_user_settings({"has_seen_tutorial": True, "appearance_mode": "Dark"})
        settings_file = tk_app._get_settings_path()

        assert settings_file.is_file()
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["has_seen_tutorial"] is True
        assert data["appearance_mode"] == "Dark"
        assert data["auto_suggest_tutorial"] is True

    def test_atomic_save_fallback_on_os_replace_failure(self, tk_app: SlipPrinterApp):
        """Verify fallback direct write executes when os.replace raises OSError."""
        settings_file = tk_app._get_settings_path()

        with patch("os.replace", side_effect=OSError("Simulated cross-device link or locked file")):
            tk_app._save_user_settings({"has_seen_tutorial": True})

        assert settings_file.is_file()
        data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert data["has_seen_tutorial"] is True

    def test_atomic_save_resilience_on_unwritable_directory(self, tk_app: SlipPrinterApp):
        """Verify saving to an unwritable directory or throwing Exception does not crash."""
        with patch("pathlib.Path.write_text", side_effect=PermissionError("Access denied")):
            # Must not raise
            try:
                tk_app._save_user_settings({"has_seen_tutorial": True})
            except Exception as exc:
                pytest.fail(f"_save_user_settings raised unexpected exception: {exc}")

    def test_atomic_save_100_rapid_merges(self, tk_app: SlipPrinterApp):
        """Stress-test: 100 rapid consecutive settings merges preserving existing fields."""
        for i in range(100):
            if i % 2 == 0:
                tk_app._save_theme_setting("Dark" if i % 4 == 0 else "Light")
            else:
                tk_app._save_tutorial_seen_setting(seen=(i % 3 == 0))

        settings = tk_app._load_user_settings()
        assert "appearance_mode" in settings
        assert "has_seen_tutorial" in settings
        assert "auto_suggest_tutorial" in settings

    def test_headless_mark_tutorial_seen_atomic_persistence(self, headless_controller: tuple[AppController, AppState]):
        """Verify AppController.mark_tutorial_seen persists atomically without live view."""
        controller, state = headless_controller
        settings_file = state.paths.data_dir / "user_settings.json"

        controller.mark_tutorial_seen(True)
        assert settings_file.is_file()
        assert controller.is_tutorial_seen() is True

        controller.mark_tutorial_seen(False)
        assert controller.is_tutorial_seen() is False


# ============================================================================
# 3. IDEMPOTENCY & RE-ENTRANCY OF start_tutorial()
# ============================================================================


class TestStartTutorialIdempotencyAndReentrancy:
    """Stress tests start_tutorial() re-entrancy, rapid clicking, and active overlay management."""

    def test_start_tutorial_creates_active_overlay(self, tk_app: SlipPrinterApp):
        """Verify start_tutorial() instantiates InteractiveTutorialOverlay and sets _tutorial_overlay."""
        overlay = tk_app.start_tutorial()
        tk_app.update_idletasks()

        try:
            assert overlay is not None
            assert tk_app._tutorial_overlay is overlay
            assert overlay.is_active is True
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_50_rapid_start_tutorial_clicks_reentrancy(self, tk_app: SlipPrinterApp):
        """Stress-test: Calling start_tutorial() 50 times in a tight loop does not leak overlays or crash."""
        initial_overlay = tk_app.start_tutorial()
        tk_app.update_idletasks()

        try:
            for _ in range(50):
                overlay = tk_app.start_tutorial()
                assert overlay is initial_overlay
                assert overlay.is_active is True
                assert overlay.current_step_index == 0
        finally:
            initial_overlay.destroy()

    def test_start_tutorial_while_overlay_at_later_step_resets_to_zero(self, tk_app: SlipPrinterApp):
        """Verify re-invoking start_tutorial() when overlay is at Step 3 cleanly resets to Step 0."""
        overlay = tk_app.start_tutorial()
        tk_app.update_idletasks()

        try:
            overlay.next_step()  # Step 1
            overlay.next_step()  # Step 2
            assert overlay.current_step_index == 2

            # User clicks "💡 Hướng dẫn" button again while on Step 3
            restarted = tk_app.start_tutorial()
            tk_app.update_idletasks()

            assert restarted is overlay
            assert restarted.is_active is True
            assert restarted.current_step_index == 0
        finally:
            overlay.destroy()

    def test_start_tutorial_after_overlay_destroyed_creates_new_instance(self, tk_app: SlipPrinterApp):
        """Verify calling start_tutorial() after destroying previous overlay creates a fresh overlay."""
        overlay1 = tk_app.start_tutorial()
        tk_app.update_idletasks()
        overlay1.destroy()
        assert overlay1.is_active is False

        overlay2 = tk_app.start_tutorial()
        tk_app.update_idletasks()
        try:
            assert overlay2 is not None
            assert overlay2.is_active is True
            assert overlay2 is not overlay1
        finally:
            overlay2.destroy()

    def test_controller_start_tutorial_delegates_to_view(self, tk_app: SlipPrinterApp):
        """Verify AppController.start_tutorial() properly triggers view.start_tutorial()."""
        overlay = tk_app.controller.start_tutorial()
        tk_app.update_idletasks()
        try:
            assert overlay is not None
            assert overlay.is_active is True
        finally:
            overlay.destroy()


# ============================================================================
# 4. TIMER CANCELLATION AND IMMEDIATE WINDOW DESTROY
# ============================================================================


class TestWindowDestroyAndTimerCancellation:
    """Stress tests immediate destroy() during/after initialization to prevent stale timer leaks."""

    def test_immediate_destroy_after_init_no_tcl_error(self, temp_paths: AppPaths):
        """Stress-test: Initialize SlipPrinterApp and immediately destroy() in same turn (0ms delay)."""
        with patch("ui.main_window.prepare_runtime_paths", return_value=temp_paths):
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}):
                app = SlipPrinterApp()
                # Destroy immediately before any scheduled jobs fire
                app.destroy()
                # Flush pending events to ensure no scheduled timer throws TclError
                try:
                    app.update()
                except Exception:
                    pass

    def test_destroy_cancels_all_scheduled_jobs(self, temp_paths: AppPaths):
        """Verify that destroy() calls after_cancel on _drain_job, _update_job, and _tutorial_prompt_job."""
        with patch("ui.main_window.prepare_runtime_paths", return_value=temp_paths):
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}):
                app = SlipPrinterApp()
                assert hasattr(app, "_drain_job")
                assert hasattr(app, "_update_job")
                assert hasattr(app, "_tutorial_prompt_job")

                with patch.object(app, "after_cancel", wraps=app.after_cancel) as mock_cancel:
                    app.destroy()
                    assert mock_cancel.call_count >= 3

    def test_50_consecutive_app_destroy_calls_idempotency(self, temp_paths: AppPaths):
        """Verify calling destroy() 50 times on SlipPrinterApp is safe and idempotent."""
        with patch("ui.main_window.prepare_runtime_paths", return_value=temp_paths):
            with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "1"}):
                app = SlipPrinterApp()
                for _ in range(50):
                    try:
                        app.destroy()
                    except Exception as exc:
                        pytest.fail(f"Consecutive destroy() failed: {exc}")

    def test_destroy_while_overlay_active_cleans_up(self, tk_app: SlipPrinterApp):
        """Verify destroying SlipPrinterApp while tutorial overlay is actively rendered cleans up cleanly."""
        overlay = tk_app.start_tutorial()
        tk_app.update_idletasks()
        assert overlay.is_active is True

        tk_app.destroy()
        # Overlay should no longer be active or throw errors
        assert overlay.is_active is False or overlay.master is None


# ============================================================================
# 5. STATE TRANSITIONS (is_tutorial_seen & mark_tutorial_seen)
# ============================================================================


class TestTutorialStateTransitions:
    """Stress tests state transitions and prompt decision logic."""

    def test_state_transitions_cycle(self, tk_app: SlipPrinterApp):
        """Verify state transitions: False -> True -> False -> True."""
        assert tk_app._load_tutorial_seen_setting() is False
        assert tk_app.controller.is_tutorial_seen() is False

        # Transition 1: Mark seen
        tk_app._save_tutorial_seen_setting(True)
        assert tk_app._load_tutorial_seen_setting() is True
        assert tk_app.controller.is_tutorial_seen() is True

        # Transition 2: Mark unseen
        tk_app._save_tutorial_seen_setting(False)
        assert tk_app._load_tutorial_seen_setting() is False
        assert tk_app.controller.is_tutorial_seen() is False

        # Transition 3: Mark seen via controller
        tk_app.controller.mark_tutorial_seen(True)
        assert tk_app._load_tutorial_seen_setting() is True
        assert tk_app.controller.is_tutorial_seen() is True

    def test_should_prompt_first_launch_tutorial_truth_table(self, tk_app: SlipPrinterApp):
        """Verify _should_prompt_first_launch_tutorial under all (has_seen, auto_suggest) permutations."""
        # Permutation 1: has_seen=False, auto_suggest=True -> PROMPT (True)
        tk_app._save_user_settings({"has_seen_tutorial": False, "auto_suggest_tutorial": True})
        assert tk_app._should_prompt_first_launch_tutorial() is True

        # Permutation 2: has_seen=True, auto_suggest=True -> NO PROMPT (False)
        tk_app._save_user_settings({"has_seen_tutorial": True, "auto_suggest_tutorial": True})
        assert tk_app._should_prompt_first_launch_tutorial() is False

        # Permutation 3: has_seen=False, auto_suggest=False -> NO PROMPT (False)
        tk_app._save_user_settings({"has_seen_tutorial": False, "auto_suggest_tutorial": False})
        assert tk_app._should_prompt_first_launch_tutorial() is False

        # Permutation 4: has_seen=True, auto_suggest=False -> NO PROMPT (False)
        tk_app._save_user_settings({"has_seen_tutorial": True, "auto_suggest_tutorial": False})
        assert tk_app._should_prompt_first_launch_tutorial() is False

    def test_tutorial_completion_automatically_saves_seen_state(self, tk_app: SlipPrinterApp):
        """Verify completing the tutorial triggers _on_finish and marks has_seen_tutorial=True."""
        tk_app._save_tutorial_seen_setting(False)
        assert tk_app._load_tutorial_seen_setting() is False

        overlay = tk_app.start_tutorial()
        tk_app.update_idletasks()

        try:
            # Advance through all 4 steps to finish
            overlay.next_step()  # 1 -> 2
            overlay.next_step()  # 2 -> 3
            overlay.next_step()  # 3 -> 4
            overlay.next_step()  # 4 -> finish
            tk_app.update_idletasks()

            assert tk_app._load_tutorial_seen_setting() is True
            assert tk_app.controller.is_tutorial_seen() is True
        finally:
            overlay.destroy()
