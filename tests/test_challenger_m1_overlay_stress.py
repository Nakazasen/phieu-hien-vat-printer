"""Empirical Stress Test Suite by Challenger 2 for Milestone 1.

Verifies:
1. Rapid sequential calls to start(), next_step(), prev_step(), skip(), and destroy() in tight loops (50+ calls).
2. Keybinding and <Configure> unbinding lifecycle and absence of TclError / stale callback execution post-destroy.
3. Debounced timer cancellation on destroy.
4. Canvas widget raising & stacking order behavior (Canvas.lift vs Misc.lift / Tcl tag_raise).
5. TooltipCard place geometry compatibility with CustomTkinter.
6. Target widget exception and destruction resilience during active overlay.
"""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pytest

from ui.components.tutorial_overlay import (
    GeometryHelper,
    InteractiveTutorialOverlay,
    PlacementEngine,
    TabSyncHelper,
    TooltipCard,
    TutorialOverlay,
    TutorialStep,
)


@pytest.fixture
def tk_root():
    """Create a Tk/CTk root for testing and ensure clean teardown."""
    try:
        root = ctk.CTk()
    except Exception:
        root = tk.Tk()
    root.geometry("1024x768")
    root.update_idletasks()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


def make_dummy_steps(root: tk.Widget, count: int = 4) -> tuple[list[TutorialStep], list[ctk.CTkButton]]:
    """Helper to create dummy target buttons and corresponding TutorialStep objects."""
    buttons = []
    steps = []
    for i in range(count):
        btn = ctk.CTkButton(root, text=f"Target {i+1}")
        btn.place(x=50 + i * 150, y=50 + i * 50)
        buttons.append(btn)
        step = TutorialStep(
            step_id=f"step_{i+1}",
            title=f"Step {i+1} Title",
            description=f"Step {i+1} Description content here.",
            target_widget_getter=lambda b=btn: b,
        )
        steps.append(step)
    root.update_idletasks()
    return steps, buttons


# ============================================================================
# 1. RAPID SEQUENTIAL CALLS & STATE MACHINE STRESS TESTS (50+ iterations)
# ============================================================================


class TestRapidSequentialCalls:
    """Stress tests rapid sequential method invocations on TutorialOverlay."""

    def test_stress_50_rapid_start_next_prev_skip_destroy_loop(self, tk_root):
        """Stress-test: 50 cycles of (start -> next -> prev -> skip -> destroy) in tight loop."""
        steps, _ = make_dummy_steps(tk_root, 4)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        for i in range(50):
            overlay.start(0)
            assert overlay.is_active is True
            overlay.next_step()
            overlay.prev_step()
            overlay.skip()
            assert overlay.is_active is False
            overlay.destroy()
            assert overlay.is_active is False

    def test_stress_50_rapid_next_steps_beyond_bounds(self, tk_root):
        """Stress-test: 50 rapid calls to next_step() on a 3-step tutorial."""
        finish_called = []
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(
            master_window=tk_root,
            on_finish=lambda: finish_called.append(True),
        )
        overlay.register_steps(steps)
        overlay.start(0)

        for _ in range(50):
            overlay.next_step()

        assert overlay.is_active is False
        assert len(finish_called) == 1
        assert overlay.canvas is None
        assert overlay.tooltip is None

    def test_stress_50_rapid_prev_steps_clamping(self, tk_root):
        """Stress-test: 50 rapid calls to prev_step() at step 0."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)

        for _ in range(50):
            overlay.prev_step()

        assert overlay.is_active is True
        assert overlay.current_step_index == 0
        overlay.destroy()

    def test_stress_100_rapid_oscillating_next_prev(self, tk_root):
        """Stress-test: 100 rapid oscillations between next_step and prev_step."""
        steps, _ = make_dummy_steps(tk_root, 4)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(1)

        for i in range(100):
            if i % 2 == 0:
                overlay.next_step()
            else:
                overlay.prev_step()

        assert overlay.is_active is True
        overlay.destroy()
        assert overlay.is_active is False

    def test_stress_50_rapid_consecutive_start_calls(self, tk_root):
        """Stress-test: 50 rapid start() calls without destroying in between."""
        steps, _ = make_dummy_steps(tk_root, 4)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        for i in range(50):
            overlay.start(i % len(steps))
            assert overlay.is_active is True

        overlay.destroy()
        assert overlay.is_active is False

    def test_stress_50_rapid_consecutive_destroy_calls(self, tk_root):
        """Stress-test: 50 consecutive destroy() calls (idempotency)."""
        steps, _ = make_dummy_steps(tk_root, 2)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)

        for _ in range(50):
            overlay.destroy()

        assert overlay.is_active is False
        assert overlay.canvas is None
        assert overlay.tooltip is None

    def test_methods_after_destroy_are_safe_noops(self, tk_root):
        """Verify calling navigation methods after destroy does not crash or resurrect overlay."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)
        overlay.destroy()

        # Invoking navigation methods on destroyed overlay must be safe no-ops
        overlay.next_step()
        overlay.prev_step()
        overlay.skip()
        overlay.finish()
        assert overlay.is_active is False


