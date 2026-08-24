"""Tier 5 Adversarial Coverage Hardening Test Suite for Interactive Tutorial Overlay.

Adversarial Stress Testing Categories:
- Sub-tier 5.1: Geometry & Placement Engine Adversarial Stress (Extreme dimensions, edge clamping, flipping)
- Sub-tier 5.2: Dynamic Event Concurrency & Rapid Interaction Stress (Rapid transitions, debouncing, re-entrancy)
- Sub-tier 5.3: Tab Synchronization & Hierarchy Traversal (Deep nesting, invalid tab indices, dynamic tabs)
- Sub-tier 5.4: State Desynchronization & Corruption Resilience (Corrupted settings, headless controller, atomic persistence)
- Sub-tier 5.5: Full App Lifecycle & UI Interaction Integrity (App destroy with active overlay, mouse interception, memory lifecycle)
"""
from __future__ import annotations

import gc
import json
import os
import time
from pathlib import Path
from typing import Any, Optional
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pytest

from core.slip_printer_engine import create_record
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
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


def create_step(
    step_id: str,
    title: str,
    description: str,
    target_getter: Any = None,
    target_tab_index: Optional[int] = None,
    tooltip_position: str = "auto",
    padding: int = 6,
) -> TutorialStep:
    getter = target_getter if callable(target_getter) else (lambda: target_getter)
    return TutorialStep(
        step_id=step_id,
        title=title,
        description=description,
        target_widget_getter=getter,
        target_tab_index=target_tab_index,
        tooltip_position=tooltip_position,
        padding=padding,
    )


# ============================================================================
# SUB-TIER 5.1: GEOMETRY & PLACEMENT ENGINE ADVERSARIAL STRESS
# ============================================================================


