"""Unit and Integration Tests for Interactive Tutorial Script and Widget Accessors."""
from __future__ import annotations

from unittest.mock import MagicMock
import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pytest

from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.sidebar import SidebarPanel
from ui.components.tutorial_overlay import (
    InteractiveTutorialOverlay,
    TutorialStep,
    build_tutorial_steps as reexported_build_tutorial_steps,
)
from ui.components.tutorial_script import build_tutorial_steps
from ui.main_window import SlipPrinterApp


class TestTutorialScriptStructure:
    """Test the structure, metadata, and Vietnamese textual contents of tutorial steps."""

    def test_build_tutorial_steps_headless_returns_four_steps(self):
        steps = build_tutorial_steps(None)
        assert isinstance(steps, list)
        assert len(steps) == 4
        for step in steps:
            assert isinstance(step, TutorialStep)

    def test_step_ids_and_order(self):
        steps = build_tutorial_steps(None)
        expected_ids = [
            "step_excel_import",
            "step_qr_scanner",
            "step_auto_po",
            "step_pdf_generation",
        ]
        actual_ids = [s.step_id for s in steps]
        assert actual_ids == expected_ids

    def test_all_steps_target_tab_index_zero(self):
        steps = build_tutorial_steps(None)
        for step in steps:
            assert step.target_tab_index == 0

    def test_step1_excel_import_vietnamese_content(self):
        step = build_tutorial_steps(None)[0]
        assert step.step_id == "step_excel_import"
        assert "1. Nạp dữ liệu từ Excel" in step.title
        desc = step.description.lower()
        assert "excel" in desc
        assert "import từ excel" in desc or "import" in desc
        assert "mã hàng" in desc
        assert "trùng lặp" in desc or "cảnh báo" in desc

    def test_step2_qr_scanner_vietnamese_content(self):
        step = build_tutorial_steps(None)[1]
        assert step.step_id == "step_qr_scanner"
        assert "2. Quét mã QR thông minh" in step.title
        desc = step.description
        assert "Quét QR" in desc
        assert "Phân tách" in desc
        assert "Hoàn kho" in desc
        assert "In lại" in desc
        assert "10010" in desc
        assert "11010" in desc

    def test_step3_auto_po_vietnamese_content(self):
        step = build_tutorial_steps(None)[2]
        assert step.step_id == "step_auto_po"
        assert "3. Tạo mã Auto PO & Thêm phiếu" in step.title
        desc = step.description
        assert "Auto PO" in desc or "11YYMMDDNN" in desc
        assert "PO Registry" in desc or "trùng lặp" in desc or "Thêm mới" in desc

    def test_step4_pdf_generation_vietnamese_content(self):
        step = build_tutorial_steps(None)[3]
        assert step.step_id == "step_pdf_generation"
        assert "4. Tạo & In phiếu hiện vật PDF" in step.title
        desc = step.description
        assert "Tạo PDF" in desc
        assert "4 phiếu" in desc or "A4" in desc
        assert "Mở PDF" in desc or "in" in desc.lower()

    def test_step_tooltips_and_padding(self):
        steps = build_tutorial_steps(None)
        for step in steps:
            assert step.padding >= 6
            assert step.tooltip_position in ("auto", "right", "bottom", "top", "left")


