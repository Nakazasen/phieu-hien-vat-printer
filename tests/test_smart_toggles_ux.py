import json
import pytest
import customtkinter as ctk

from ui.app_state import AppState
from ui.app_controller import AppController
from ui.components.layout_tab import LayoutTabPanel
from ui.components.data_tab import DataTabPanel


def test_smart_toggles_rendered_and_synced(tk_root, monkeypatch):
    monkeypatch.setattr('tkinter.messagebox.showinfo', lambda *args, **kwargs: True)
    monkeypatch.setattr('tkinter.messagebox.showwarning', lambda *args, **kwargs: True)
    monkeypatch.setattr('tkinter.messagebox.showerror', lambda *args, **kwargs: True)

    root = tk_root
    state = AppState(root)
    controller = AppController(state)

    layout_tab = LayoutTabPanel(root, controller)
    data_tab = DataTabPanel(root, controller)

    # 1. Verify Layout Tab components
    assert hasattr(layout_tab, 'options_card')
    assert hasattr(layout_tab, 'sw_hide_total')
    assert hasattr(layout_tab, 'sw_hide_package')
    assert hasattr(layout_tab, 'lbl_total_status')
    assert hasattr(layout_tab, 'lbl_pkg_status')

    # Initial state badges
    assert layout_tab.lbl_total_status.cget('text') == '[Chỉ in 20]'
    assert layout_tab.lbl_pkg_status.cget('text') == '[Ô trống]'

    # 2. Verify Data Tab quick switch components
    assert hasattr(data_tab, 'sw_quick_hide_total')
    assert hasattr(data_tab, 'sw_quick_hide_pkg')

    # Both tabs share the same BooleanVars
    assert data_tab.sw_quick_hide_total.cget('variable') is controller.app_state.opt_hide_total_qty_var
    assert layout_tab.sw_hide_total.cget('variable') is controller.app_state.opt_hide_total_qty_var

    # 3. Test toggling hide_total_qty
    controller.app_state.opt_hide_total_qty_var.set(False)
    layout_tab.sync_option_ui()
    assert layout_tab.lbl_total_status.cget('text') == '[In 20 / 60]'

    # 4. Test toggling hide_package_qty
    controller.app_state.opt_hide_package_qty_var.set(False)
    layout_tab.sync_option_ui()
    assert layout_tab.lbl_pkg_status.cget('text') == '[In 001/003]'

    # 5. Test switch toggle callback
    layout_tab._on_switch_toggle()
    assert controller.app_state.layout_config['options']['hide_total_qty_on_slip'] is False
    assert controller.app_state.layout_config['options']['hide_package_qty_box'] is False

    # 6. Test reset layout config
    controller.reset_layout_config()
    assert controller.app_state.opt_hide_total_qty_var.get() is True
    assert controller.app_state.opt_hide_package_qty_var.get() is True