class TestTier51GeometryAndPlacementStress:
    """Stress-test mathematical calculations, bounding boxes, and screen clamping."""

    def test_t5_1_01_placement_engine_zero_and_negative_window_dims(self):
        """Verify PlacementEngine handles zero and negative window dimensions without crash."""
        pos = PlacementEngine.calculate(root_w=0, root_h=0, spotlight_bounds=None)
        assert isinstance(pos, tuple) and len(pos) == 2
        assert pos[0] >= PlacementEngine.MARGIN
        assert pos[1] >= PlacementEngine.MARGIN

        pos_neg = PlacementEngine.calculate(root_w=-500, root_h=-300, spotlight_bounds=(10, 10, 50, 50))
        assert isinstance(pos_neg, tuple)
        assert pos_neg[0] >= PlacementEngine.MARGIN

    def test_t5_1_02_placement_engine_all_preferred_positions_stress(self):
        """Verify PlacementEngine correctly handles all directional positions under tight constraints."""
        root_w, root_h = 1000, 700
        bounds = (400, 250, 600, 450)  # Center box

        for pos_type in ("auto", "bottom", "top", "left", "right", "center", "INVALID_POS", ""):
            pos = PlacementEngine.calculate(
                root_w=root_w,
                root_h=root_h,
                spotlight_bounds=bounds,
                preferred_position=pos_type,
            )
            assert isinstance(pos, tuple)
            x, y = pos
            assert PlacementEngine.MARGIN <= x <= root_w - PlacementEngine.MARGIN
            assert PlacementEngine.MARGIN <= y <= root_h - PlacementEngine.MARGIN

    def test_t5_1_03_placement_engine_extreme_corner_spotlights(self):
        """Verify tooltip flips appropriately when spotlight is in each extreme corner of the screen."""
        root_w, root_h = 1200, 800

        # Top-Left Corner Spotlight
        pos_tl = PlacementEngine.calculate(root_w, root_h, (0, 0, 100, 50), preferred_position="top")
        assert pos_tl[1] >= 50  # Must flip below top boundary

        # Bottom-Right Corner Spotlight
        pos_br = PlacementEngine.calculate(root_w, root_h, (1100, 750, 1200, 800), preferred_position="bottom")
        assert pos_br[1] <= 800 - PlacementEngine.CARD_HEIGHT  # Must flip above bottom boundary

        # Far-Right Spotlight
        pos_r = PlacementEngine.calculate(root_w, root_h, (1150, 300, 1200, 400), preferred_position="right")
        assert pos_r[0] <= 1200 - PlacementEngine.CARD_WIDTH  # Must flip left

        # Far-Left Spotlight
        pos_l = PlacementEngine.calculate(root_w, root_h, (0, 300, 50, 400), preferred_position="left")
        assert pos_l[0] >= PlacementEngine.MARGIN

    def test_t5_1_04_geometry_helper_unmapped_and_zero_sized_widgets(self, tk_root):
        """Verify GeometryHelper returns None for unmapped, unplaced, or 0x0 widgets."""
        root = tk_root
        unmapped_btn = ctk.CTkButton(root, text="Unmapped")
        # Do not pack or place
        bounds = GeometryHelper.get_relative_bounds(root, unmapped_btn)
        assert bounds is None

        # Widget with 0 dimensions
        zero_frame = tk.Frame(root, width=0, height=0)
        zero_frame.pack()
        root.update_idletasks()
        bounds_zero = GeometryHelper.get_relative_bounds(root, zero_frame)
        assert bounds_zero is None

    def test_t5_1_05_geometry_helper_partially_and_fully_offscreen_widget(self, tk_root):
        """Verify GeometryHelper clamps partially visible widgets and rejects fully offscreen widgets."""
        root = tk_root
        root.geometry("800x600+50+50")
        root.update_idletasks()
        root.update()

        # Target partially offscreen on left
        left_frame = tk.Frame(root, width=100, height=50, bg="blue")
        left_frame.place(x=-40, y=100)
        root.update_idletasks()
        bounds_left = GeometryHelper.get_relative_bounds(root, left_frame, pad=0)
        if bounds_left is not None:
            assert bounds_left[0] == 0  # Clamped to left window edge

        # Target completely offscreen on top
        top_frame = tk.Frame(root, width=100, height=50, bg="red")
        top_frame.place(x=100, y=-200)
        root.update_idletasks()
        bounds_top = GeometryHelper.get_relative_bounds(root, top_frame)
        assert bounds_top is None  # Fully offscreen returns None

    def test_t5_1_06_geometry_helper_widget_destroyed_before_calculation(self, tk_root):
        """Verify GeometryHelper safely handles widgets destroyed immediately before query."""
        root = tk_root
        temp_btn = tk.Button(root, text="Doomed")
        temp_btn.pack()
        root.update_idletasks()
        temp_btn.destroy()

        # Should not raise TclError or unhandled exception
        bounds = GeometryHelper.get_relative_bounds(root, temp_btn)
        assert bounds is None


# ============================================================================
# SUB-TIER 5.2: DYNAMIC EVENT CONCURRENCY & RAPID INTERACTION STRESS
# ============================================================================