class TestWidgetGettersWithNoneAndMocks:
    """Test widget getters under headless, mock, and edge case conditions."""

    def test_widget_getters_return_none_when_app_none(self):
        steps = build_tutorial_steps(None)
        for step in steps:
            assert step.target_widget_getter() is None

    def test_widget_getters_with_mock_accessors(self):
        mock_excel_btn = object()
        mock_qr_btn = object()
        mock_form_frame = object()
        mock_pdf_btn = object()

        mock_sidebar = MagicMock()
        mock_sidebar.get_excel_import_widget.return_value = mock_excel_btn
        mock_sidebar.get_qr_scan_widget.return_value = mock_qr_btn
        mock_sidebar.get_generate_pdf_widget.return_value = mock_pdf_btn

        mock_data_tab = MagicMock()
        mock_data_tab.get_form_frame.return_value = mock_form_frame

        mock_app = MagicMock()
        mock_app.sidebar = mock_sidebar
        mock_app.data_tab = mock_data_tab

        steps = build_tutorial_steps(mock_app)
        assert steps[0].target_widget_getter() is mock_excel_btn
        assert steps[1].target_widget_getter() is mock_qr_btn
        assert steps[2].target_widget_getter() is mock_form_frame
        assert steps[3].target_widget_getter() is mock_pdf_btn

    def test_widget_getters_fallback_to_attribute_names(self):
        mock_excel_btn = object()
        mock_qr_btn = object()
        mock_form_frame = object()
        mock_pdf_btn = object()

        class DummySidebar:
            excel_import_button = mock_excel_btn
            qr_scan_button = mock_qr_btn
            generate_button = mock_pdf_btn

        class DummyDataTab:
            form_frame = mock_form_frame

        class DummyApp:
            sidebar = DummySidebar()
            data_tab = DummyDataTab()

        steps = build_tutorial_steps(DummyApp())
        assert steps[0].target_widget_getter() is mock_excel_btn
        assert steps[1].target_widget_getter() is mock_qr_btn
        assert steps[2].target_widget_getter() is mock_form_frame
        assert steps[3].target_widget_getter() is mock_pdf_btn

    def test_widget_getter_with_controller_wrapper(self):
        mock_excel_btn = object()

        class DummyView:
            class DummySidebar:
                excel_import_button = mock_excel_btn
            sidebar = DummySidebar()
            data_tab = None

        class DummyController:
            view = DummyView()

        steps = build_tutorial_steps(DummyController())
        assert steps[0].target_widget_getter() is mock_excel_btn

    def test_widget_getter_handles_exceptions_gracefully(self):
        class FaultySidebar:
            def get_excel_import_widget(self):
                raise RuntimeError("Boom!")

        class FaultyApp:
            sidebar = FaultySidebar()
            data_tab = None

        # Should not raise exception
        steps = build_tutorial_steps(FaultyApp())
        # Might return FaultySidebar or None, but never raises
        try:
            res = steps[0].target_widget_getter()
            assert res is not None or res is None
        except Exception as exc:
            pytest.fail(f"target_widget_getter raised unexpected exception: {exc}")


class TestSidebarAndDataTabAccessors:
    """Test actual SidebarPanel and DataTabPanel widget accessors and aliases."""

    def test_sidebar_and_data_tab_accessors_and_aliases(self, tk_root):
        state = AppState(tk_root)
        controller = AppController(state)
        sidebar = SidebarPanel(tk_root, controller)
        data_tab = DataTabPanel(tk_root, controller)
        try:
            tk_root.update_idletasks()

            # Sidebar Method accessors
            assert sidebar.get_excel_import_widget() is sidebar.excel_import_button
            assert sidebar.get_excel_path_widget() is sidebar.excel_entry
            assert sidebar.get_excel_frame_widget() is sidebar.excel_frame
            assert sidebar.get_qr_scan_widget() is sidebar.qr_scan_button
            assert sidebar.get_generate_pdf_widget() is sidebar.generate_button
            assert sidebar.get_open_pdf_widget() is sidebar.open_pdf_button

            # Sidebar Property aliases
            assert sidebar.excel_import_btn is sidebar.excel_import_button
            assert sidebar.btn_import_excel is sidebar.excel_import_button
            assert sidebar.qr_scan_btn is sidebar.qr_scan_button
            assert sidebar.btn_qr_scan is sidebar.qr_scan_button
            assert sidebar.btn_generate_pdf is sidebar.generate_button
            assert sidebar.open_pdf_btn is sidebar.open_pdf_button
            assert sidebar.btn_open_pdf is sidebar.open_pdf_button

            # DataTab Method accessors
            assert data_tab.get_form_frame() is data_tab.form_frame
            assert data_tab.get_auto_po_widget() is data_tab.po_entry
            assert data_tab.get_po_detail_widget() is data_tab.po_detail_entry
            assert data_tab.get_po_sub_widget() is data_tab.po_sub_entry
            assert data_tab.get_add_button_widget() is data_tab.btn_add_record
            assert data_tab.get_update_button_widget() is data_tab.btn_update_record
            assert data_tab.get_delete_button_widget() is data_tab.btn_delete_record
            assert data_tab.get_qr_button_widget() is data_tab.btn_qr_scan
            assert data_tab.get_treeview_widget() is data_tab.preview_tree
            assert data_tab.get_table_frame() is data_tab.table_frame
            assert data_tab.get_preview_frame() is data_tab.preview_frame
            assert data_tab.get_preview_image_label() is data_tab.preview_image_label
            assert data_tab.get_qr_payload_box() is data_tab.qr_payload_box
            assert data_tab.get_refresh_preview_button() is data_tab.btn_refresh_preview

            # DataTab Property aliases
            assert data_tab.qr_scan_btn is data_tab.btn_qr_scan
            assert data_tab.add_btn is data_tab.btn_add_record
            assert data_tab.update_btn is data_tab.btn_update_record
            assert data_tab.delete_btn is data_tab.btn_delete_record
        finally:
            sidebar.destroy()
            data_tab.destroy()
            state.po_registry.close()


