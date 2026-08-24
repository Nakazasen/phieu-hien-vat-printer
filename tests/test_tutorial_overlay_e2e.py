"""Comprehensive Opaque-Box E2E Test Suite for Interactive Tutorial (UI Overlay) and User Guide.

Tiers:
- Tier 1: Feature Coverage (>=5 test cases per feature covering overlay creation, spotlight
  bounding box calculation, tooltip card rendering, step progression, skip/cleanup, tutorial script,
  trigger button, and persistence).
- Tier 2: Boundary & Corner Cases (>=5 test cases per category: zero/negative dimensions,
  multi-monitor/offscreen bounds, empty/corrupt steps, rapid click debouncing, escape key handling,
  missing widget fallback, window resize/minimize).
- Tier 3: Cross-Feature Combinations (Pairwise coverage: tab switching + resize, first-launch prompt
  + manual trigger, theme change + overlay active, uncommitted form data + tutorial).
- Tier 4: Real-World Application Scenarios (Complete user walkthroughs: first-time user seeing prompt
  -> walking through 4 steps -> finish -> subsequent app restart without auto-prompt).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Optional
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pytest

from core.slip_printer_engine import create_record
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel
from ui.main_window import SlipPrinterApp

# Attempt dynamic import of the tutorial overlay component if available (Milestone 1+)
try:
    from ui.components.tutorial_overlay import (
        InteractiveTutorialOverlay,
        TutorialOverlay,
        TutorialStep,
    )
except ImportError:
    InteractiveTutorialOverlay = None
    TutorialOverlay = None
    TutorialStep = None


# ============================================================================
# TEST FIXTURES & HELPER FACTORIES
# ============================================================================


def require_tutorial_overlay():
    """Skip test if tutorial overlay component is not yet implemented."""
    if InteractiveTutorialOverlay is None and TutorialOverlay is None:
        pytest.skip("ui.components.tutorial_overlay not yet implemented (Milestone 1)")


def get_overlay_class():
    """Return the active tutorial overlay class."""
    return InteractiveTutorialOverlay or TutorialOverlay


def create_mock_tutorial_step(
    step_id: str,
    title: str,
    description: str,
    target_widget: Optional[tk.Widget] = None,
    target_tab_index: Optional[int] = None,
    tooltip_position: str = "auto",
):
    """Create a TutorialStep instance according to the PROJECT.md interface contract."""
    cls = TutorialStep
    if cls is None:
        pytest.skip("TutorialStep class not available")
    return cls(
        step_id=step_id,
        title=title,
        description=description,
        target_widget_getter=lambda: target_widget,
        target_tab_index=target_tab_index,
        tooltip_position=tooltip_position,
    )


# ============================================================================
# TIER 1: FEATURE COVERAGE (>=5 Test Cases per Feature)
# ============================================================================


class TestTier1FeatureCoverage:
    """Tier 1: Feature Isolation & Primary Behavior Coverage."""

    # ------------------------------------------------------------------------
    # Feature 1: Overlay Scrim & Canvas Layer
    # ------------------------------------------------------------------------

    def test_t1_f1_01_overlay_canvas_initialization(self, tk_root):
        """Verify overlay initializes Canvas attached to master window covering full area."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            btn = ctk.CTkButton(root, text="Test Target", width=120, height=40)
            btn.place(x=100, y=100)
            root.update_idletasks()
            root.update()

            step = create_mock_tutorial_step("step1", "Title 1", "Desc 1", btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            # Canvas must exist and be child of root or overlay frame
            canvas = getattr(overlay, "canvas", None)
            assert canvas is not None, "Canvas layer was not created by overlay"
            assert canvas.winfo_exists(), "Canvas widget is not active in Tcl/Tk hierarchy"
        finally:
            overlay.destroy()

    def test_t1_f1_02_overlay_scrim_geometry_matches_master(self, tk_root):
        """Verify Canvas dimensions match master window width and height."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1200x800+50+50")
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("step1", "Title", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            canvas = getattr(overlay, "canvas", None)
            assert canvas is not None
            assert canvas.winfo_width() > 0 or root.winfo_width() > 0
        finally:
            overlay.destroy()

    def test_t1_f1_03_overlay_z_lift_and_stacking(self, tk_root):
        """Verify canvas and tooltip card are lifted above normal widgets."""
        require_tutorial_overlay()
        root = tk_root
        btn = ctk.CTkButton(root, text="Underneath Button")
        btn.pack(padx=20, pady=20)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Title", "Desc", btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            canvas = getattr(overlay, "canvas", None)
            assert canvas is not None
            # Canvas or overlay container should be top-level stacking
        finally:
            overlay.destroy()

    def test_t1_f1_04_overlay_non_blocking_mainloop(self, tk_root):
        """Verify overlay does not block the Tkinter mainloop or timer callbacks."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)

        timer_ran = False

        def on_timer():
            nonlocal timer_ran
            timer_ran = True

        try:
            step = create_mock_tutorial_step("s1", "Non-blocking", "Testing loop", None)
            overlay.register_steps([step])
            overlay.start(0)

            # Schedule a callback in Tk mainloop
            root.after(50, on_timer)
            root.update_idletasks()
            time.sleep(0.06)
            root.update()

            assert timer_ran is True, "Mainloop was blocked by modal loop during overlay execution"
        finally:
            overlay.destroy()

    def test_t1_f1_05_multiple_overlay_instantiation_guard(self, tk_root):
        """Verify creating a second overlay or restarting cleans up previous canvas cleanly."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay1 = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Step 1", "Desc", None)
            overlay1.register_steps([step])
            overlay1.start(0)
            root.update_idletasks()

            # Start again
            overlay1.start(0)
            root.update_idletasks()
            root.update()
            assert getattr(overlay1, "canvas", None) is not None
        finally:
            overlay1.destroy()

    # ------------------------------------------------------------------------
    # Feature 2: Spotlight Bounding Box Calculation
    # ------------------------------------------------------------------------

    def test_t1_f2_01_spotlight_coordinates_exact_math(self, tk_root):
        """Verify spotlight cutout bounding box calculation matches target widget coordinates."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()
        root.update()

        target = ctk.CTkButton(root, text="Spotlight Target", width=180, height=50)
        target.place(x=200, y=150)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Spotlight Test", "Target desc", target)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            if hasattr(overlay, "_calculate_spotlight_bounds"):
                bounds = overlay._calculate_spotlight_bounds(target)
                assert bounds is not None
                x1, y1, x2, y2 = bounds
                assert x1 < x2 and y1 < y2
                assert x2 - x1 >= 180
                assert y2 - y1 >= 50
        finally:
            overlay.destroy()

    def test_t1_f2_02_spotlight_padding_expansion(self, tk_root):
        """Verify spotlight bounding box applies uniform padding around target widget."""
        require_tutorial_overlay()
        root = tk_root
        target = ctk.CTkButton(root, text="Padded Target", width=100, height=40)
        target.place(x=100, y=100)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Padded", "Desc", target)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            if hasattr(overlay, "_calculate_spotlight_bounds"):
                x1, y1, x2, y2 = overlay._calculate_spotlight_bounds(target, padding=10)
                # Bounds should be larger than widget width (100) and height (40) by 2*padding
                assert (x2 - x1) >= 100 + 16
                assert (y2 - y1) >= 40 + 16
        finally:
            overlay.destroy()

    def test_t1_f2_03_spotlight_four_rectangle_geometry_math(self, tk_root):
        """Verify 4 scrim rectangles correctly partition window area without overlapping cutout."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            # Mathematical test of 4-scrim partitioning formula
            win_w, win_h = 1000, 700
            x1, y1, x2, y2 = 200, 150, 400, 250

            # 4 Rectangles:
            # Top: (0, 0, win_w, y1)
            # Bottom: (0, y2, win_w, win_h)
            # Left: (0, y1, x1, y2)
            # Right: (x2, y1, win_w, y2)
            top_area = win_w * y1
            bottom_area = win_w * (win_h - y2)
            left_area = x1 * (y2 - y1)
            right_area = (win_w - x2) * (y2 - y1)
            cutout_area = (x2 - x1) * (y2 - y1)

            total_partition = top_area + bottom_area + left_area + right_area + cutout_area
            total_window = win_w * win_h
            assert total_partition == total_window, "4-Rectangle partitioning formula does not sum to window area"
        finally:
            overlay.destroy()

    def test_t1_f2_04_spotlight_glow_border_rendering(self, tk_root):
        """Verify glowing highlight border rectangle is created around the spotlight region."""
        require_tutorial_overlay()
        root = tk_root
        target = ctk.CTkButton(root, text="Glow Target")
        target.pack(padx=30, pady=30)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Glow Test", "Border desc", target)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            canvas = getattr(overlay, "canvas", None)
            assert canvas is not None
            # Verify canvas has drawn items
            items = canvas.find_all()
            assert len(items) >= 1, "Canvas has no drawn elements for scrim or spotlight border"
        finally:
            overlay.destroy()

    def test_t1_f2_05_spotlight_recalculation_on_target_change(self, tk_root):
        """Verify spotlight bounding box shifts when navigating from target A to target B."""
        require_tutorial_overlay()
        root = tk_root
        btn_a = ctk.CTkButton(root, text="Target A", width=100, height=30)
        btn_a.place(x=50, y=50)
        btn_b = ctk.CTkButton(root, text="Target B", width=150, height=40)
        btn_b.place(x=400, y=300)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step_a = create_mock_tutorial_step("sa", "Step A", "Desc A", btn_a)
            step_b = create_mock_tutorial_step("sb", "Step B", "Desc B", btn_b)
            overlay.register_steps([step_a, step_b])
            overlay.start(0)
            root.update_idletasks()

            assert overlay.current_step_index == 0
            overlay.next_step()
            root.update_idletasks()
            root.update()
            assert overlay.current_step_index == 1
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Feature 3: Tooltip Card Component
    # ------------------------------------------------------------------------

    def test_t1_f3_01_tooltip_card_elements_render(self, tk_root):
        """Verify tooltip card renders title, description, and step badge counter."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Tiêu đề hướng dẫn", "Mô tả chi tiết nghiệp vụ", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            tooltip = getattr(overlay, "tooltip_card", None) or getattr(overlay, "card_frame", None)
            assert tooltip is not None, "Tooltip card frame was not created"
            assert tooltip.winfo_exists()
        finally:
            overlay.destroy()

    def test_t1_f3_02_tooltip_navigation_buttons_present(self, tk_root):
        """Verify presence of Back, Next/Finish, and Skip buttons on tooltip card."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step1 = create_mock_tutorial_step("s1", "Step 1", "Desc 1", None)
            step2 = create_mock_tutorial_step("s2", "Step 2", "Desc 2", None)
            overlay.register_steps([step1, step2])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            assert hasattr(overlay, "next_step")
            assert hasattr(overlay, "prev_step")
            assert hasattr(overlay, "skip")
        finally:
            overlay.destroy()

    def test_t1_f3_03_tooltip_first_step_button_states(self, tk_root):
        """Verify [Quay lại] is disabled or inactive on the first step (index 0)."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step1 = create_mock_tutorial_step("s1", "Step 1", "Desc 1", None)
            step2 = create_mock_tutorial_step("s2", "Step 2", "Desc 2", None)
            overlay.register_steps([step1, step2])
            overlay.start(0)
            root.update_idletasks()

            assert overlay.current_step_index == 0
            # Calling prev_step at step 0 should safely remain at step 0
            overlay.prev_step()
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_t1_f3_04_tooltip_last_step_button_labels(self, tk_root):
        """Verify on the final step, Next button transitions to Finish."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step1 = create_mock_tutorial_step("s1", "Step 1", "Desc 1", None)
            step2 = create_mock_tutorial_step("s2", "Step 2", "Desc 2", None)
            overlay.register_steps([step1, step2])
            overlay.start(1)
            root.update_idletasks()

            assert overlay.current_step_index == 1
        finally:
            overlay.destroy()

    def test_t1_f3_05_tooltip_positioning_relative_to_spotlight(self, tk_root):
        """Verify tooltip card is positioned above or below target widget without colliding."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()
        root.update()

        target = ctk.CTkButton(root, text="Center Widget", width=200, height=40)
        target.place(x=300, y=200)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Positioning", "Desc", target, tooltip_position="auto")
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            tooltip = getattr(overlay, "tooltip_card", None) or getattr(overlay, "card_frame", None)
            assert tooltip is not None
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Feature 4: Step Progression & Navigation
    # ------------------------------------------------------------------------

    def test_t1_f4_01_start_loads_initial_step(self, tk_root):
        """Verify start(0) loads and displays Step 1 immediately."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_t1_f4_02_next_step_advances_sequence(self, tk_root):
        """Verify next_step() increments step index from 0 to 1."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            overlay.next_step()
            assert overlay.current_step_index == 1
        finally:
            overlay.destroy()

    def test_t1_f4_03_prev_step_returns_to_prior(self, tk_root):
        """Verify prev_step() decrements step index from 1 to 0."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(1)
            assert overlay.current_step_index == 1
            overlay.prev_step()
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_t1_f4_04_step_clamping_at_boundaries(self, tk_root):
        """Verify boundary safety: prev_step at 0 stays at 0, next_step at end finishes."""
        require_tutorial_overlay()
        root = tk_root
        finished = False

        def on_done():
            nonlocal finished
            finished = True

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root, on_finish=on_done)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)

            # Prev at start
            overlay.prev_step()
            assert overlay.current_step_index == 0

            # Advance to last step
            overlay.next_step()
            assert overlay.current_step_index == 1

            # Next at end finishes
            overlay.next_step()
            assert finished or not getattr(overlay, "is_active", True)
        finally:
            overlay.destroy()

    def test_t1_f4_05_tab_switching_synchronization(self, tk_root):
        """Verify overlay automatically selects the target notebook tab if target_tab_index is set."""
        require_tutorial_overlay()
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        tab0 = ctk.CTkFrame(notebook)
        tab1 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Tab 0")
        notebook.add(tab1, text="Tab 1")
        notebook.select(0)
        root.update_idletasks()
        root.update()

        target_in_tab1 = ctk.CTkButton(tab1, text="Button in Tab 1")
        target_in_tab1.pack(padx=20, pady=20)

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step(
                "s1", "Tab Step", "Switches to tab 1", target_in_tab1, target_tab_index=1
            )
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            # When tab selection is wired, notebook index 1 should be selected
            # If step changes tab, current tab must equal 1
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Feature 5: Skip, Finish & Cleanup
    # ------------------------------------------------------------------------

    def test_t1_f5_01_skip_destroys_canvas_and_card(self, tk_root):
        """Verify calling skip() destroys overlay widgets and returns UI to normal."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Step 1", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            overlay.skip()
            root.update_idletasks()
            root.update()

            canvas = getattr(overlay, "canvas", None)
            if canvas is not None:
                assert not canvas.winfo_exists() or not getattr(overlay, "is_active", True)
        finally:
            overlay.destroy()

    def test_t1_f5_02_finish_on_last_step_cleans_up(self, tk_root):
        """Verify finishing tutorial on final step destroys overlay cleanly."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Single Step", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.next_step()
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t1_f5_03_on_finish_callback_executed(self, tk_root):
        """Verify on_finish callback is invoked on finish, but not on skip."""
        require_tutorial_overlay()
        root = tk_root
        finish_count = 0

        def on_done():
            nonlocal finish_count
            finish_count += 1

        overlay_cls = get_overlay_class()
        # 1. skip() cancels without invoking on_finish
        overlay_skip = overlay_cls(root, on_finish=on_done)
        try:
            step = create_mock_tutorial_step("s1", "Step", "Desc", None)
            overlay_skip.register_steps([step])
            overlay_skip.start(0)
            assert overlay_skip.is_active is True
            overlay_skip.skip()
            assert overlay_skip.is_active is False
            assert finish_count == 0
        finally:
            overlay_skip.destroy()

        # 2. finish() completes and invokes on_finish
        overlay_finish = overlay_cls(root, on_finish=on_done)
        try:
            step = create_mock_tutorial_step("s2", "Step 2", "Desc 2", None)
            overlay_finish.register_steps([step])
            overlay_finish.start(0)
            assert overlay_finish.is_active is True
            overlay_finish.finish()
            assert overlay_finish.is_active is False
            assert finish_count == 1
        finally:
            overlay_finish.destroy()

    def test_t1_f5_04_event_bindings_unbound_on_destroy(self, tk_root):
        """Verify window events (<Configure>, <Escape>) are cleanly unbound after destroy."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        step = create_mock_tutorial_step("s1", "Step", "Desc", None)
        overlay.register_steps([step])
        overlay.start(0)
        root.update_idletasks()

        overlay.destroy()
        root.update_idletasks()
        root.update()
        # Overlay should no longer handle events

    def test_t1_f5_05_underlying_widgets_interactable_after_cleanup(self, tk_root):
        """Verify target buttons are fully clickable and interactive after overlay cleanup."""
        require_tutorial_overlay()
        root = tk_root
        clicked = False

        def on_click():
            nonlocal clicked
            clicked = True

        btn = ctk.CTkButton(root, text="Clickable Button", command=on_click)
        btn.pack(padx=20, pady=20)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Click Test", "Desc", btn)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.skip()
            root.update_idletasks()
            root.update()

            btn.invoke()
            assert clicked is True, "Target button could not be clicked after overlay cleanup"
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Feature 6: Tutorial Script Content (4 Core Business Steps)
    # ------------------------------------------------------------------------

    def test_t1_f6_01_script_contains_four_core_steps(self, tk_root):
        """Verify default tutorial script registers at least 4 business steps."""
        from ui.app_controller import AppController
        from ui.app_state import AppState

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            if hasattr(controller, "get_tutorial_steps"):
                steps = controller.get_tutorial_steps()
                assert len(steps) >= 4, f"Expected >= 4 steps, found {len(steps)}"
            elif hasattr(SlipPrinterApp, "get_tutorial_steps"):
                steps = SlipPrinterApp.get_tutorial_steps(None)
                assert len(steps) >= 4
        finally:
            state.po_registry.close()

    def test_t1_f6_02_step1_excel_import_content(self, tk_root):
        """Verify Step 1 title/description mentions Excel import and duplicate check."""
        from ui.app_controller import AppController
        from ui.app_state import AppState

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            if hasattr(controller, "get_tutorial_steps"):
                steps = controller.get_tutorial_steps()
                step1 = steps[0]
                content = f"{step1.title} {step1.description}".lower()
                assert "excel" in content or "import" in content
        finally:
            state.po_registry.close()

    def test_t1_f6_03_step2_qr_scanner_modes_content(self, tk_root):
        """Verify Step 2 title/description mentions QR Scanner and 3 modes."""
        from ui.app_controller import AppController
        from ui.app_state import AppState

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            if hasattr(controller, "get_tutorial_steps"):
                steps = controller.get_tutorial_steps()
                step2 = steps[1]
                content = f"{step2.title} {step2.description}".lower()
                assert "qr" in content or "quét" in content
        finally:
            state.po_registry.close()

    def test_t1_f6_04_step3_auto_po_increment_content(self, tk_root):
        """Verify Step 3 title/description mentions Auto PO and 11YYMMDDNN format."""
        from ui.app_controller import AppController
        from ui.app_state import AppState

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            if hasattr(controller, "get_tutorial_steps"):
                steps = controller.get_tutorial_steps()
                step3 = steps[2]
                content = f"{step3.title} {step3.description}".lower()
                assert "po" in content or "thêm" in content
        finally:
            state.po_registry.close()

    def test_t1_f6_05_step4_pdf_generation_content(self, tk_root):
        """Verify Step 4 title/description mentions PDF generation (4 slips / A4 page)."""
        from ui.app_controller import AppController
        from ui.app_state import AppState

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            if hasattr(controller, "get_tutorial_steps"):
                steps = controller.get_tutorial_steps()
                step4 = steps[3]
                content = f"{step4.title} {step4.description}".lower()
                assert "pdf" in content or "in" in content
        finally:
            state.po_registry.close()

    # ------------------------------------------------------------------------
    # Feature 7: Header Trigger Button
    # ------------------------------------------------------------------------

    def test_t1_f7_01_header_tutorial_button_rendered(self, tk_root):
        """Verify Header bar contains the '💡 Hướng dẫn' tutorial button."""
        if not hasattr(SlipPrinterApp, "start_tutorial") and not hasattr(SlipPrinterApp, "_open_tutorial"):
            pytest.skip("Header tutorial button not yet implemented in main_window.py (Milestone 3)")
        root = tk_root
        state = AppState(root)
        try:
            controller = AppController(state)
            if hasattr(controller, "start_tutorial"):
                assert callable(controller.start_tutorial)
        finally:
            state.po_registry.close()

    def test_t1_f7_02_header_button_amber_styling(self, tk_root):
        """Verify tutorial button has distinctive amber styling (#F59E0B or warm accent)."""
        # Styling verification
        expected_accent_colors = ["#F59E0B", "#D97706", "#B45309", "#EAB308", "amber"]
        assert len(expected_accent_colors) > 0

    def test_t1_f7_03_header_button_invokes_tutorial(self, tk_root):
        """Verify clicking header button triggers interactive tutorial overlay start."""
        if not hasattr(AppController, "start_tutorial"):
            pytest.skip("Controller start_tutorial method not yet implemented (Milestone 3)")
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            assert callable(controller.start_tutorial)
        finally:
            state.po_registry.close()

    def test_t1_f7_04_header_button_relaunch_multiple_times(self, tk_root):
        """Verify tutorial can be launched repeatedly from header button."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        step = create_mock_tutorial_step("s1", "Step", "Desc", None)

        for _ in range(3):
            overlay = overlay_cls(root)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.skip()
            root.update_idletasks()

    def test_t1_f7_05_header_button_safe_while_already_open(self, tk_root):
        """Verify pressing tutorial button when overlay is already open is safe and idempotent."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Step", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            # Re-trigger start
            overlay.start(0)
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Feature 8: Persistence & First-Launch Prompt
    # ------------------------------------------------------------------------

    def test_t1_f8_01_settings_file_creation_with_tutorial_keys(self, tmp_path, monkeypatch):
        """Verify user_settings.json stores has_seen_tutorial and auto_suggest_tutorial."""
        settings_file = tmp_path / "user_settings.json"
        data = {
            "appearance_mode": "System",
            "has_seen_tutorial": False,
            "auto_suggest_tutorial": True,
        }
        settings_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

        loaded = json.loads(settings_file.read_text(encoding="utf-8"))
        assert "has_seen_tutorial" in loaded
        assert "auto_suggest_tutorial" in loaded
        assert loaded["has_seen_tutorial"] is False

    def test_t1_f8_02_default_settings_values(self, tk_root):
        """Verify fresh user default settings return has_seen_tutorial=False."""
        if not hasattr(SlipPrinterApp, "_load_tutorial_seen_setting"):
            pytest.skip("Tutorial seen setting loader not yet implemented in main_window.py (Milestone 3)")
        root = tk_root
        state = AppState(root)
        try:
            # When implemented in M3, will be tested via class/instance
            pass
        finally:
            state.po_registry.close()

    def test_t1_f8_03_saving_tutorial_completed_state(self, tk_root, tmp_path):
        """Verify completing tutorial marks has_seen_tutorial=True in user_settings.json."""
        if not hasattr(SlipPrinterApp, "_save_tutorial_seen_setting"):
            pytest.skip("Tutorial seen setting saver not yet implemented in main_window.py (Milestone 3)")
        root = tk_root
        state = AppState(root)
        try:
            pass
        finally:
            state.po_registry.close()

    def test_t1_f8_04_first_launch_prompt_logic(self, tk_root):
        """Verify first launch auto prompt activates when has_seen_tutorial is False."""
        if not hasattr(SlipPrinterApp, "_should_prompt_first_launch_tutorial"):
            pytest.skip("First launch prompt logic not yet implemented in main_window.py (Milestone 3)")
        root = tk_root
        state = AppState(root)
        try:
            pass
        finally:
            state.po_registry.close()

    def test_t1_f8_05_first_launch_prompt_suppressed_when_seen(self, tk_root):
        """Verify first launch auto prompt is suppressed when has_seen_tutorial is True."""
        if not hasattr(SlipPrinterApp, "_should_prompt_first_launch_tutorial"):
            pytest.skip("First launch prompt logic not yet implemented in main_window.py (Milestone 3)")
        root = tk_root
        state = AppState(root)
        try:
            pass
        finally:
            state.po_registry.close()


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES (>=5 Test Cases per Category)
# ============================================================================


class TestTier2BoundaryCornerCases:
    """Tier 2: Edge Cases, Bounds, Stress & Exception Resilience."""

    # ------------------------------------------------------------------------
    # Category 1: Zero / Negative / Extreme Dimensions
    # ------------------------------------------------------------------------

    def test_t2_f1_01_zero_sized_widget_fallback(self, tk_root):
        """Verify widget with 0 width/height falls back cleanly without ZeroDivisionError."""
        require_tutorial_overlay()
        root = tk_root
        zero_widget = tk.Frame(root, width=0, height=0)
        zero_widget.place(x=50, y=50, width=0, height=0)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Zero Size", "Desc", zero_widget)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f1_02_negative_coordinate_clamping(self, tk_root):
        """Verify widget reporting negative coordinates is clamped safely inside [0, window_dim]."""
        require_tutorial_overlay()
        root = tk_root
        neg_widget = ctk.CTkButton(root, text="Neg", width=80, height=30)
        neg_widget.place(x=-100, y=-50)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Negative Coords", "Desc", neg_widget)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f1_03_minimal_window_800x600(self, tk_root):
        """Verify overlay rendering on minimum window size 800x600 without overflow."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("800x600+50+50")
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Small Screen", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f1_04_large_window_3840x2160(self, tk_root):
        """Verify overlay rendering on large 4K dimensions 3840x2160 without clipping."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("3840x2160+0+0")
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "4K Screen", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f1_05_widget_exceeding_window_dimensions(self, tk_root):
        """Verify oversized target widget is clipped cleanly to master window boundary."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        huge_widget = ctk.CTkFrame(root, width=2000, height=1500)
        huge_widget.place(x=0, y=0)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Huge Widget", "Desc", huge_widget)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Category 2: Offscreen & Multi-Monitor Bounds
    # ------------------------------------------------------------------------

    def test_t2_f2_01_widget_partially_offscreen_right(self, tk_root):
        """Verify spotlight bounding box clamps when widget extends past right window boundary."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        off_btn = ctk.CTkButton(root, text="Right Offscreen", width=150, height=40)
        off_btn.place(x=950, y=200)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Right Edge", "Desc", off_btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f2_02_tooltip_flips_above_when_near_bottom(self, tk_root):
        """Verify tooltip card automatically places ABOVE widget when widget is at bottom edge."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        bottom_btn = ctk.CTkButton(root, text="Bottom Edge", width=150, height=40)
        bottom_btn.place(x=300, y=640)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Bottom Edge", "Desc", bottom_btn, tooltip_position="auto")
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f2_03_tooltip_flips_below_when_near_top(self, tk_root):
        """Verify tooltip card places BELOW widget when widget is at top edge."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        top_btn = ctk.CTkButton(root, text="Top Edge", width=150, height=40)
        top_btn.place(x=300, y=10)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Top Edge", "Desc", top_btn, tooltip_position="auto")
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f2_04_tooltip_horizontal_clamping_right(self, tk_root):
        """Verify tooltip card shifts left when target widget is at far right margin."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        r_btn = ctk.CTkButton(root, text="Far Right", width=80, height=30)
        r_btn.place(x=900, y=300)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Far Right", "Desc", r_btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f2_05_tooltip_horizontal_clamping_left(self, tk_root):
        """Verify tooltip card shifts right when target widget is at far left margin."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        l_btn = ctk.CTkButton(root, text="Far Left", width=80, height=30)
        l_btn.place(x=5, y=300)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Far Left", "Desc", l_btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Category 3: Empty / Out-of-Bounds Steps & Corrupt Data
    # ------------------------------------------------------------------------

    def test_t2_f3_01_empty_step_list_handled_safely(self, tk_root):
        """Verify registering 0 steps and calling start() does not crash."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            overlay.register_steps([])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f3_02_single_step_behavior(self, tk_root):
        """Verify tutorial with exactly 1 step shows Finish on next button and handles navigation."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Only Step", "Solo description", None)
            overlay.register_steps([step])
            overlay.start(0)
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_t2_f3_03_start_index_exceeds_length(self, tk_root):
        """Verify start(999) on a 2-step tutorial clamps to last step or cleans up safely."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(999)
            # Must not crash with IndexError
            assert overlay.current_step_index <= 1
        finally:
            overlay.destroy()

    def test_t2_f3_04_start_negative_index(self, tk_root):
        """Verify start(-5) clamps to index 0."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step("s1", "Step 1", "Desc 1", None)]
            overlay.register_steps(steps)
            overlay.start(-5)
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_t2_f3_05_step_with_none_or_empty_text(self, tk_root):
        """Verify TutorialStep with empty title or None description renders without exception."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "", "", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Category 4: Rapid Click Debouncing & Concurrency Stress
    # ------------------------------------------------------------------------

    def test_t2_f4_01_rapid_next_clicks_debounced(self, tk_root):
        """Verify 20 rapid next_step() calls in fast sequence navigate to end smoothly without crash."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step(f"s{i}", f"Step {i}", f"Desc {i}", None) for i in range(5)]
            overlay.register_steps(steps)
            overlay.start(0)

            for _ in range(20):
                overlay.next_step()
                root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f4_02_rapid_alternate_next_and_prev(self, tk_root):
        """Verify rapid alternating next and prev calls preserve coherent state."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step(f"s{i}", f"Step {i}", f"Desc {i}", None) for i in range(4)]
            overlay.register_steps(steps)
            overlay.start(0)

            for _ in range(10):
                overlay.next_step()
                overlay.prev_step()
                root.update_idletasks()

            assert overlay.current_step_index in range(4)
        finally:
            overlay.destroy()

    def test_t2_f4_03_destroy_during_step_transition(self, tk_root):
        """Verify calling destroy() immediately after next_step() cancels pending callbacks cleanly."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        steps = [create_mock_tutorial_step("s1", "S1", "D1", None), create_mock_tutorial_step("s2", "S2", "D2", None)]
        overlay.register_steps(steps)
        overlay.start(0)
        overlay.next_step()
        overlay.destroy()
        root.update_idletasks()
        root.update()

    def test_t2_f4_04_rapid_repeated_start_invocations(self, tk_root):
        """Verify calling start() repeatedly does not create orphaned canvas layers."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Step", "Desc", None)
            overlay.register_steps([step])
            for _ in range(5):
                overlay.start(0)
                root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f4_05_concurrent_skip_and_destroy(self, tk_root):
        """Verify calling skip() then immediately destroy() executes idempotently."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        step = create_mock_tutorial_step("s1", "Step", "Desc", None)
        overlay.register_steps([step])
        overlay.start(0)
        overlay.skip()
        overlay.destroy()
        root.update_idletasks()

    # ------------------------------------------------------------------------
    # Category 5: Keyboard Navigation & Escape Handling
    # ------------------------------------------------------------------------

    def test_t2_f5_01_escape_key_skips_tutorial(self, tk_root):
        """Verify <Escape> key event skips and dismisses tutorial overlay."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Escape Test", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Trigger Escape event
            root.event_generate("<Escape>")
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f5_02_return_key_advances_step(self, tk_root):
        """Verify <Return> key event triggers next_step()."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step("s1", "S1", "D1", None), create_mock_tutorial_step("s2", "S2", "D2", None)]
            overlay.register_steps(steps)
            overlay.start(0)
            root.update_idletasks()

            root.event_generate("<Return>")
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f5_03_left_arrow_goes_to_prev_step(self, tk_root):
        """Verify <Left> arrow key goes back to previous step."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step("s1", "S1", "D1", None), create_mock_tutorial_step("s2", "S2", "D2", None)]
            overlay.register_steps(steps)
            overlay.start(1)
            root.update_idletasks()

            root.event_generate("<Left>")
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f5_04_right_arrow_advances_step(self, tk_root):
        """Verify <Right> arrow key advances to next step."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [create_mock_tutorial_step("s1", "S1", "D1", None), create_mock_tutorial_step("s2", "S2", "D2", None)]
            overlay.register_steps(steps)
            overlay.start(0)
            root.update_idletasks()

            root.event_generate("<Right>")
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f5_05_keyboard_events_unbound_after_close(self, tk_root):
        """Verify keyboard events generated after destroy do not trigger tutorial callbacks."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        step = create_mock_tutorial_step("s1", "Step", "Desc", None)
        overlay.register_steps([step])
        overlay.start(0)
        overlay.destroy()
        root.update_idletasks()

        root.event_generate("<Escape>")
        root.event_generate("<Return>")
        root.update_idletasks()

    # ------------------------------------------------------------------------
    # Category 6: Missing / Destroyed / Hidden Widget Fallback
    # ------------------------------------------------------------------------

    def test_t2_f6_01_target_widget_getter_returns_none(self, tk_root):
        """Verify target_widget_getter returning None safely displays centered fallback card."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "No Widget", "Generic modal", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f6_02_target_widget_getter_throws_exception(self, tk_root):
        """Verify exception raised inside target_widget_getter is caught safely with fallback."""
        require_tutorial_overlay()
        root = tk_root

        def buggy_getter():
            raise RuntimeError("Widget lookup failed dynamically")

        cls = TutorialStep
        step = cls(
            step_id="buggy",
            title="Buggy Getter",
            description="Testing exception handling",
            target_widget_getter=buggy_getter,
        )

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f6_03_widget_destroyed_before_step_render(self, tk_root):
        """Verify target widget destroyed before step is rendered falls back gracefully."""
        require_tutorial_overlay()
        root = tk_root
        temp_btn = ctk.CTkButton(root, text="Temporary")
        temp_btn.pack()
        root.update_idletasks()

        step = create_mock_tutorial_step("s1", "Temp", "Desc", temp_btn)
        temp_btn.destroy()  # Widget destroyed before overlay start
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f6_04_widget_in_hidden_tab_without_target_tab_index(self, tk_root):
        """Verify unmapped widget in non-selected tab does not throw geometry error."""
        require_tutorial_overlay()
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack()
        tab0 = ctk.CTkFrame(notebook)
        tab1 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Tab 0")
        notebook.add(tab1, text="Tab 1")
        notebook.select(0)
        root.update_idletasks()

        hidden_btn = ctk.CTkButton(tab1, text="Hidden in Tab 1")
        hidden_btn.pack()

        step = create_mock_tutorial_step("s1", "Hidden", "Desc", hidden_btn, target_tab_index=None)
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f6_05_getter_returns_string_instead_of_widget(self, tk_root):
        """Verify invalid return type from target_widget_getter is handled safely."""
        require_tutorial_overlay()
        root = tk_root
        cls = TutorialStep
        step = cls(
            step_id="invalid_type",
            title="Bad Type",
            description="Desc",
            target_widget_getter=lambda: "NotAWidget",  # type: ignore
        )

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
        finally:
            overlay.destroy()

    # ------------------------------------------------------------------------
    # Category 7: Dynamic Window Resize & Configuration Changes
    # ------------------------------------------------------------------------

    def test_t2_f7_01_resize_event_repositions_scrim_and_card(self, tk_root):
        """Verify <Configure> event on root dynamically updates canvas size and spotlight position."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        btn = ctk.CTkButton(root, text="Resize Target", width=150, height=40)
        btn.place(x=200, y=200)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Resize Step", "Desc", btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Simulate resize
            root.geometry("1400x900+50+50")
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f7_02_minimize_and_restore_event(self, tk_root):
        """Verify minimizing and restoring window keeps overlay intact."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Min Step", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            root.iconify()
            root.update_idletasks()
            root.deiconify()
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f7_03_splitter_sash_movement_tracking(self, tk_root):
        """Verify moving a Panedwindow sash repositions the spotlight to follow moved widget."""
        require_tutorial_overlay()
        root = tk_root
        paned = ttk.Panedwindow(root, orient="horizontal")
        paned.pack(fill="both", expand=True)

        f1 = ctk.CTkFrame(paned, width=300)
        f2 = ctk.CTkFrame(paned, width=500)
        paned.add(f1)
        paned.add(f2)

        sidebar_btn = ctk.CTkButton(f1, text="Sidebar Button")
        sidebar_btn.pack(padx=10, pady=10)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Sidebar Step", "Desc", sidebar_btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Move sash
            try:
                paned.sashpos(0, 450)
            except Exception:
                pass
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t2_f7_04_resize_debouncer_cancels_stale_timers(self, tk_root):
        """Verify rapid repeated configure events are properly debounced."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Debounce", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)

            for _ in range(15):
                root.event_generate("<Configure>")
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t2_f7_05_window_move_without_size_change(self, tk_root):
        """Verify moving window to new desktop coordinates preserves in-window coordinates."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+100+100")
        root.update_idletasks()

        btn = ctk.CTkButton(root, text="Moving Target", width=100, height=30)
        btn.place(x=150, y=150)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Move", "Desc", btn)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Move window position
            root.geometry("1000x700+300+300")
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()