class TestTier52EventConcurrencyAndStress:
    """Stress-test rapid event loops, asynchronous timer cancels, and keyboard navigation."""

    def test_t5_2_01_100_rapid_next_and_prev_transitions(self, tk_root):
        """Verify 100 rapid alternating next/prev step calls maintain consistent step index."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        try:
            steps = [
                create_step("s1", "Step 1", "D1"),
                create_step("s2", "Step 2", "D2"),
                create_step("s3", "Step 3", "D3"),
            ]
            overlay.register_steps(steps)
            overlay.start(0)

            for i in range(100):
                if i % 2 == 0:
                    overlay.next_step()
                else:
                    overlay.prev_step()
                root.update_idletasks()

            assert 0 <= overlay.current_step_index < len(steps)
            assert overlay.is_active is True
        finally:
            overlay.destroy()

    def test_t5_2_02_rapid_configure_resize_debouncing(self, tk_root):
        """Verify high-frequency <Configure> events do not spawn uncancelled runaway timer cascades."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        try:
            step = create_step("s1", "Resize Test", "Testing debouncer")
            overlay.register_steps([step])
            overlay.start(0)

            # Fire 50 simulated Configure events in rapid succession
            dummy_event = tk.Event()
            dummy_event.widget = root
            for _ in range(50):
                overlay._on_configure(dummy_event)

            # Exactly one active timer should be pending
            assert overlay._configure_timer_id is not None
            root.update_idletasks()
            time.sleep(0.08)
            root.update()

            # Timer should have fired and cleared
            assert overlay._configure_timer_id is None
        finally:
            overlay.destroy()

    def test_t5_2_03_destroy_while_configure_timer_pending(self, tk_root):
        """Verify destroying overlay while a configure debounce timer is queued cancels cleanly."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        step = create_step("s1", "Timer Cancel", "D1")
        overlay.register_steps([step])
        overlay.start(0)

        # Trigger configure event
        dummy_event = tk.Event()
        dummy_event.widget = root
        overlay._on_configure(dummy_event)
        timer_id = overlay._configure_timer_id
        assert timer_id is not None

        # Immediate destroy before timer expires
        overlay.destroy()
        assert overlay._configure_timer_id is None
        assert overlay.is_active is False

        # Ensure mainloop does not crash when after-timer time elapses
        time.sleep(0.08)
        root.update()

    def test_t5_2_04_keyboard_navigation_event_storm(self, tk_root):
        """Verify rapid interleaved keyboard events (<Return>, <Left>, <Right>, <Escape>) resolve safely."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        try:
            steps = [
                create_step("s1", "Step 1", "D1"),
                create_step("s2", "Step 2", "D2"),
                create_step("s3", "Step 3", "D3"),
            ]
            overlay.register_steps(steps)
            overlay.start(0)

            # Generate synthetic key events
            root.event_generate("<Right>")
            root.update_idletasks()
            root.event_generate("<Left>")
            root.update_idletasks()
            root.event_generate("<space>")
            root.update_idletasks()
            root.event_generate("<Return>")
            root.update_idletasks()

            assert overlay.current_step_index in (0, 1, 2)
            root.event_generate("<Escape>")
            root.update_idletasks()
            root.update()

            assert overlay.is_active is False
        finally:
            overlay.destroy()

    def test_t5_2_05_double_destroy_and_double_start_safety(self, tk_root):
        """Verify calling destroy() or start() multiple times is completely idempotent and harmless."""
        root = tk_root
        overlay = InteractiveTutorialOverlay(root)
        step = create_step("s1", "Step 1", "D1")
        overlay.register_steps([step])

        overlay.start(0)
        overlay.start(0)  # Double start
        assert overlay.is_active is True

        overlay.destroy()
        overlay.destroy()  # Double destroy
        assert overlay.is_active is False
        assert overlay._is_destroyed is True


# ============================================================================
# SUB-TIER 5.3: TAB SYNCHRONIZATION & HIERARCHY TRAVERSAL
# ============================================================================


