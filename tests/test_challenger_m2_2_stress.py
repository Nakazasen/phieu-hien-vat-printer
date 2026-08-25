"""Empirical Stress Test Suite for Milestone 2.2 by Challenger (teamwork_preview_challenger).

Objectives:
1. Verify walkthrough navigation across all 4 steps with tab 0 synchronization.
2. Stress test widget getters under missing/mock/partial/faulty app objects to ensure 0 crashes.
3. Stress test overlay rendering and event handling across all 4 steps with live UI components.
4. Stress test boundary, cyclic, and rapid navigation scenarios.
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk
from typing import Any
from unittest.mock import MagicMock
import customtkinter as ctk
import pytest

from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.qr_scan_tab import QRScanTabPanel
from ui.components.sidebar import SidebarPanel
from ui.components.tutorial_overlay import (
    GeometryHelper,
    InteractiveTutorialOverlay,
    PlacementEngine,
    TabSyncHelper,
    TooltipCard,
    TutorialOverlay,
    TutorialStep,
)
from ui.components.tutorial_script import _resolve_app, build_tutorial_steps
from ui.main_window import SlipPrinterApp


@pytest.fixture
def tk_root():
    """Create a Tk/CTk root for testing and ensure clean teardown."""
    try:
        root = ctk.CTk()
    except Exception:
        root = tk.Tk()
    root.geometry("1200x800")
    root.update_idletasks()
    root.update()
    yield root
    try:
        root.destroy()
    except Exception:
        pass


# ============================================================================
# 1. 4-STEP WALKTHROUGH & TAB 0 SYNCHRONIZATION STRESS TESTS
# ============================================================================


class TestTab0SynchronizationAndWalkthrough:
    """Stress tests for tab 0 synchronization across all 4 walkthrough steps."""

    def test_all_4_steps_explicit_target_tab_indexes(self):
        """Verify canonical target tabs: all steps on tab 0 except the QR step on its dedicated tab 3."""
        expected_by_id = {
            "step_excel_import": 0,
            "step_qr_scanner": 3,
            "step_auto_po": 0,
            "step_pdf_generation": 0,
        }
        for app_input in (None, object(), MagicMock()):
            steps = build_tutorial_steps(app_input)
            assert len(steps) == 4, f"Expected exactly 4 steps, got {len(steps)}"
            for idx, step in enumerate(steps):
                expected = expected_by_id[step.step_id]
                assert step.target_tab_index == expected, (
                    f"Step {idx} ({step.step_id}) has target_tab_index={step.target_tab_index}, expected {expected}"
                )

    def test_walkthrough_synchronizes_tab_from_non_zero_start(self, tk_root):
        """Verify overlay forces notebook tab 0 when started while on Tab 1 or Tab 2."""
        notebook = ttk.Notebook(tk_root)
        notebook.place(x=0, y=0, width=800, height=600)

        tab0 = ctk.CTkFrame(notebook)
        tab1 = ctk.CTkFrame(notebook)
        tab2 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Dữ liệu")
        notebook.add(tab1, text="Căn chỉnh")
        notebook.add(tab2, text="Lịch sử")

        # Set active tab to Tab 2 initially
        notebook.select(2)
        tk_root.update_idletasks()
        tk_root.update()
        assert notebook.index(notebook.select()) == 2

        steps = build_tutorial_steps(None)
        overlay = InteractiveTutorialOverlay(master_window=tk_root, notebook=notebook)
        overlay.register_steps(steps)

        try:
            overlay.start(0)
            tk_root.update_idletasks()
            tk_root.update()

            # Should immediately switch to tab 0
            assert notebook.index(notebook.select()) == 0
            assert overlay.current_step_index == 0
        finally:
            overlay.destroy()

    def test_walkthrough_navigation_across_all_4_steps_maintains_expected_tabs(self, tk_root):
        """Verify complete forward and backward walkthrough recovers the expected tab even if tampered.

        Tab map: steps 1/3/4 -> tab 0; step 2 (QR scanner) -> dedicated tab 3.
        """
        notebook = ttk.Notebook(tk_root)
        notebook.place(x=0, y=0, width=800, height=600)

        tab0 = ctk.CTkFrame(notebook)
        tab1 = ctk.CTkFrame(notebook)
        tab2 = ctk.CTkFrame(notebook)
        tab3 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Tab 0")
        notebook.add(tab1, text="Tab 1")
        notebook.add(tab2, text="Tab 2")
        notebook.add(tab3, text="Tab 3")
        tk_root.update_idletasks()
        tk_root.update()

        steps = build_tutorial_steps(None)
        overlay = InteractiveTutorialOverlay(master_window=tk_root, notebook=notebook)
        overlay.register_steps(steps)

        expected_tab_for_step = {0: 0, 1: 3, 2: 0, 3: 0}

        def _render_and_assert(step_idx: int) -> None:
            tk_root.update_idletasks()
            tk_root.update()
            assert overlay.current_step_index == step_idx
            assert notebook.index(notebook.select()) == expected_tab_for_step[step_idx]

        try:
            overlay.start(0)
            _render_and_assert(0)

            # Step 1 -> Step 2 (QR tab)
            overlay.next_step()
            _render_and_assert(1)

            # Simulate external tamper: switch notebook to Tab 1
            notebook.select(1)
            assert notebook.index(notebook.select()) == 1

            # Step 2 -> Step 3: Must auto-recover to Tab 0
            overlay.next_step()
            _render_and_assert(2)

            # Tamper again to Tab 1
            notebook.select(1)

            # Step 3 -> Step 4: Must auto-recover to Tab 0
            overlay.next_step()
            _render_and_assert(3)

            # Navigate backward: Step 4 -> Step 3 -> Step 2 -> Step 1
            for expected_idx in (2, 1, 0):
                notebook.select(1)  # Tamper before every step
                overlay.prev_step()
                tk_root.update_idletasks()
                tk_root.update()
                assert overlay.current_step_index == expected_idx
                assert notebook.index(notebook.select()) == expected_tab_for_step[expected_idx]
        finally:
            overlay.destroy()

    def test_tab_sync_helper_edge_cases(self, tk_root):
        """Stress-test TabSyncHelper under None, destroyed notebook, invalid tab indexes, etc."""
        # 1. All None
        assert TabSyncHelper.ensure_tab_active(tk_root, None, None) is False
        assert TabSyncHelper.ensure_tab_active(tk_root, None, 0) is False

        # 2. Target tab index out of range
        notebook = ttk.Notebook(tk_root)
        notebook.place(x=0, y=0, width=400, height=300)
        tab0 = ctk.CTkFrame(notebook)
        notebook.add(tab0, text="Tab 0")
        tk_root.update_idletasks()
        tk_root.update()

        # Out of bounds index
        res = TabSyncHelper.ensure_tab_active(tk_root, notebook, 999)
        assert res is False

        # Negative index
        res = TabSyncHelper.ensure_tab_active(tk_root, notebook, -5)
        # Should not crash
        assert isinstance(res, bool)

        # 3. Destroyed notebook
        notebook.destroy()
        res = TabSyncHelper.ensure_tab_active(tk_root, notebook, 0)
        assert res is False


# ============================================================================
# 2. WIDGET GETTERS ADVERSARIAL STRESS TESTS (0 CRASH GUARANTEE)
# ============================================================================


class TestWidgetGettersAdversarialResilience:
    """Stress tests widget getters against malicious, broken, cyclic, and partial objects."""

    @pytest.mark.parametrize(
        "invalid_input",
        [
            None,
            "",
            "invalid_string",
            12345,
            -99.9,
            [],
            [1, 2, 3],
            {},
            {"sidebar": "fake"},
            True,
            False,
            object(),
            lambda: None,
            sys,
        ],
    )
    def test_widget_getters_under_primitive_and_arbitrary_types(self, invalid_input):
        """Ensure all 4 widget getters execute cleanly and return None for non-app objects."""
        steps = build_tutorial_steps(invalid_input)
        assert len(steps) == 4
        for idx, step in enumerate(steps):
            try:
                widget = step.target_widget_getter()
                assert widget is None or widget is invalid_input
            except Exception as exc:
                pytest.fail(f"Step {idx} ({step.step_id}) crashed with input {invalid_input!r}: {exc}")

    def test_widget_getters_under_cyclic_references(self):
        """Ensure widget getters handle cyclic app structures without infinite recursion / RecursionError."""
        class CyclicApp:
            def __init__(self):
                self.view = self
                self.sidebar = self
                self.data_tab = self

        app = CyclicApp()
        steps = build_tutorial_steps(app)
        for idx, step in enumerate(steps):
            try:
                res = step.target_widget_getter()
                assert res is not None or res is None
            except RecursionError:
                pytest.fail(f"Step {idx} caused RecursionError on cyclic app")
            except Exception as exc:
                pytest.fail(f"Step {idx} raised unexpected exception on cyclic app: {exc}")

    def test_widget_getters_when_attributes_raise_arbitrary_exceptions(self):
        """Ensure widget getters catch any exception raised during property access or method invocation."""
        class ExplodingObject:
            def __getattr__(self, name):
                raise RuntimeError(f"Explosion accessing {name}")

        class ExplodingMethodsSidebar:
            def get_excel_import_widget(self):
                raise TypeError("Type mismatch in Excel getter")

            def get_qr_scan_widget(self):
                raise ValueError("Value error in QR getter")

            def get_generate_pdf_widget(self):
                raise MemoryError("OOM in PDF getter")

            @property
            def excel_import_button(self):
                raise AttributeError("Property access error")

        class ExplodingMethodsDataTab:
            def get_form_frame(self):
                raise ZeroDivisionError("Math error in form getter")

            def get_qr_button_widget(self):
                raise KeyError("Missing key in QR button")

            def get_preview_frame(self):
                raise IndexError("Index out of range in preview")

        class HostileApp:
            sidebar = ExplodingMethodsSidebar()
            data_tab = ExplodingMethodsDataTab()

        # Test hostile app with throwing methods
        steps = build_tutorial_steps(HostileApp())
        for idx, step in enumerate(steps):
            try:
                res = step.target_widget_getter()
                assert res is not None or res is None
            except Exception as exc:
                pytest.fail(f"Step {idx} failed to contain exception: {exc}")

        # Test completely exploding object
        exploding_steps = build_tutorial_steps(ExplodingObject())
        for idx, step in enumerate(exploding_steps):
            try:
                res = step.target_widget_getter()
                assert res is not None or res is None
            except Exception as exc:
                pytest.fail(f"Step {idx} failed to contain exploding getattr: {exc}")

    def test_widget_getters_with_partial_mock_permutations(self):
        """Test all permutations of partial app structures (sidebar only, data_tab only, None sub-properties)."""
        mock_btn = object()

        # Permutation 1: Sidebar only, no data_tab
        class AppSidebarOnly:
            def __init__(self):
                class DummySidebar:
                    def get_excel_import_widget(self):
                        return mock_btn
                    def get_qr_scan_widget(self):
                        return mock_btn
                    def get_generate_pdf_widget(self):
                        return mock_btn
                self.sidebar = DummySidebar()
                self.data_tab = None

        steps1 = build_tutorial_steps(AppSidebarOnly())
        assert steps1[0].target_widget_getter() is mock_btn
        assert steps1[1].target_widget_getter() is mock_btn
        assert steps1[2].target_widget_getter() is None  # Step 3 needs data_tab
        assert steps1[3].target_widget_getter() is mock_btn

        # Permutation 2: DataTab only, no sidebar
        class AppDataTabOnly:
            def __init__(self):
                class DummyDataTab:
                    def get_form_frame(self):
                        return mock_btn
                    def get_qr_button_widget(self):
                        return mock_btn
                    def get_preview_frame(self):
                        return mock_btn
                self.sidebar = None
                self.data_tab = DummyDataTab()

        steps2 = build_tutorial_steps(AppDataTabOnly())
        assert steps2[0].target_widget_getter() is None  # Step 1 needs sidebar
        assert steps2[1].target_widget_getter() is mock_btn  # Step 2 falls back to data_tab qr button
        assert steps2[2].target_widget_getter() is mock_btn  # Step 3 gets form frame
        assert steps2[3].target_widget_getter() is mock_btn  # Step 4 falls back to data_tab preview

        # Permutation 3: Methods return None, fallback attributes present
        class AppFallback:
            def __init__(self):
                class DummySidebar:
                    def get_excel_import_widget(self):
                        return None
                    def get_qr_scan_widget(self):
                        return None
                    def get_generate_pdf_widget(self):
                        return None
                    excel_frame = mock_btn
                    btn_qr_scan = mock_btn
                    btn_generate_pdf = mock_btn

                class DummyDataTab:
                    def get_form_frame(self):
                        return None
                    btn_add_record = mock_btn

                self.sidebar = DummySidebar()
                self.data_tab = DummyDataTab()

        steps3 = build_tutorial_steps(AppFallback())
        assert steps3[0].target_widget_getter() is mock_btn
        assert steps3[1].target_widget_getter() is mock_btn
        assert steps3[2].target_widget_getter() is mock_btn
        assert steps3[3].target_widget_getter() is mock_btn

    def test_widget_getters_with_dead_or_unmapped_widgets(self, tk_root):
        """Verify GeometryHelper and getters safely handle widgets that are destroyed or unmapped."""
        btn_alive = tk.Button(tk_root, text="Alive", width=15, height=2)
        btn_alive.place(x=10, y=10, width=120, height=40)
        btn_dead = tk.Button(tk_root, text="Dead", width=15, height=2)
        btn_dead.place(x=50, y=50, width=120, height=40)
        btn_unmapped = tk.Button(tk_root, text="Unmapped")  # Not placed

        tk_root.update_idletasks()
        tk_root.update()
        btn_dead.destroy()

        # GeometryHelper on dead widget
        bounds_dead = GeometryHelper.get_relative_bounds(tk_root, btn_dead)
        assert bounds_dead is None

        # GeometryHelper on unmapped widget
        bounds_unmapped = GeometryHelper.get_relative_bounds(tk_root, btn_unmapped)
        assert bounds_unmapped is None

        # GeometryHelper on None
        bounds_none = GeometryHelper.get_relative_bounds(tk_root, None)
        assert bounds_none is None

        # GeometryHelper on alive mapped widget
        bounds_alive = GeometryHelper.get_relative_bounds(tk_root, btn_alive)
        assert bounds_alive is not None
        assert bounds_alive[0] < bounds_alive[2]


# ============================================================================
# 3. FULL APP SIMULATION & STEP-BY-STEP HIGHLIGHT VALIDATION
# ============================================================================


class TestFullAppTutorialIntegration:
    """Tests tutorial walkthrough on real UI hierarchy with Notebook, Sidebar, and DataTab."""

    def test_full_live_app_walkthrough_and_spotlight_coordinates(self, tk_root):
        """Build live SidebarPanel and DataTabPanel and execute 4-step walkthrough verifying each spotlight."""
        state = AppState(tk_root)
        controller = AppController(state)

        # Build composite structure matching SlipPrinterApp layout
        paned = ttk.Panedwindow(tk_root, orient="horizontal")
        paned.pack(fill="both", expand=True)

        sidebar_host = ctk.CTkFrame(paned, corner_radius=14)
        sidebar_host.grid_rowconfigure(0, weight=1)
        sidebar_host.grid_columnconfigure(0, weight=1)
        sidebar = SidebarPanel(sidebar_host, controller)
        sidebar.grid(row=0, column=0, sticky="nsew")
        paned.add(sidebar_host, weight=1)

        content = ctk.CTkFrame(paned, corner_radius=14)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)
        paned.add(content, weight=3)

        notebook = ttk.Notebook(content)
        notebook.grid(row=0, column=0, sticky="nsew")

        data_tab_frame = ctk.CTkFrame(notebook)
        layout_tab_frame = ctk.CTkFrame(notebook)
        notebook.add(data_tab_frame, text="Dữ liệu")
        notebook.add(layout_tab_frame, text="Căn chỉnh")

        data_tab = DataTabPanel(data_tab_frame, controller)
        data_tab.pack(fill="both", expand=True)

        qr_tab = QRScanTabPanel(notebook, controller)
        notebook.add(qr_tab, text="Quét QR")

        class LiveAppComposite:
            def __init__(self, s, d, nb, q):
                self.sidebar = s
                self.data_tab = d
                self.notebook = nb
                self.qr_tab = q

        app_composite = LiveAppComposite(sidebar, data_tab, notebook, qr_tab)
        tk_root.update_idletasks()
        tk_root.update()

        steps = build_tutorial_steps(app_composite)
        overlay = InteractiveTutorialOverlay(master_window=tk_root, notebook=notebook)
        overlay.register_steps(steps)

        try:
            # --- STEP 1: Excel Import ---
            overlay.start(0)
            tk_root.update_idletasks()
            tk_root.update()

            assert overlay.current_step_index == 0
            assert overlay.is_active is True
            target1 = steps[0].target_widget_getter()
            assert target1 is sidebar.excel_import_button
            # Verify tooltip card reflects step 1
            assert overlay.tooltip.badge_label.cget("text") == "Bước 1 / 4"
            assert "Excel" in overlay.tooltip.title_label.cget("text")

            # --- STEP 2: QR Scanner ---
            overlay.next_step()
            tk_root.update_idletasks()
            tk_root.update()

            assert overlay.current_step_index == 1
            target2 = steps[1].target_widget_getter()
            assert target2 is qr_tab.scan_panel
            assert overlay.tooltip.badge_label.cget("text") == "Bước 2 / 4"
            assert "QR" in overlay.tooltip.title_label.cget("text")

            # --- STEP 3: Auto PO & Form ---
            overlay.next_step()
            tk_root.update_idletasks()
            tk_root.update()

            assert overlay.current_step_index == 2
            target3 = steps[2].target_widget_getter()
            assert target3 in (data_tab.form_frame, data_tab.btn_add_record)
            assert overlay.tooltip.badge_label.cget("text") == "Bước 3 / 4"
            assert "Auto PO" in overlay.tooltip.title_label.cget("text")

            # --- STEP 4: PDF Generation ---
            overlay.next_step()
            tk_root.update_idletasks()
            tk_root.update()

            assert overlay.current_step_index == 3
            target4 = steps[3].target_widget_getter()
            assert target4 in (sidebar.generate_button, data_tab.preview_frame)
            assert overlay.tooltip.badge_label.cget("text") == "Bước 4 / 4"
            assert "PDF" in overlay.tooltip.title_label.cget("text")
            assert overlay.tooltip.next_btn.cget("text") == "🎉 Hoàn tất"

            # Finish
            overlay.next_step()
            tk_root.update_idletasks()
            tk_root.update()

            assert overlay.is_active is False
            assert overlay.canvas is None
            assert overlay.tooltip is None
        finally:
            overlay.destroy()
            sidebar.destroy()
            data_tab.destroy()
            paned.destroy()
            state.po_registry.close()

    def test_live_app_controller_integration(self, tk_root):
        """Verify AppController get_tutorial_steps() wires directly with view and build_tutorial_steps."""
        state = AppState(tk_root)
        controller = AppController(state)

        # 1. Without view: safe headless steps
        headless_steps = controller.get_tutorial_steps()
        assert len(headless_steps) == 4
        for s in headless_steps:
            assert s.target_widget_getter() is None

        # 2. With view attached
        mock_view = MagicMock()
        mock_view.sidebar = MagicMock()
        mock_view.data_tab = MagicMock()
        mock_btn = object()
        mock_view.sidebar.get_excel_import_widget.return_value = mock_btn
        controller.set_view(mock_view)

        attached_steps = controller.get_tutorial_steps()
        assert len(attached_steps) == 4
        assert attached_steps[0].target_widget_getter() is mock_btn
        state.po_registry.close()


# ============================================================================
# 4. EXTREME RAPID NAVIGATION & REPEATED LIFECYCLE STRESS TESTS
# ============================================================================


class TestExtremeNavigationStress:
    """Stress tests rapid keyboard/button clicking, resizing during walkthrough, and repeated restarts."""

    def test_100_rapid_back_and_forth_traversals(self, tk_root):
        """Execute 100 rapid forward and backward transitions across all 4 steps without leak or crash."""
        steps = build_tutorial_steps(None)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        overlay.start(0)
        try:
            for _ in range(100):
                overlay.next_step()  # 1
                overlay.next_step()  # 2
                overlay.next_step()  # 3
                overlay.prev_step()  # 2
                overlay.prev_step()  # 1
                overlay.prev_step()  # 0
                overlay.prev_step()  # clamped to 0
                assert overlay.current_step_index == 0
            tk_root.update_idletasks()
            tk_root.update()
        finally:
            overlay.destroy()

    def test_rapid_resize_configure_events_during_walkthrough(self, tk_root):
        """Simulate rapid <Configure> resize bursts on master window during active 4-step walkthrough."""
        steps = build_tutorial_steps(None)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        overlay.start(0)
        try:
            for w, h in [(800, 600), (1024, 768), (1400, 900), (900, 700), (1200, 800)]:
                tk_root.geometry(f"{w}x{h}")
                # Dispatch artificial Configure event
                event = tk.Event()
                event.widget = tk_root
                event.width = w
                event.height = h
                overlay._on_configure(event)

            tk_root.update_idletasks()
            # Wait for debounced timer to settle
            tk_root.after(100, lambda: None)
            tk_root.update()
            assert overlay.is_active is True
        finally:
            overlay.destroy()

    def test_50_repeated_start_and_destroy_cycles(self, tk_root):
        """Verify starting and destroying overlay 50 consecutive times leaves clean state."""
        steps = build_tutorial_steps(None)
        overlay = InteractiveTutorialOverlay(master_window=tk_root)
        overlay.register_steps(steps)

        for _ in range(50):
            overlay.start(0)
            assert overlay.is_active is True
            overlay.destroy()
            assert overlay.is_active is False
            assert overlay.canvas is None
            assert overlay.tooltip is None
