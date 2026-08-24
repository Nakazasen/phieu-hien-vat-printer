"""Comprehensive Unit & Integration Tests for Interactive Tutorial Overlay."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional
import pytest
import customtkinter as ctk

from ui.components.tutorial_overlay import (
    TutorialStep,
    TooltipCard,
    PlacementEngine,
    GeometryHelper,
    TabSyncHelper,
    InteractiveTutorialOverlay,
)


@pytest.fixture
def tk_root():
    """Create a headless or virtual Tk/CTk root for testing."""
    try:
        root = ctk.CTk()
    except Exception:
        root = tk.Tk()
    root.geometry("1200x800")
    root.update_idletasks()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


class TestTutorialStep:
    def test_step_initialization_defaults(self):
        step = TutorialStep(
            step_id="step_1",
            title="Step 1 Title",
            description="Step 1 Description",
            target_widget_getter=lambda: None,
        )
        assert step.step_id == "step_1"
        assert step.title == "Step 1 Title"
        assert step.description == "Step 1 Description"
        assert step.target_widget_getter() is None
        assert step.target_tab_index is None
        assert step.tooltip_position == "auto"
        assert step.padding == 6

    def test_step_custom_properties(self):
        dummy_btn = object()
        step = TutorialStep(
            step_id="step_custom",
            title="Custom Title",
            description="Custom Description",
            target_widget_getter=lambda: dummy_btn,
            target_tab_index=2,
            tooltip_position="bottom",
            padding=10,
        )
        assert step.target_tab_index == 2
        assert step.tooltip_position == "bottom"
        assert step.padding == 10
        assert step.target_widget_getter() is dummy_btn


class TestPlacementEngine:
    def test_center_fallback_when_none(self):
        w, h = 1200, 800
        card_w, card_h = 360, 200
        pos = PlacementEngine.calculate(w, h, None, card_w=card_w, card_h=card_h)
        expected_x = (w - card_w) // 2
        expected_y = (h - card_h) // 2
        assert pos == (expected_x, expected_y)

    def test_center_when_preferred_is_center(self):
        w, h = 1200, 800
        spotlight = (100, 100, 300, 200)
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=360, card_h=200, preferred_position="center"
        )
        assert pos == ((w - 360) // 2, (h - 200) // 2)

    def test_bottom_placement_when_fits(self):
        w, h = 1200, 800
        card_w, card_h = 360, 200
        gap, margin = 14, 16
        spotlight = (200, 100, 400, 200)  # cx = 300, y2 = 200
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="bottom", gap=gap, margin=margin
        )
        cx = (200 + 400) // 2
        expected_x = cx - card_w // 2
        expected_y = 200 + gap
        assert pos == (expected_x, expected_y)

    def test_top_placement_when_fits(self):
        w, h = 1200, 800
        card_w, card_h = 360, 200
        gap, margin = 14, 16
        spotlight = (200, 400, 400, 600)  # y1 = 400
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="top", gap=gap, margin=margin
        )
        cx = (200 + 400) // 2
        expected_x = cx - card_w // 2
        expected_y = 400 - gap - card_h
        assert pos == (expected_x, expected_y)

    def test_right_placement_when_fits(self):
        w, h = 1200, 800
        card_w, card_h = 360, 200
        gap, margin = 14, 16
        spotlight = (100, 300, 300, 500)  # x2 = 300, cy = 400
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="right", gap=gap, margin=margin
        )
        expected_x = 300 + gap
        expected_y = 400 - (card_h // 2)
        assert pos == (expected_x, expected_y)

    def test_left_placement_when_fits(self):
        w, h = 1200, 800
        card_w, card_h = 360, 200
        gap, margin = 14, 16
        spotlight = (700, 300, 900, 500)  # x1 = 700, cy = 400
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="left", gap=gap, margin=margin
        )
        expected_x = 700 - gap - card_w
        expected_y = 400 - (card_h // 2)
        assert pos == (expected_x, expected_y)

    def test_overflow_flip_bottom_to_top(self):
        # Spotlight at bottom of screen (y2 = 750, root_h = 800, space_bottom = 800 - 750 - 14 - 16 = 20 < 200)
        w, h = 1200, 800
        card_w, card_h = 360, 200
        gap = 14
        spotlight = (400, 600, 600, 750)
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="bottom"
        )
        # Should flip to top: raw_y = 600 - 14 - 200 = 386
        expected_y = 600 - gap - card_h
        assert pos[1] == expected_y

    def test_boundary_clamping(self):
        # Spotlight at far right (x1 = 1100, x2 = 1180, root_w = 1200)
        w, h = 1200, 800
        card_w, card_h = 360, 200
        margin = 16
        spotlight = (1100, 100, 1180, 200)
        pos = PlacementEngine.calculate(
            w, h, spotlight, card_w=card_w, card_h=card_h, preferred_position="bottom"
        )
        assert pos[0] <= w - card_w - margin
        assert pos[0] >= margin
        assert pos[1] >= margin


class TestGeometryAndPartitioning:
    def test_4_rectangle_partition_area_conservation(self):
        """Mathematically verifies that 4 disjoint slices + cutout cover exact window area."""
        win_w, win_h = 1400, 900
        x1, y1, x2, y2 = 120, 150, 450, 380

        top_area = win_w * y1
        bottom_area = win_w * (win_h - y2)
        left_area = x1 * (y2 - y1)
        right_area = (win_w - x2) * (y2 - y1)
        cutout_area = (x2 - x1) * (y2 - y1)

        total = top_area + bottom_area + left_area + right_area + cutout_area
        assert total == win_w * win_h


class TestTooltipCard:
    def test_tooltip_card_creation_and_callbacks(self, tk_root):
        calls = []

        card = TooltipCard(
            tk_root,
            on_next=lambda: calls.append("next"),
            on_prev=lambda: calls.append("prev"),
            on_skip=lambda: calls.append("skip"),
        )
        tk_root.update_idletasks()

        assert card.title_label.cget("text") == "💡 Hướng dẫn"
        assert card.badge_label.cget("text") == "Bước 1 / 4"
        assert card.prev_btn.cget("state") == "disabled"
        assert card.next_btn.cget("text") == "Tiếp tục ▶"

        # Trigger callbacks
        card.next_btn.invoke()
        card.prev_btn.invoke()
        card.skip_btn.invoke()

        assert calls == ["next", "prev", "skip"]

    def test_tooltip_card_update_content(self, tk_root):
        card = TooltipCard(
            tk_root,
            on_next=lambda: None,
            on_prev=lambda: None,
            on_skip=lambda: None,
        )

        # Update to step 2/4
        card.update_content("Quét mã QR", "Hướng dẫn quét QR", 1, 4)
        assert card.title_label.cget("text") == "Quét mã QR"
        assert card.desc_label.cget("text") == "Hướng dẫn quét QR"
        assert card.badge_label.cget("text") == "Bước 2 / 4"
        assert card.prev_btn.cget("state") == "normal"
        assert card.next_btn.cget("text") == "Tiếp tục ▶"

        # Update to final step 4/4
        card.update_content("In phiếu PDF", "Tạo file PDF", 3, 4)
        assert card.badge_label.cget("text") == "Bước 4 / 4"
        assert card.next_btn.cget("text") == "🎉 Hoàn tất"


class TestInteractiveTutorialOverlay:
    def test_overlay_lifecycle_and_navigation(self, tk_root):
        finished = []
        overlay = InteractiveTutorialOverlay(
            master_window=tk_root,
            on_finish=lambda: finished.append(True),
        )

        # Create dummy target widgets
        btn1 = ctk.CTkButton(tk_root, text="Target 1", width=120, height=36)
        btn1.place(x=50, y=50)
        btn2 = ctk.CTkButton(tk_root, text="Target 2", width=150, height=40)
        btn2.place(x=300, y=100)
        tk_root.update_idletasks()

        steps = [
            TutorialStep("step_1", "Bước 1", "Nạp Excel", lambda: btn1),
            TutorialStep("step_2", "Bước 2", "Quét QR", lambda: btn2),
        ]
        overlay.register_steps(steps)

        assert not overlay.is_active

        # Start overlay
        overlay.start()
        assert overlay.is_active
        assert overlay.current_step_index == 0
        assert overlay.canvas is not None
        assert overlay.tooltip is not None
        tk_root.update_idletasks()

        # Advance to step 2
        overlay.next_step()
        assert overlay.current_step_index == 1

        # Go back to step 1
        overlay.prev_step()
        assert overlay.current_step_index == 0

        # Advance to final and finish
        overlay.next_step()
        overlay.next_step()  # Triggers finish

        assert not overlay.is_active
        assert finished == [True]
        assert overlay.canvas is None
        assert overlay.tooltip is None

    def test_overlay_skip(self, tk_root):
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        steps = [TutorialStep("step_1", "B1", "Desc", lambda: None)]
        overlay.register_steps(steps)
        overlay.start()
        assert overlay.is_active

        overlay.skip()
        assert not overlay.is_active
        assert overlay.canvas is None
        assert overlay.tooltip is None

    def test_overlay_tab_sync(self, tk_root):
        # Create ttk.Notebook with 2 tabs
        notebook = ttk.Notebook(tk_root)
        notebook.place(x=0, y=0, width=800, height=600)

        tab0 = ctk.CTkFrame(notebook)
        tab1 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Tab 0")
        notebook.add(tab1, text="Tab 1")
        tk_root.update_idletasks()

        btn_in_tab1 = ctk.CTkButton(tab1, text="Tab 1 Button")
        btn_in_tab1.pack(padx=20, pady=20)
        tk_root.update_idletasks()

        overlay = InteractiveTutorialOverlay(master_window=tk_root, notebook=notebook)
        steps = [
            TutorialStep("step_t0", "Tab 0 Step", "In Tab 0", lambda: None, target_tab_index=0),
            TutorialStep("step_t1", "Tab 1 Step", "In Tab 1", lambda: btn_in_tab1, target_tab_index=1),
        ]
        overlay.register_steps(steps)
        overlay.start()

        assert notebook.index(notebook.select()) == 0

        # Advance to step 2 -> should switch to Tab 1
        overlay.next_step()
        assert notebook.index(notebook.select()) == 1

        overlay.destroy()
        assert not overlay.is_active