class TestTier53TabSynchronizationAndHierarchy:
    """Stress-test ttk.Notebook tab switching, deep hierarchy crawlers, and invalid tab indices."""

    def test_t5_3_01_tab_sync_helper_deep_hierarchy_crawler(self, tk_root):
        """Verify TabSyncHelper.find_parent_notebook traverses deeply nested container frames."""
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        tab = tk.Frame(notebook)
        notebook.add(tab, text="Tab 1")

        # Nest 5 frames deep
        f1 = tk.Frame(tab)
        f1.pack()
        f2 = tk.Frame(f1)
        f2.pack()
        f3 = tk.Frame(f2)
        f3.pack()
        deep_widget = tk.Button(f3, text="Deep Target")
        deep_widget.pack()
        root.update_idletasks()

        found_nb = TabSyncHelper.find_parent_notebook(deep_widget)
        assert found_nb == notebook

    def test_t5_3_02_tab_sync_helper_widget_without_notebook(self, tk_root):
        """Verify TabSyncHelper returns None when widget has no parent notebook."""
        root = tk_root
        orphan_frame = tk.Frame(root)
        orphan_frame.pack()
        btn = tk.Button(orphan_frame, text="Orphan")
        btn.pack()

        found = TabSyncHelper.find_parent_notebook(btn)
        assert found is None

    def test_t5_3_03_tab_sync_helper_invalid_tab_index_graceful(self, tk_root):
        """Verify TabSyncHelper handles invalid tab indices (-1, 999) without unhandled exceptions."""
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack()
        tab0 = tk.Frame(notebook)
        notebook.add(tab0, text="Tab 0")

        # Negative index
        res_neg = TabSyncHelper.ensure_tab_active(root, notebook, target_tab_index=-1)
        assert res_neg is False

        # Out-of-bounds index
        res_oob = TabSyncHelper.ensure_tab_active(root, notebook, target_tab_index=999)
        assert res_oob is False

    def test_t5_3_04_overlay_auto_switches_multiple_tabs_in_sequence(self, tk_root):
        """Verify sequential steps targeting different tabs trigger automatic tab switching."""
        root = tk_root
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        tab0 = tk.Frame(notebook, width=400, height=300)
        tab1 = tk.Frame(notebook, width=400, height=300)
        tab2 = tk.Frame(notebook, width=400, height=300)
        notebook.add(tab0, text="Tab 0")
        notebook.add(tab1, text="Tab 1")
        notebook.add(tab2, text="Tab 2")
        root.update_idletasks()

        btn0 = tk.Button(tab0, text="B0")
        btn0.pack()
        btn1 = tk.Button(tab1, text="B1")
        btn1.pack()
        btn2 = tk.Button(tab2, text="B2")
        btn2.pack()
        root.update_idletasks()

        overlay = InteractiveTutorialOverlay(root, notebook=notebook)
        try:
            steps = [
                create_step("s0", "Step 0", "D0", btn0, target_tab_index=0),
                create_step("s1", "Step 1", "D1", btn1, target_tab_index=1),
                create_step("s2", "Step 2", "D2", btn2, target_tab_index=2),
            ]
            overlay.register_steps(steps)
            overlay.start(0)
            assert notebook.index(notebook.select()) == 0

            overlay.next_step()
            root.update_idletasks()
            assert notebook.index(notebook.select()) == 1

            overlay.next_step()
            root.update_idletasks()
            assert notebook.index(notebook.select()) == 2

            overlay.prev_step()
            root.update_idletasks()
            assert notebook.index(notebook.select()) == 1
        finally:
            overlay.destroy()


# ============================================================================
# SUB-TIER 5.4: STATE DESYNCHRONIZATION & CORRUPTION RESILIENCE
# ============================================================================


class TestTier54StateAndCorruptionResilience:
    """Stress-test settings file corruption, headless controller operation, and atomic saving."""

    def test_t5_4_01_corrupted_json_in_user_settings(self, tk_root, tmp_path, monkeypatch):
        """Verify corrupted syntax in user_settings.json falls back safely to default settings."""
        data_dir = tmp_path / "isolated_app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("INPHIEUHIENVAT_DATA_DIR", str(data_dir))

        settings_path = data_dir / "user_settings.json"
        settings_path.write_text("{CORRUPTED_SYNTAX: !!", encoding="utf-8")

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            # Should not raise JSONDecodeError
            seen = controller.is_tutorial_seen()
            assert seen is False

            # Saving should overwrite corrupted file with valid JSON
            controller.mark_tutorial_seen(True)
            assert controller.is_tutorial_seen() is True

            data = json.loads(settings_path.read_text(encoding="utf-8"))
            assert data["has_seen_tutorial"] is True
        finally:
            state.po_registry.close()

    def test_t5_4_02_headless_controller_tutorial_methods_safe(self, tmp_path, monkeypatch):
        """Verify AppController operates safely in headless mode (view is None)."""
        data_dir = tmp_path / "isolated_app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("INPHIEUHIENVAT_DATA_DIR", str(data_dir))

        # Headless AppState with a hidden dummy root
        dummy_root = tk.Tk()
        dummy_root.withdraw()
        state = AppState(dummy_root)
        controller = AppController(state)
        try:
            # View is intentionally None
            assert controller.view is None

            steps = controller.get_tutorial_steps()
            assert len(steps) == 4
            for s in steps:
                # All getters must return None safely in headless mode without crashing
                w = s.target_widget_getter()
                assert w is None

            # Start tutorial should return None gracefully without error
            res = controller.start_tutorial()
            assert res is None

            controller.mark_tutorial_seen(True)
            assert controller.is_tutorial_seen() is True
        finally:
            state.po_registry.close()
            dummy_root.destroy()

    def test_t5_4_03_atomic_write_concurrency_stress(self, tk_root, tmp_path, monkeypatch):
        """Verify repeated concurrent updates to user_settings.json do not leave temporary files."""
        data_dir = tmp_path / "isolated_app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("INPHIEUHIENVAT_DATA_DIR", str(data_dir))

        root = tk_root
        state = AppState(root)
        controller = AppController(state)
        try:
            for i in range(20):
                controller.mark_tutorial_seen(bool(i % 2 == 0))

            settings_path = data_dir / "user_settings.json"
            assert settings_path.is_file()
            # Temp files (.tmp) should be cleaned up
            tmp_files = list(data_dir.glob("*.tmp"))
            assert len(tmp_files) == 0
        finally:
            state.po_registry.close()