# ============================================================================
# 2. KEYBINDINGS, CONFIGURE CALLBACKS & DESTRUCTION LIFECYCLE
# ============================================================================


class TestDestructionLifecycleAndEventUnbinding:
    """Verifies that all bound keys and <Configure> callbacks no longer execute and do not raise TclError."""

    def test_keybindings_unbound_after_destroy_no_tcl_error(self, tk_root):
        """Dispatch keyboard events after destroy() and verify no TclError or unhandled exceptions occur."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)
        assert overlay.is_active is True

        overlay.destroy()
        assert overlay.is_active is False
        assert len(overlay._bound_events) == 0

        # Dispatch all navigation keys to root window
        keys_to_test = ["<Escape>", "<Return>", "<KP_Enter>", "<Right>", "<space>", "<Left>"]
        for key in keys_to_test:
            tk_root.event_generate(key)
            tk_root.update_idletasks()

        # Check that overlay was NOT resurrected or modified
        assert overlay.is_active is False
        assert overlay.canvas is None

    def test_configure_callback_unbound_after_destroy(self, tk_root):
        """Dispatch <Configure> event after destroy() to verify no TclError or stale redraw occurs."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)

        overlay.destroy()

        # Fire Configure events on root
        tk_root.event_generate("<Configure>", width=1200, height=900)
        tk_root.update_idletasks()
        tk_root.update()

        assert overlay.is_active is False
        assert overlay.canvas is None

    def test_pending_configure_timer_cancelled_on_destroy(self, tk_root):
        """Trigger <Configure> (scheduling debounced timer) then immediately destroy().

        Verify timer is cancelled and callback does not execute after delay.
        """
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)

        # Trigger configure directly
        fake_event = tk.Event()
        fake_event.widget = tk_root
        overlay._on_configure(fake_event)

        assert overlay._configure_timer_id is not None

        # Destroy overlay while timer is pending
        overlay.destroy()
        assert overlay._configure_timer_id is None
        assert overlay.is_active is False

        # Allow time for what would have been the timer firing (60ms + margin)
        time.sleep(0.08)
        tk_root.update_idletasks()
        tk_root.update()

        # Canvas must remain None (no redraw happened)
        assert overlay.canvas is None
        assert overlay.tooltip is None


# ============================================================================
# 3. CANVAS LIFECYCLE, RAISING AND GEOMETRY RESILIENCE
# ============================================================================


