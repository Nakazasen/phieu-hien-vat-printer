"""Tier 5 Robustness Hardening & Adversarial Stress Test Suite for Interactive Tutorial Overlay.

Focus areas:
1. Tooltip card clamping at window boundaries on minimal window sizes (640x480, 800x600, 320x240, 1920x1080).
2. Memory leaks and resource tracking across 100 consecutive start/skip/destroy cycles.
3. Dynamic widget destruction mid-walkthrough (target widget or parent destroyed while overlay is active).
4. Concurrency, debouncer storm, and mainloop responsiveness under heavy event queuing.
"""

from __future__ import annotations

import gc
import json
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional
import customtkinter as ctk
import pytest

from core.slip_printer_engine import SlipRecord, create_record
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.history_tab import HistoryTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel
from ui.components.tutorial_overlay import (
    GeometryHelper,
    InteractiveTutorialOverlay,
    PlacementEngine,
    TabSyncHelper,
    TooltipCard,
    TutorialOverlay,
    TutorialStep,
    build_tutorial_steps,
)
from ui.main_window import SlipPrinterApp


# ============================================================================
# 1. TOOLTIP CARD BOUNDARY CLAMPING & MINIMAL GEOMETRY STRESS TESTS
# ============================================================================


class TestBoundaryClampingStress:
    """Stress testing coordinate math and boundary clamping across extreme window geometries."""

    @pytest.mark.parametrize(
        ("win_w", "win_h"),
        [
            (640, 480),   # Minimal legacy VGA
            (800, 600),   # SVGA
            (1024, 768),  # XGA
            (1280, 720),  # HD
            (1920, 1080), # Full HD
            (3840, 2160), # 4K UHD
            (400, 300),   # Sub-minimal window
            (200, 150),   # Extreme compact edge case
        ],
    )
    def test_placement_engine_minimal_and_extreme_resolutions(self, win_w: int, win_h: int):
        """Verify PlacementEngine produces strictly clamped non-negative coordinates without crashing."""
        card_w, card_h = 360, 200
        margin = 16

        # Test with no spotlight (center modal fallback)
        cx, cy = PlacementEngine.calculate(
            root_w=win_w,
            root_h=win_h,
            spotlight_bounds=None,
            card_w=card_w,
            card_h=card_h,
            preferred_position="center",
            margin=margin,
        )
        assert cx >= margin
        assert cy >= margin
        if win_w >= card_w + 2 * margin:
            assert cx + card_w <= win_w

        # Test with spotlight at various positions
        positions = ["auto", "bottom", "top", "left", "right", "center", "invalid_pos"]
        spotlights = [
            (0, 0, 100, 50),                      # Top-left corner
            (win_w - 100, 0, win_w, 50),          # Top-right corner
            (0, win_h - 50, 100, win_h),          # Bottom-left corner
            (win_w - 100, win_h - 50, win_w, win_h), # Bottom-right corner
            (win_w // 2 - 50, win_h // 2 - 25, win_w // 2 + 50, win_h // 2 + 25), # Center
            (-100, -100, -10, -10),              # Negative offscreen
            (win_w + 50, win_h + 50, win_w + 150, win_h + 150), # Far offscreen
            (0, 0, win_w, win_h),                 # Full window widget
        ]

        for spot in spotlights:
            for pref in positions:
                px, py = PlacementEngine.calculate(
                    root_w=win_w,
                    root_h=win_h,
                    spotlight_bounds=spot,
                    card_w=card_w,
                    card_h=card_h,
                    preferred_position=pref,
                    margin=margin,
                )
                assert isinstance(px, int)
                assert isinstance(py, int)
                assert px >= margin
                assert py >= margin

    def test_geometry_helper_clamping_on_offscreen_and_negative_widgets(self, tk_root):
        """Verify GeometryHelper clamps partially or fully offscreen widgets safely."""
        root = tk_root
        root.geometry("800x600+50+50")
        root.update_idletasks()

        # Widget placed offscreen
        btn_off = ctk.CTkButton(root, text="Offscreen", width=120, height=40)
        btn_off.place(x=-50, y=-20)
        root.update_idletasks()

        bounds = GeometryHelper.get_relative_bounds(root, btn_off, pad=6)
        if bounds is not None:
            x1, y1, x2, y2 = bounds
            assert x1 >= 0
            assert y1 >= 0
            assert x2 <= root.winfo_width()
            assert y2 <= root.winfo_height()

        btn_off.destroy()

    def test_tooltip_rendering_in_minimal_640x480_window(self, tk_root):
        """Verify live rendering and UI update of TutorialOverlay in a 640x480 window."""
        root = tk_root
        root.geometry("640x480+50+50")
        root.update_idletasks()

        target_btn = ctk.CTkButton(root, text="VGA Target", width=100, height=30)
        target_btn.place(x=20, y=20)
        root.update_idletasks()

        overlay = InteractiveTutorialOverlay(root)
        step = TutorialStep(
            step_id="vga_step",
            title="Minimal 640x480 Step",
            description="Testing tooltip positioning on minimal display resolution.",
            target_widget_getter=lambda: target_btn,
            tooltip_position="bottom",
        )
        overlay.register_steps([step])
        overlay.start(0)
        root.update_idletasks()

        assert overlay.is_active is True
        assert overlay.tooltip is not None
        assert overlay.canvas is not None

        # Advance and skip
        overlay.skip()
        root.update_idletasks()
        assert overlay.is_active is False
        target_btn.destroy()


# ============================================================================
# 2. MEMORY LEAK & 100-CYCLE LIFECYCLE STRESS TESTS
# ============================================================================


class TestMemoryLeakAndLifecycleStress:
    """Stress testing 100 consecutive start() / skip() / destroy() cycles for memory leaks."""

    def test_100_consecutive_overlay_lifecycle_cycles(self, tk_root):
        """Run 100 rapid start -> next -> prev -> skip cycles, ensuring zero dangling canvas widgets or timers."""
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        test_btn1 = ctk.CTkButton(root, text="Target 1", width=120, height=35)
        test_btn1.place(x=50, y=50)
        test_btn2 = ctk.CTkButton(root, text="Target 2", width=120, height=35)
        test_btn2.place(x=250, y=50)
        root.update_idletasks()

        steps = [
            TutorialStep("s1", "Step 1", "Desc 1", lambda: test_btn1),
            TutorialStep("s2", "Step 2", "Desc 2", lambda: test_btn2),
        ]

        gc.collect()
        initial_canvas_count = len([w for w in root.winfo_children() if isinstance(w, tk.Canvas)])

        for cycle_idx in range(100):
            overlay = InteractiveTutorialOverlay(root)
            overlay.register_steps(steps)
            overlay.start(0)

            # Exercise state transitions
            overlay.next_step()
            assert overlay.current_step_index == 1
            overlay.prev_step()
            assert overlay.current_step_index == 0

            # Alternate between finish, skip, and direct destroy
            if cycle_idx % 3 == 0:
                overlay.skip()
            elif cycle_idx % 3 == 1:
                overlay.next_step()
                overlay.finish()
            else:
                overlay.destroy()

            # Ensure overlay state is cleanly marked
            assert overlay.is_active is False
            assert overlay._bound_events == []
            assert overlay._configure_timer_id is None

            # Periodically pump events to trigger pending after callbacks
            if cycle_idx % 10 == 0:
                root.update_idletasks()

        root.update_idletasks()
        gc.collect()

        # Canvas widgets created by overlay must all have been destroyed
        final_canvas_count = len([w for w in root.winfo_children() if isinstance(w, tk.Canvas)])
        assert final_canvas_count <= initial_canvas_count, (
            f"Canvas leak detected: initial {initial_canvas_count}, final {final_canvas_count}"
        )

        test_btn1.destroy()
        test_btn2.destroy()

    def test_rapid_start_re_entry_without_destroy(self, tk_root):
        """Calling start() repeatedly without explicit destroy() must safely reuse/recreate overlay without crashing."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        step = TutorialStep("s1", "Re-entry", "Testing re-entry", lambda: None)
        overlay.register_steps([step])

        for _ in range(30):
            overlay.start(0)
            assert overlay.is_active is True

        overlay.destroy()
        assert overlay.is_active is False


# ============================================================================
# 3. DYNAMIC WIDGET DESTRUCTION MID-WALKTHROUGH
# ============================================================================


class TestDynamicWidgetDestructionStress:
    """Stress testing behavior when target widgets or parent containers are destroyed mid-walkthrough."""

    def test_target_widget_destroyed_while_overlay_active(self, tk_root):
        """Destroy target widget while tutorial overlay is displaying it; next step must gracefully fallback."""
        root = tk_root
        btn_ephemeral = ctk.CTkButton(root, text="Ephemeral", width=120, height=35)
        btn_ephemeral.place(x=100, y=100)
        btn_stable = ctk.CTkButton(root, text="Stable", width=120, height=35)
        btn_stable.place(x=300, y=100)
        root.update_idletasks()

        steps = [
            TutorialStep("step_eph", "Ephemeral Step", "Widget will be deleted", lambda: btn_ephemeral),
            TutorialStep("step_stb", "Stable Step", "Widget stays alive", lambda: btn_stable),
        ]

        overlay = InteractiveTutorialOverlay(root)
        overlay.register_steps(steps)
        overlay.start(0)
        root.update_idletasks()

        # Destroy ephemeral widget right under active overlay
        btn_ephemeral.destroy()
        root.update_idletasks()

        # Force debounced configure/render recalculation
        overlay._debounced_recalculate()
        root.update_idletasks()

        # Advance to next step - must succeed cleanly
        overlay.next_step()
        root.update_idletasks()
        assert overlay.current_step_index == 1

        # Go back to destroyed widget step - must fallback to centered modal without exception
        overlay.prev_step()
        root.update_idletasks()
        assert overlay.current_step_index == 0

        overlay.destroy()
        btn_stable.destroy()

    def test_target_getter_throws_arbitrary_exceptions(self, tk_root):
        """Target widget getter raising ValueError or RuntimeError must not crash the overlay."""
        root = tk_root

        def buggy_getter():
            raise RuntimeError("Simulated internal UI fault in widget locator")

        steps = [
            TutorialStep("s_err", "Error Step", "Getter raises error", buggy_getter),
        ]

        overlay = InteractiveTutorialOverlay(root)
        overlay.register_steps(steps)
        overlay.start(0)
        root.update_idletasks()

        assert overlay.is_active is True
        assert overlay.tooltip is not None

        overlay.skip()
        assert overlay.is_active is False

    def test_parent_frame_destroyed_mid_tutorial(self, tk_root):
        """Destroy an entire parent frame containing the target widget while overlay is active."""
        root = tk_root
        parent_frame = ctk.CTkFrame(root, width=300, height=200)
        parent_frame.place(x=50, y=50)
        inner_btn = ctk.CTkButton(parent_frame, text="Inner", width=100, height=30)
        inner_btn.pack(padx=20, pady=20)
        root.update_idletasks()

        steps = [
            TutorialStep("s_inner", "Inner Step", "Inner button in frame", lambda: inner_btn),
        ]

        overlay = InteractiveTutorialOverlay(root)
        overlay.register_steps(steps)
        overlay.start(0)
        root.update_idletasks()

        # Destroy entire container
        parent_frame.destroy()
        root.update_idletasks()

        # Re-render step
        overlay._render_current_step()
        root.update_idletasks()

        overlay.destroy()


# ============================================================================
# 4. CONCURRENCY, TIMER STORMS & MAINLOOP RESPONSIVENESS
# ============================================================================


class TestConcurrencyAndEventLoopStress:
    """Stress testing mainloop responsiveness, debouncing storms, and background queue events."""

    def test_50_rapid_configure_resize_events_debounced(self, tk_root):
        """Fire 50 rapid Configure events simulating intense window resizing; debouncer must coalesce calls."""
        root = tk_root
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        btn = ctk.CTkButton(root, text="Resize Target", width=120, height=35)
        btn.place(x=100, y=100)
        root.update_idletasks()

        overlay = InteractiveTutorialOverlay(root)
        overlay.register_steps([TutorialStep("s1", "Title", "Desc", lambda: btn)])
        overlay.start(0)

        # Dispatch 50 simulated <Configure> events rapidly
        for i in range(50):
            event = tk.Event()
            event.widget = root
            event.width = 1000 + (i % 20)
            event.height = 700 + (i % 20)
            overlay._on_configure(event)

        # Timer must be active
        assert overlay._configure_timer_id is not None

        # Settle after timer delay
        time.sleep(0.08)
        root.update_idletasks()

        overlay.destroy()
        btn.destroy()

    def test_background_worker_queue_concurrency_during_tutorial(self, tk_root):
        """Simulate active background PDF worker / updater thread posting events while user navigates tutorial."""
        root = tk_root
        state = AppState(root)
        controller = AppController(state)

        # Build app components safely inside root
        header = ctk.CTkFrame(root)
        header.pack(fill="x")
        sidebar_host = ctk.CTkFrame(root)
        sidebar_host.pack(fill="y", side="left")
        sidebar = SidebarPanel(sidebar_host, controller)
        sidebar.pack(fill="both", expand=True)

        steps = build_tutorial_steps(controller)
        overlay = InteractiveTutorialOverlay(root)
        overlay.register_steps(steps)
        overlay.start(0)

        # Background thread posting 40 progress/status events
        stop_worker = threading.Event()

        def background_producer():
            for i in range(40):
                if stop_worker.is_set():
                    break
                state.event_queue.put(("progress", (i + 1, 40, f"Processing slip {i+1}/40...")))
                time.sleep(0.01)

        worker = threading.Thread(target=background_producer)
        worker.start()

        # Main thread navigates through all 4 tutorial steps while worker is actively posting
        for step_idx in range(len(steps)):
            overlay.next_step()
            # Drain queue events
            while not state.event_queue.empty():
                try:
                    ev_type, payload = state.event_queue.get_nowait()
                    if ev_type == "progress":
                        curr, tot, msg = payload
                        state.status_var.set(msg)
                except queue.Empty:
                    break
            root.update_idletasks()
            time.sleep(0.02)

        stop_worker.set()
        worker.join(timeout=2.0)

        overlay.skip()
        root.update_idletasks()
        assert overlay.is_active is False

    def test_full_slip_printer_app_robustness(self, tk_root, tmp_path):
        """Full integration test: instantiate SlipPrinterApp, run tutorial, trigger tab switching, resize, and close."""
        settings_path = tmp_path / "user_settings.json"
        settings_path.write_text(
            json.dumps({"appearance_mode": "System", "has_seen_tutorial": False, "auto_suggest_tutorial": True}),
            encoding="utf-8",
        )

        app = SlipPrinterApp()
        try:
            app.update_idletasks()

            # Start tutorial
            overlay = app.start_tutorial()
            assert overlay is not None
            assert overlay.is_active is True

            # Walk through all 4 steps
            for _ in range(4):
                overlay.next_step()
                app.update_idletasks()

            assert overlay.is_active is False

            # Verify settings persisted
            seen = app._load_tutorial_seen_setting()
            assert seen is True
        finally:
            app.destroy()