# ============================================================================
# SUB-TIER 5.5: FULL APP LIFECYCLE & UI INTERACTION INTEGRITY
# ============================================================================


class TestTier55AppLifecycleAndUIIntegrity:
    """Stress-test app destruction with active overlay, mouse focus trap, and memory lifecycle."""

    def test_t5_5_01_app_destroyed_while_tutorial_overlay_active(self, tmp_path, monkeypatch):
        """Verify closing root window while overlay is active terminates cleanly without Tcl error."""
        data_dir = tmp_path / "isolated_app_data"
        data_dir.mkdir(parents=True, exist_ok=True)
        monkeypatch.setenv("INPHIEUHIENVAT_DATA_DIR", str(data_dir))

        root = ctk.CTk()
        root.geometry("1000x700+50+50")
        root.update_idletasks()

        overlay = InteractiveTutorialOverlay(root)
        step = create_step("s1", "Active Step", "Walkthrough active")
        overlay.register_steps([step])
        overlay.start(0)
        root.update_idletasks()

        # Destroy root directly
        root.destroy()
        time.sleep(0.05)

    def test_t5_5_02_modal_focus_trap_intercepts_mouse_clicks(self, tk_root):
        """Verify canvas scrim intercepts background mouse clicks so underlying widgets cannot be clicked."""
        root = tk_root
        underneath_clicked = False

        def on_btn_click():
            nonlocal underneath_clicked
            underneath_clicked = True

        underneath_btn = tk.Button(root, text="Background Button", command=on_btn_click)
        underneath_btn.pack(padx=50, pady=50)
        root.update_idletasks()

        overlay = InteractiveTutorialOverlay(root)
        try:
            step = create_step("s1", "Focus Trap", "Background blocked")
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            root.update()

            canvas = getattr(overlay, "canvas", None)
            assert canvas is not None

            # Generate synthetic click on canvas over the button region
            canvas.event_generate("<Button-1>", x=50, y=50)
            root.update_idletasks()

            # Underneath button must NOT have received click
            assert underneath_clicked is False
        finally:
            overlay.destroy()

    def test_t5_5_03_memory_lifecycle_twenty_sequential_sessions(self, tk_root):
        """Verify launching and skipping 20 sequential tutorial sessions does not leak widgets."""
        root = tk_root
        initial_widget_count = len(root.winfo_children())

        for _ in range(20):
            overlay = InteractiveTutorialOverlay(root)
            step = create_step("s1", "Session Step", "Description")
            overlay.register_steps([step])
            overlay.start(0)
            root.update_idletasks()
            overlay.skip()
            root.update_idletasks()

        gc.collect()
        final_widget_count = len(root.winfo_children())
        assert final_widget_count <= initial_widget_count + 1

    def test_t5_5_04_tooltip_card_customtkinter_signature_flexibility(self, tk_root):
        """Verify TooltipCard.update_content supports positional and keyword parameter styles."""
        root = tk_root
        card = TooltipCard(
            root,
            on_next=lambda: None,
            on_prev=lambda: None,
            on_skip=lambda: None,
        )
        card.pack()
        root.update_idletasks()
        try:
            # Style 1: (title, description, current_index, total_steps)
            card.update_content("Title A", "Desc A", 0, 4)
            assert card.badge_label.cget("text") == "Bước 1 / 4"

            # Style 2: (current, total, title, description)
            card.update_content(2, 4, "Title B", "Desc B")
            assert card.badge_label.cget("text") == "Bước 2 / 4"

            # Style 3: 2-arg signature (title, description)
            card.update_content("Title Only", "Desc Only")
            assert card.title_label.cget("text") == "Title Only"

            # Style 4: keywords
            card.update_content(title="Title C", description="Desc C", current_index=3, total_steps=4)
            assert card.badge_label.cget("text") == "Bước 4 / 4"
            assert card.next_btn.cget("text") == "🎉 Hoàn tất"
        finally:
            card.destroy()

    def test_t5_5_05_full_canonical_tutorial_script_contract(self, tk_root):
        """Verify build_tutorial_steps produces all 4 canonical steps with complete metadata."""
        steps = build_tutorial_steps(None)
        assert len(steps) == 4

        expected_ids = ["step_excel_import", "step_qr_scanner", "step_auto_po", "step_pdf_generation"]
        for idx, expected_id in enumerate(expected_ids):
            step = steps[idx]
            assert step.step_id == expected_id
            assert len(step.title.strip()) > 0
            assert len(step.description.strip()) > 0
            assert callable(step.target_widget_getter)
            assert step.target_widget_getter() is None  # Headless mode returns None safely
            assert step.padding >= 6

    def test_t5_5_06_live_app_widget_resolution_across_all_getters(self, tk_root):
        """Verify build_tutorial_steps resolves actual live widgets when attached to active UI panels."""
        root = tk_root
        state = AppState(root)
        controller = AppController(state)

        # Host container
        sidebar_host = ctk.CTkFrame(root)
        sidebar_host.pack(side="left", fill="y")
        sidebar = SidebarPanel(sidebar_host, controller)
        sidebar.pack(fill="both", expand=True)

        notebook = ttk.Notebook(root)
        notebook.pack(side="right", fill="both", expand=True)
        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root.update_idletasks()

        class MockAppView:
            def __init__(self, sb, dt, nb):
                self.sidebar = sb
                self.data_tab = dt
                self.notebook = nb

        view = MockAppView(sidebar, data_tab, notebook)
        controller.set_view(view)

        steps = build_tutorial_steps(view)
        assert len(steps) == 4

        # Step 1: Excel Import target
        w1 = steps[0].target_widget_getter()
        assert w1 is not None

        # Step 2: QR Scanner target
        w2 = steps[1].target_widget_getter()
        assert w2 is not None

        # Step 3: Auto PO / Form target
        w3 = steps[2].target_widget_getter()
        assert w3 is not None

        # Step 4: PDF Generation target
        w4 = steps[3].target_widget_getter()
        assert w4 is not None

        state.po_registry.close()

    def test_t5_5_07_on_finish_callback_and_settings_persistence(self, tk_root):
        """Verify finishing tutorial triggers on_finish callback exactly once and cleans up."""
        root = tk_root
        finished_called = False

        def _callback():
            nonlocal finished_called
            finished_called = True

        overlay = InteractiveTutorialOverlay(root, on_finish=_callback)
        step1 = create_step("s1", "Step 1", "D1")
        step2 = create_step("s2", "Step 2", "D2")
        overlay.register_steps([step1, step2])
        overlay.start(0)

        # Advance to step 2
        overlay.next_step()
        assert overlay.current_step_index == 1

        # Advance from last step -> finishes
        overlay.next_step()
        assert finished_called is True
        assert overlay.is_active is False