class TestCanvasAndWidgetLifecycle:
    """Verifies Canvas widget raising behavior and CustomTkinter geometry compatibility."""

    def test_canvas_lift_execution_safety(self, tk_root):
        """Verify that starting and rendering overlay does NOT raise TclError from canvas.lift()."""
        steps, _ = make_dummy_steps(tk_root, 2)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        # This should execute cleanly without _tkinter.TclError: wrong # args
        overlay.start(0)
        tk_root.update_idletasks()

        assert overlay.canvas is not None
        assert overlay.canvas.winfo_exists()
        overlay.destroy()

    def test_tooltip_place_compatibility(self, tk_root):
        """Verify TooltipCard.place() does not violate CustomTkinter place argument constraints."""
        steps, _ = make_dummy_steps(tk_root, 2)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        overlay.start(0)
        tk_root.update_idletasks()

        assert overlay.tooltip is not None
        assert overlay.tooltip.winfo_exists()
        overlay.destroy()

    def test_target_widget_destroyed_while_overlay_active(self, tk_root):
        """Destroy the highlighted target widget while overlay is displayed.

        Verify subsequent redraw/configure does not crash.
        """
        steps, buttons = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)
        tk_root.update_idletasks()

        # Destroy button 1 while step 0 is active
        buttons[0].destroy()
        tk_root.update_idletasks()

        # Trigger re-render / configure
        fake_event = tk.Event()
        fake_event.widget = tk_root
        overlay._on_configure(fake_event)
        overlay._debounced_recalculate()
        tk_root.update_idletasks()

        # Should fall back to modal blackout scrim without throwing exception
        assert overlay.is_active is True
        overlay.destroy()

    def test_target_widget_getter_raising_exception(self, tk_root):
        """Step with a target_widget_getter that raises an Exception."""
        step = TutorialStep(
            step_id="error_step",
            title="Error Step",
            description="Testing exception in getter",
            target_widget_getter=lambda: (_ for _ in ()).throw(RuntimeError("Simulated getter failure")),
        )
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps([step])

        overlay.start(0)
        tk_root.update_idletasks()

        assert overlay.is_active is True
        overlay.destroy()

    def test_empty_steps_list_start_safety(self, tk_root):
        """Calling start() on overlay with empty steps list should cleanly no-op."""
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps([])
        overlay.start(0)

        assert overlay.is_active is False
        assert overlay.canvas is None
        assert overlay.tooltip is None


# ============================================================================
# 4. DEEP EMPIRICAL STRESS TEST (DIAGNOSTIC TEST HARNESS)
# ============================================================================


