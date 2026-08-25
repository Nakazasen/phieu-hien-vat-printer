"""Tests for the consolidated QR Scan tab (QRScanTabPanel) and embedded QRScanPanel."""
from __future__ import annotations

import customtkinter as ctk
import pytest
from tkinter import ttk

from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.qr_scan_dialog import QRScanPanel
from ui.components.qr_scan_tab import QRScanTabPanel


SAMPLE_QR_129 = (
    "112602110100010+001    0000006000003W2ND25350 01            000000600000"
    "                          "
    "                        "
    "001/003"
)


class FakeView:
    """Minimal view double satisfying QRScanPanel controller.view interactions."""

    def __init__(self, root: ctk.CTkBaseClass, state: AppState):
        self.notebook = ttk.Notebook(root)
        self.logs: list[str] = []
        self.app_state = state

    def append_log(self, message: str) -> None:
        self.logs.append(message)

    def set_records(self, records, select_index=None, source: str | None = None) -> None:
        self.app_state.records = list(records)


@pytest.fixture
def qr_env(tk_root):
    """Build an isolated state/controller + embedded QR tab with a fake view."""
    state = AppState(tk_root)
    controller = AppController(state)
    view = FakeView(tk_root, state)
    controller.set_view(view)
    tab = QRScanTabPanel(tk_root, controller)
    yield tk_root, state, controller, view, tab
    try:
        tab.destroy()
    except Exception:
        pass
    state.po_registry.close()


def test_qr_tab_embeds_panel_in_embedded_mode(qr_env):
    _root, _state, _controller, _view, tab = qr_env
    assert isinstance(tab.scan_panel, QRScanPanel)
    assert tab.scan_panel.embedded is True
    assert tab.get_scan_panel_widget() is tab.scan_panel


def test_qr_tab_scan_decode_and_add_records(qr_env):
    _root, state, _controller, view, tab = qr_env
    panel = tab.scan_panel

    panel.scan_input_var.set(SAMPLE_QR_129)
    panel.process_scanned_code()

    assert panel.mode_var.get() == QRScanPanel.MODE_SPLIT
    assert panel.item_code_var.get() == "3W2ND25350"
    assert panel.po_var.get() == "1126021101"
    assert panel.po_detail_var.get() == "10010"

    panel.item_name_var.set("COVER REAR")
    panel.confirm_and_add_records()

    assert len(state.records) == 1
    assert state.records[0].qr_payload.startswith("112602110110010+001")
    assert any("nghiệp vụ Phân tách" in log for log in view.logs)


def test_qr_tab_apply_to_main_form_switches_to_data_tab_without_destroy(qr_env):
    root, state, _controller, view, tab = qr_env
    panel = tab.scan_panel

    data_holder = ctk.CTkFrame(view.notebook)
    view.notebook.add(data_holder, text="Dữ liệu và xem trước")
    view.notebook.add(tab, text="📷 Quét QR")
    view.notebook.select(1)

    panel.scan_input_var.set(SAMPLE_QR_129)
    panel.process_scanned_code()
    panel.item_name_var.set("SPLIT PART")
    panel.apply_to_main_form()

    assert state.item_code_var.get() == "3W2ND25350"
    assert state.po_detail_var.get() == "10010"
    # Embedded mode must NOT destroy the tab and must switch back to the data tab
    assert tab.winfo_exists()
    assert view.notebook.index(view.notebook.select()) == 0


def test_qr_tab_close_button_absent_when_embedded(qr_env):
    _root, _state, _controller, _view, tab = qr_env
    # The dialog-only 'Đóng' button must not exist in embedded mode
    assert not hasattr(tab.scan_panel, "close_btn")


def test_main_window_qr_tab_next_to_history_tab():
    """The QR tab must be registered right after the EDI history tab in SlipPrinterApp."""
    from ui.main_window import SlipPrinterApp

    source = __import__("inspect").getsource(SlipPrinterApp._build_content)
    history_pos = source.find('text="📊 Lịch sử Đăng ký EDI"')
    qr_pos = source.find('text="📷 Quét QR"')
    assert history_pos != -1, "History tab missing in _build_content"
    assert qr_pos != -1, "QR tab missing in _build_content"
    assert qr_pos > history_pos, "QR tab must be added after the history tab"


def test_qr_tab_focus_scan_entry(qr_env):
    root, _state, _controller, _view, tab = qr_env
    root.update_idletasks()
    tab.focus_scan_entry()
    assert tab.scan_panel.scan_entry is not None