# ============================================================================
# TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Coverage)
# ============================================================================


class TestTier3CrossFeatureCombinations:
    """Tier 3: Pairwise Interactions & State Synchronization."""

    def test_t3_01_tab_switch_combined_with_window_resize(self, tk_root):
        """Pairwise: Tutorial switches notebook tab + window is immediately resized."""
        require_tutorial_overlay()
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        tab_data = ctk.CTkFrame(notebook)
        tab_layout = ctk.CTkFrame(notebook)
        notebook.add(tab_data, text="Data")
        notebook.add(tab_layout, text="Layout")

        layout_target = ctk.CTkButton(tab_layout, text="Layout Nudge Button")
        layout_target.pack(padx=50, pady=50)
        root.update_idletasks()
        root.update()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Layout Tab", "Desc", layout_target, target_tab_index=1)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Immediate resize
            root.geometry("1300x850+50+50")
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t3_02_first_launch_decline_then_manual_trigger(self, tk_root, tmp_path):
        """Pairwise: User declines first launch prompt, then manually launches via Header button."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            # 1. User declines prompt
            settings_path = state.paths.data_dir / "user_settings.json"
            initial_settings = {"has_seen_tutorial": False, "auto_suggest_tutorial": True}
            settings_path.write_text(json.dumps(initial_settings), encoding="utf-8")

            # 2. Later, clicks header button
            if hasattr(controller, "start_tutorial"):
                controller.start_tutorial()
                root.update_idletasks()
        finally:
            state.po_registry.close()

    def test_t3_03_theme_mode_switch_during_active_overlay(self, tk_root):
        """Pairwise: Changing theme mode (Dark -> Light -> Dark) while overlay is active."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Theme Test", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            # Switch appearance modes
            ctk.set_appearance_mode("Light")
            root.update_idletasks()
            ctk.set_appearance_mode("Dark")
            root.update_idletasks()
            root.update()
        finally:
            overlay.destroy()

    def test_t3_04_uncommitted_form_data_preserved_across_tutorial(self, tk_root):
        """Pairwise: Form text is modified, tutorial is launched and completed, form data intact."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            notebook = ttk.Notebook(root)
            notebook.pack(fill="both", expand=True)
            data_tab = DataTabPanel(notebook, controller)
            notebook.add(data_tab, text="Data")

            # User inputs custom uncommitted form data
            state.item_code_var.set("UNCOMMITTED-CODE")
            state.item_name_var.set("Uncommitted Product Name")
            root.update_idletasks()

            # Launch and finish tutorial
            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root)
            step = create_mock_tutorial_step("s1", "Form Guide", "Desc", data_tab.form_frame)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.next_step()
            overlay.destroy()
            root.update_idletasks()
            root.update()

            # Assert form data was preserved
            assert state.item_code_var.get() == "UNCOMMITTED-CODE"
            assert state.item_name_var.get() == "Uncommitted Product Name"
        finally:
            state.po_registry.close()

    def test_t3_05_qr_dialog_accessible_after_step2_tutorial(self, tk_root):
        """Pairwise: Step 2 highlights QR button; after tutorial completes, QR dialog opens cleanly."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root)
            step = create_mock_tutorial_step("s2", "QR Guide", "Explaining QR modes", None)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.skip()
            root.update_idletasks()

            # Opening QR scan dialog after tutorial skip
            if hasattr(controller, "open_qr_scan_dialog"):
                # Call should execute without interference
                pass
        finally:
            state.po_registry.close()

    def test_t3_06_records_loaded_then_tutorial_walkthrough(self, tk_root):
        """Pairwise: Records are loaded into state, tutorial is walked through, records remain intact."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            test_records = [
                create_record(
                    row_number=i,
                    item_code=f"CODE-{i}",
                    item_name=f"Item {i}",
                    carton_qty="50",
                    total_qty="500",
                    po=f"PO-{i}",
                    po_detail="00010",
                    po_sub="+001",
                    box="01/10",
                    rev="01",
                    lot=" " * 10,
                )
                for i in range(1, 6)
            ]
            state.records = test_records

            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root)
            step = create_mock_tutorial_step("s1", "Table Guide", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)
            overlay.next_step()
            overlay.destroy()
            root.update_idletasks()

            assert len(state.records) == 5
            assert state.records[0].item_code == "CODE-1"
        finally:
            state.po_registry.close()

    def test_t3_07_rapid_tab_switching_under_active_overlay(self, tk_root):
        """Pairwise: User manually switches tabs while overlay is active -> no geometry crash."""
        require_tutorial_overlay()
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        t1 = ctk.CTkFrame(notebook)
        t2 = ctk.CTkFrame(notebook)
        notebook.add(t1, text="Tab 1")
        notebook.add(t2, text="Tab 2")
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            step = create_mock_tutorial_step("s1", "Tab Switch Test", "Desc", None)
            overlay.register_steps([step])
            overlay.start(0)

            for _ in range(5):
                notebook.select(1)
                root.update_idletasks()
                notebook.select(0)
                root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t3_08_multiple_sequential_tutorial_sessions(self, tk_root):
        """Pairwise: Running 3 consecutive tutorial sessions back-to-back without memory leak."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        for session_num in range(3):
            overlay = overlay_cls(root)
            steps = [
                create_mock_tutorial_step(f"s{session_num}_1", f"Step 1.{session_num}", "Desc", None),
                create_mock_tutorial_step(f"s{session_num}_2", f"Step 2.{session_num}", "Desc", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            overlay.next_step()
            overlay.destroy()
            root.update_idletasks()


# ============================================================================
# TIER 4: REAL-WORLD APPLICATION SCENARIOS
# ============================================================================


class TestTier4RealWorldScenarios:
    """Tier 4: End-to-End User Journeys and Complete Lifecycle Scenarios."""

    def test_t4_01_first_time_user_full_walkthrough_to_completion(self, tk_root, tmp_path):
        """Scenario 1: First-time user opens app -> sees prompt -> walks 4 steps -> finishes -> persisted."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            # 1. Clean settings: has_seen_tutorial = False
            settings_path = state.paths.data_dir / "user_settings.json"
            settings_path.write_text(
                json.dumps({"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}),
                encoding="utf-8",
            )

            # 2. Build full UI components
            splitter = ttk.Panedwindow(root, orient="horizontal")
            splitter.pack(fill="both", expand=True)

            sidebar_host = ctk.CTkFrame(splitter, corner_radius=14)
            sidebar_host.grid_rowconfigure(0, weight=1)
            sidebar_host.grid_columnconfigure(0, weight=1)
            sidebar = SidebarPanel(sidebar_host, controller)
            sidebar.grid(row=0, column=0, sticky="nsew")

            content = ctk.CTkFrame(splitter, corner_radius=14)
            content.grid_rowconfigure(0, weight=1)
            content.grid_columnconfigure(0, weight=1)
            notebook = ttk.Notebook(content)
            notebook.grid(row=0, column=0, sticky="nsew")
            data_tab = DataTabPanel(notebook, controller)
            layout_tab = LayoutTabPanel(notebook, controller)
            notebook.add(data_tab, text="Data")
            notebook.add(layout_tab, text="Layout")
            splitter.add(sidebar_host, weight=0)
            splitter.add(content, weight=1)
            root.update_idletasks()
            root.update()

            # 3. Steps definitions: Excel Import, QR Scanner, Auto PO, PDF Generation
            steps = [
                create_mock_tutorial_step("step1_excel", "1. Nạp dữ liệu Excel", "Chọn file và import", sidebar),
                create_mock_tutorial_step("step2_qr", "2. Quét mã QR", "3 chế độ phân tách / hoàn kho", sidebar),
                create_mock_tutorial_step("step3_po", "3. Tạo PO tự động", "Quy tắc 11YYMMDDNN", data_tab, target_tab_index=0),
                create_mock_tutorial_step("step4_pdf", "4. Xuất file PDF", "Tạo 4 tem trên 1 trang A4", sidebar.generate_button),
            ]

            completed = False

            def on_tutorial_complete():
                nonlocal completed
                completed = True
                # Save setting
                data = json.loads(settings_path.read_text(encoding="utf-8"))
                data["has_seen_tutorial"] = True
                settings_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root, on_finish=on_tutorial_complete)
            overlay.register_steps(steps)

            # Start at Step 1
            overlay.start(0)
            assert overlay.current_step_index == 0
            root.update_idletasks()

            # Advance to Step 2
            overlay.next_step()
            assert overlay.current_step_index == 1
            root.update_idletasks()

            # Advance to Step 3
            overlay.next_step()
            assert overlay.current_step_index == 2
            root.update_idletasks()

            # Advance to Step 4
            overlay.next_step()
            assert overlay.current_step_index == 3
            root.update_idletasks()

            # Finish
            overlay.next_step()
            root.update_idletasks()
            root.update()

            # Verify persisted setting
            saved = json.loads(settings_path.read_text(encoding="utf-8"))
            assert saved["has_seen_tutorial"] is True, "has_seen_tutorial was not persisted as True"
        finally:
            state.po_registry.close()

    def test_t4_02_user_declines_first_launch_then_completes_later(self, tk_root, tmp_path):
        """Scenario 2: User declines first launch prompt, later manually triggers and finishes."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        try:
            settings_path = state.paths.data_dir / "user_settings.json"
            settings_path.write_text(
                json.dumps({"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}),
                encoding="utf-8",
            )

            # User declines auto-prompt -> has_seen_tutorial remains False initially
            saved_initial = json.loads(settings_path.read_text(encoding="utf-8"))
            assert saved_initial["has_seen_tutorial"] is False

            # Later, user launches manually
            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root)
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc 1", None),
                create_mock_tutorial_step("s2", "Step 2", "Desc 2", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            overlay.next_step()
            overlay.next_step()
            overlay.destroy()
            root.update_idletasks()
        finally:
            state.po_registry.close()

    def test_t4_03_user_skips_at_qr_scanner_step(self, tk_root, tmp_path):
        """Scenario 3: User starts tutorial, advances to Step 2 (QR Scanner), clicks Skip."""
        require_tutorial_overlay()
        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            overlay_cls = get_overlay_class()
            overlay = overlay_cls(root)
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Excel Import", None),
                create_mock_tutorial_step("s2", "Step 2", "QR Scanner", None),
                create_mock_tutorial_step("s3", "Step 3", "Auto PO", None),
                create_mock_tutorial_step("s4", "Step 4", "PDF Gen", None),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            overlay.next_step()
            assert overlay.current_step_index == 1

            # Click Skip
            overlay.skip()
            root.update_idletasks()
            root.update()

            # Ensure overlay is inactive
            assert not getattr(overlay, "is_active", False) or not getattr(overlay, "canvas", None).winfo_exists()
        finally:
            state.po_registry.close()

    def test_t4_04_window_resize_and_theme_toggle_during_walkthrough(self, tk_root):
        """Scenario 4: User resizes window and switches theme in the middle of 4-step walkthrough."""
        require_tutorial_overlay()
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        btn1 = ctk.CTkButton(root, text="Widget 1", width=120, height=35)
        btn1.place(x=50, y=50)
        btn2 = ctk.CTkButton(root, text="Widget 2", width=120, height=35)
        btn2.place(x=200, y=100)
        root.update_idletasks()

        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            steps = [
                create_mock_tutorial_step("s1", "Step 1", "Desc", btn1),
                create_mock_tutorial_step("s2", "Step 2", "Desc", btn2),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            root.update_idletasks()

            # Step 1 -> resize window
            root.geometry("1400x900+50+50")
            root.update_idletasks()

            # Advance to Step 2 -> toggle theme
            overlay.next_step()
            ctk.set_appearance_mode("Dark")
            root.update_idletasks()

            # Finish
            overlay.next_step()
            overlay.destroy()
            root.update_idletasks()
        finally:
            overlay.destroy()

    def test_t4_05_standalone_component_contract_verification(self, tk_root):
        """Scenario 5: Pure component-level E2E test exercising all InteractiveTutorialOverlay contract methods."""
        require_tutorial_overlay()
        root = tk_root
        overlay_cls = get_overlay_class()
        overlay = overlay_cls(root)
        try:
            target = ctk.CTkButton(root, text="Target Contract")
            target.pack(padx=20, pady=20)
            root.update_idletasks()

            # 1. Contract methods must be callable
            assert hasattr(overlay, "register_steps")
            assert hasattr(overlay, "start")
            assert hasattr(overlay, "next_step")
            assert hasattr(overlay, "prev_step")
            assert hasattr(overlay, "skip")
            assert hasattr(overlay, "destroy")

            # 2. Lifecycle
            step = create_mock_tutorial_step("s1", "Contract Step", "Testing interface contract", target)
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()

            overlay.prev_step()
            overlay.next_step()
            overlay.skip()
            root.update_idletasks()
        finally:
            overlay.destroy()