class TestUnderlyingStateMachineStressWithHarness:
    """Diagnostically isolates the state machine logic by bypassing the Canvas.lift()

    and CTkFrame.place(width=...) bugs via monkey-patch in test process.
    This allows comprehensive empirical validation of:
    - 50 rapid sequential calls (start, next, prev, skip, destroy)
    - Keybinding unbinding & destruction lifecycle
    - <Configure> debouncing & cancellation
    """

    @pytest.fixture(autouse=True)
    def patch_canvas_lift_and_tooltip_place(self, monkeypatch):
        """Diagnostic patch for Canvas.lift and CTk.place bugs to test remaining state machine."""
        orig_build = InteractiveTutorialOverlay._build_overlay
        orig_render = InteractiveTutorialOverlay._render_current_step

        def patched_build(self):
            if self.canvas is not None or self.tooltip is not None:
                self._cleanup_widgets()

            self.canvas = tk.Canvas(
                self.master,
                highlightthickness=0,
                borderwidth=0,
                bg=self.SCRIM_COLOR,
                cursor="arrow",
            )
            self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            tk.Misc.lift(self.canvas)

            for event_name in (
                "<Button-1>",
                "<Button-2>",
                "<Button-3>",
                "<Double-Button-1>",
                "<Triple-Button-1>",
                "<B1-Motion>",
                "<B2-Motion>",
                "<B3-Motion>",
                "<MouseWheel>",
            ):
                self.canvas.bind(event_name, lambda e: "break")

            self.tooltip = TooltipCard(
                self.master,
                width=PlacementEngine.CARD_WIDTH,
                height=PlacementEngine.CARD_HEIGHT,
                on_next=self.next_step,
                on_prev=self.prev_step,
                on_skip=self.skip,
            )
            tk.Misc.lift(self.tooltip)

        def patched_render(self):
            if not self._is_active or self._is_destroyed or not self.canvas or not self.tooltip:
                return

            if not self.steps or self._current_step_index >= len(self.steps):
                self.destroy()
                return

            step = self.steps[self._current_step_index]

            target_widget = None
            if step.target_widget_getter:
                try:
                    target_widget = step.target_widget_getter()
                except Exception:
                    target_widget = None

            self.master.update_idletasks()
            bounds = self._calculate_spotlight_bounds(target_widget, padding=step.padding)

            self._draw_scrim_and_spotlight(bounds)

            self.tooltip.update_content(
                title=step.title,
                description=step.description,
                current_index=self._current_step_index,
                total_steps=len(self.steps),
            )

            root_w = max(100, self.master.winfo_width())
            root_h = max(100, self.master.winfo_height())
            pos_x, pos_y = PlacementEngine.calculate(
                root_w=root_w,
                root_h=root_h,
                spotlight_bounds=bounds,
                card_w=PlacementEngine.CARD_WIDTH,
                card_h=PlacementEngine.CARD_HEIGHT,
                preferred_position=step.tooltip_position,
            )

            self.tooltip.place(x=pos_x, y=pos_y)
            tk.Misc.lift(self.canvas)
            tk.Misc.lift(self.tooltip)

        monkeypatch.setattr(InteractiveTutorialOverlay, "_build_overlay", patched_build)
        monkeypatch.setattr(InteractiveTutorialOverlay, "_render_current_step", patched_render)

    def test_harness_50_rapid_start_next_prev_skip_destroy_loop(self, tk_root):
        """Stress-test: 50 full cycles of rapid state transitions with diagnostic harness."""
        steps, _ = make_dummy_steps(tk_root, 4)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        for i in range(50):
            overlay.start(0)
            assert overlay.is_active is True
            assert overlay.current_step_index == 0
            overlay.next_step()
            assert overlay.current_step_index == 1
            overlay.prev_step()
            assert overlay.current_step_index == 0
            overlay.skip()
            assert overlay.is_active is False
            overlay.destroy()
            assert overlay.is_active is False
            assert overlay.canvas is None
            assert overlay.tooltip is None

    def test_harness_50_rapid_next_steps_beyond_bounds(self, tk_root):
        """Stress-test: 50 rapid next_step() calls terminating properly at end."""
        finish_called = []
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(
            master_window=tk_root,
            on_finish=lambda: finish_called.append(True),
        )
        overlay.register_steps(steps)
        overlay.start(0)

        for _ in range(50):
            overlay.next_step()

        assert overlay.is_active is False
        assert len(finish_called) == 1
        assert overlay.canvas is None
        assert overlay.tooltip is None

    def test_harness_100_oscillations_between_next_and_prev(self, tk_root):
        """Stress-test: 100 rapid oscillations between next_step and prev_step."""
        steps, _ = make_dummy_steps(tk_root, 4)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(1)

        for i in range(100):
            if i % 2 == 0:
                overlay.next_step()
            else:
                overlay.prev_step()

        assert overlay.is_active is True
        overlay.destroy()
        assert overlay.is_active is False

    def test_harness_keybindings_unbound_after_destroy(self, tk_root):
        """Verify keybindings do not trigger overlay handlers or error after destroy."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)
        assert overlay.is_active is True

        overlay.destroy()
        assert overlay.is_active is False
        assert len(overlay._bound_events) == 0

        keys_to_test = ["<Escape>", "<Return>", "<KP_Enter>", "<Right>", "<space>", "<Left>"]
        for key in keys_to_test:
            tk_root.event_generate(key)
            tk_root.update_idletasks()

        assert overlay.is_active is False
        assert overlay.canvas is None

    def test_harness_pending_configure_timer_cancelled_on_destroy(self, tk_root):
        """Verify pending debounced timer is properly cancelled and no error occurs."""
        steps, _ = make_dummy_steps(tk_root, 3)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)
        overlay.start(0)

        fake_event = tk.Event()
        fake_event.widget = tk_root
        overlay._on_configure(fake_event)

        assert overlay._configure_timer_id is not None
        overlay.destroy()
        assert overlay._configure_timer_id is None

        time.sleep(0.08)
        tk_root.update_idletasks()
        tk_root.update()

        assert overlay.canvas is None
        assert overlay.tooltip is None