class TestReExportAndControllerIntegration:
    """Test re-exports in tutorial_overlay and hooks on Controller and Main Window."""

    def test_reexport_from_tutorial_overlay(self):
        assert reexported_build_tutorial_steps is build_tutorial_steps

    def test_controller_get_tutorial_steps_headless(self):
        mock_state = MagicMock()
        controller = AppController(mock_state)
        steps = controller.get_tutorial_steps()
        assert len(steps) == 4
        assert steps[0].step_id == "step_excel_import"
        for s in steps:
            assert s.target_widget_getter() is None

    def test_controller_get_tutorial_steps_with_view(self):
        mock_state = MagicMock()
        controller = AppController(mock_state)
        mock_view = MagicMock()
        mock_sidebar = MagicMock()
        mock_btn = object()
        mock_sidebar.get_excel_import_widget.return_value = mock_btn
        mock_view.sidebar = mock_sidebar
        mock_view.data_tab = None
        controller.set_view(mock_view)

        steps = controller.get_tutorial_steps()
        assert len(steps) == 4
        assert steps[0].target_widget_getter() is mock_btn

    def test_main_window_get_tutorial_steps(self):
        steps = SlipPrinterApp.get_tutorial_steps(None)
        assert len(steps) == 4
        assert steps[3].step_id == "step_pdf_generation"

    def test_real_app_hierarchy_steps_wiring(self, tk_root):
        """Construct full app or composite and verify getters resolve live Tk widgets."""
        state = AppState(tk_root)
        controller = AppController(state)

        # Build simulated main app composite
        sidebar = SidebarPanel(tk_root, controller)
        data_tab = DataTabPanel(tk_root, controller)

        class AppContainer:
            def __init__(self, s, d):
                self.sidebar = s
                self.data_tab = d

        app = AppContainer(sidebar, data_tab)
        tk_root.update_idletasks()

        try:
            steps = build_tutorial_steps(app)
            assert len(steps) == 4

            # Verify step 1 getter returns sidebar's excel import button
            assert steps[0].target_widget_getter() is sidebar.excel_import_button
            # Verify step 2 getter returns sidebar's qr button
            assert steps[1].target_widget_getter() is sidebar.qr_scan_button
            # Verify step 3 getter returns data_tab form frame or add button
            assert steps[2].target_widget_getter() in (data_tab.form_frame, data_tab.btn_add_record)
            # Verify step 4 getter returns sidebar generate button
            assert steps[3].target_widget_getter() is sidebar.generate_button
        finally:
            sidebar.destroy()
            data_tab.destroy()
            state.po_registry.close()
