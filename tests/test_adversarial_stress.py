"""Adversarial stress test suite for UI responsiveness, extreme resizing, max length data entry, and button geometry."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
import pytest

from core.slip_printer_engine import create_record, FIELD_LABELS, list_layout_items
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.history_tab import HistoryTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel
from ui.main_window import SlipPrinterApp

RESIZE_SEQUENCE = [
    (1920, 1080, "FHD Desktop 1920x1080"),
    (1000, 700, "Minimum Supported 1000x700 (Step 1)"),
    (1366, 768, "Standard Laptop 1366x768"),
    (1000, 700, "Minimum Supported 1000x700 (Step 2)"),
]

STRESS_STRINGS = {
    "long_500": "A" * 500,
    "special_chars": r"!@#$%^&*()_+{}[]|:;\"'<>,.?/~`-=±§",
    "vietnamese": "Sản phẩm linh kiện điện tử kiểm tra độ bền nhiệt độ cao Ắ, Ộ, Ữ, Đ, ề, ố, ỹ",
    "unicode_cjk": "テスト部品名称データ_製品管理番号_品質保証基準_漢字カナ",
    "emojis": "🔥✨🎉🚀📦💾📋🧹🎯📐⚙️🕒📊",
    "xml_injection": "<script>alert('xss')</script><xml><tag attr='value'>data</tag>",
    "whitespace": "\t   SPACED DATA WITH TABS   \t",
}


def _check_no_zero_or_negative_geometry(widget, path: str = "") -> list[str]:
    violations = []
    current_path = f"{path}/{widget.winfo_name()}"
    if widget.winfo_ismapped():
        w = widget.winfo_width()
        h = widget.winfo_height()
        x = widget.winfo_x()
        y = widget.winfo_y()

        if w <= 0 or h <= 0:
            violations.append(f"Zero size at {current_path} ({widget.winfo_class()}): {w}x{h}")
        if x < 0 or y < 0:
            violations.append(f"Negative coordinates at {current_path} ({widget.winfo_class()}): ({x}, {y})")

    for child in widget.winfo_children():
        violations.extend(_check_no_zero_or_negative_geometry(child, current_path))
    return violations


def _get_action_buttons(data_tab: DataTabPanel) -> dict[str, ctk.CTkButton]:
    """Retrieve all 6 action and utility buttons from DataTabPanel."""
    left_panel = getattr(data_tab, "left_panel", data_tab.winfo_children()[0])
    form_frame = getattr(data_tab, "form_frame", left_panel.winfo_children()[0])
    
    # Button bars are children of form_frame containing CTkButton instances
    buttons = {}
    for child in form_frame.winfo_children():
        if isinstance(child, ctk.CTkFrame):
            for btn in child.winfo_children():
                if isinstance(btn, ctk.CTkButton):
                    text = btn.cget("text")
                    buttons[text] = btn
    return buttons


def test_extreme_resizing_sequence_isolated(tk_root):
    """Adversarially stress-test extreme resize cycling on DataTab and LayoutTab."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        layout_tab = LayoutTabPanel(notebook, controller)
        notebook.add(layout_tab, text="Layout")
        history_tab = HistoryTabPanel(notebook, controller)
        notebook.add(history_tab, text="History")

        state.records = [
            create_record(
                row_number=i,
                item_code=f"ITEM-{i:03d}",
                item_name=f"Standard Test Item {i}",
                carton_qty="10",
                total_qty="100",
                po=f"1100{i:04d}",
                po_detail="00010",
                po_sub="+001",
                box="10",
                rev="01",
                lot=" " * 10,
            )
            for i in range(1, 21)
        ]
        data_tab.set_records(select_index=0)
        layout_tab.refresh_tree()
        history_tab.refresh_history()

        # Run extreme resize sequence: 1920x1080 -> 1000x700 -> 1366x768 -> 1000x700
        for step_idx, (w, h, label) in enumerate(RESIZE_SEQUENCE):
            root.geometry(f"{w}x{h}+0+0")
            root.update_idletasks()
            root.update()

            # 1. Geometry check DataTab
            violations = _check_no_zero_or_negative_geometry(data_tab, f"Seq_{step_idx}_{label}")
            assert not violations, f"Step {step_idx} ({label}) DataTab violations: {violations}"

            # 2. Ratio verification (68/32)
            left_p = getattr(data_tab, "left_panel", data_tab.winfo_children()[0])
            right_p = getattr(data_tab, "preview_frame", data_tab.winfo_children()[1])
            left_w = left_p.winfo_width()
            right_w = right_p.winfo_width()
            total_w = left_w + right_w
            assert total_w > 0, f"Step {step_idx} ({label}) DataTab total width is 0"
            ratio = left_w / total_w
            assert 0.60 <= ratio <= 0.75, f"Step {step_idx} ({label}) ratio {ratio:.3f} outside [0.60, 0.75]"

            # 3. Geometry check LayoutTab
            notebook.select(1)
            root.update_idletasks()
            root.update()
            layout_violations = _check_no_zero_or_negative_geometry(layout_tab, f"Seq_{step_idx}_{label}")
            assert not layout_violations, f"Step {step_idx} ({label}) LayoutTab violations: {layout_violations}"

            # 4. Geometry check HistoryTab
            notebook.select(2)
            root.update_idletasks()
            root.update()
            history_violations = _check_no_zero_or_negative_geometry(history_tab, f"Seq_{step_idx}_{label}")
            assert not history_violations, f"Step {step_idx} ({label}) HistoryTab violations: {history_violations}"

            # Return to DataTab
            notebook.select(0)
            root.update_idletasks()
            root.update()
    finally:
        state.po_registry.close()


def test_extreme_resizing_sequence_full_app(tk_root):
    """Adversarially stress-test extreme resize cycling on full application layout."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)

    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(0, weight=1)
    splitter = ttk.Panedwindow(root, orient="horizontal")
    splitter.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

    sidebar_host = ctk.CTkFrame(splitter, corner_radius=14, fg_color=("gray94", "gray14"))
    sidebar_host.grid_rowconfigure(0, weight=1)
    sidebar_host.grid_columnconfigure(0, weight=1)
    sidebar = SidebarPanel(sidebar_host, controller)
    sidebar.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    splitter.add(sidebar_host, weight=0)

    main_host = ctk.CTkFrame(splitter, corner_radius=14, fg_color=("gray94", "gray14"))
    main_host.grid_rowconfigure(0, weight=1)
    main_host.grid_columnconfigure(0, weight=1)
    notebook = ttk.Notebook(main_host)
    notebook.grid(row=0, column=0, sticky="nsew", padx=14, pady=14)
    data_tab = DataTabPanel(notebook, controller)
    layout_tab = LayoutTabPanel(notebook, controller)
    history_tab = HistoryTabPanel(notebook, controller)
    notebook.add(data_tab, text="Dữ liệu")
    notebook.add(layout_tab, text="Cấu hình tem")
    notebook.add(history_tab, text="Lịch sử in")
    splitter.add(main_host, weight=1)

    sidebar_width = 360

    def apply_splitter_width():
        try:
            splitter.sashpos(0, sidebar_width)
        except Exception:
            pass

    try:
        state.records = [
            create_record(
                row_number=i,
                item_code=f"ITEM-{i:03d}",
                item_name=f"Stress Item {i}",
                carton_qty="5",
                total_qty="50",
                po=f"1100{i:04d}",
                po_detail="00010",
                po_sub="+001",
                box="10",
                rev="01",
                lot=" " * 10,
            )
            for i in range(1, 15)
        ]
        data_tab.set_records(select_index=0)

        for step_idx, (w, h, label) in enumerate(RESIZE_SEQUENCE):
            root.geometry(f"{w}x{h}+0+0")
            root.update_idletasks()
            root.update()
            apply_splitter_width()
            root.update_idletasks()
            root.update()

            violations = _check_no_zero_or_negative_geometry(root, f"FullApp_{step_idx}_{label}")
            assert not violations, f"Step {step_idx} ({label}) FullApp violations: {violations}"

            # Ensure sidebar does not collapse
            sidebar_w = sidebar.winfo_width()
            assert sidebar_w >= 200, f"Step {step_idx} ({label}) Sidebar width {sidebar_w} < 200px"

            # Check buttons in DataTab
            buttons = _get_action_buttons(data_tab)
            assert len(buttons) >= 5, f"Step {step_idx} ({label}) Expected 5 action buttons, found {len(buttons)}"
            for text, btn in buttons.items():
                bw = btn.winfo_width()
                assert bw >= 70, f"Step {step_idx} ({label}) Button '{text}' width {bw}px < 70px"
    finally:
        state.po_registry.close()


def test_data_entry_max_length_and_special_characters(tk_root):
    """Adversarially inject oversized strings and special characters into form inputs."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root.geometry("1000x700+0+0")
        root.update_idletasks()
        root.update()

        # Inject various extreme inputs
        for stress_key, stress_val in STRESS_STRINGS.items():
            state.item_code_var.set(f"CODE_{stress_val[:100]}")
            state.item_name_var.set(f"NAME_{stress_val}")
            state.carton_qty_var.set("99999")
            state.total_qty_var.set("9999900")
            state.box_var.set("100")
            state.rev_var.set("99")
            state.po_var.set(f"PO_{stress_val[:30]}")
            state.po_detail_var.set("00010")
            state.po_sub_var.set("+001")
            state.lot_var.set(stress_val[:50])

            root.update_idletasks()
            root.update()

            # Verify no geometry corruption
            violations = _check_no_zero_or_negative_geometry(data_tab, f"Stress_{stress_key}")
            assert not violations, f"Oversized input [{stress_key}] caused geometry violations: {violations}"

            # Verify button widths remain intact
            buttons = _get_action_buttons(data_tab)
            for text, btn in buttons.items():
                bw = btn.winfo_width()
                assert bw >= 70, f"Oversized input [{stress_key}] corrupted button '{text}' width to {bw}px (< 70px)"

        # Also inject stress records directly into Treeview and state
        stress_records = [
            create_record(
                row_number=1,
                item_code="C" * 100,
                item_name=STRESS_STRINGS["vietnamese"] + " " + STRESS_STRINGS["unicode_cjk"],
                carton_qty="99999",
                total_qty="9999900",
                po="11009999",
                po_detail="00010",
                po_sub="+001",
                box="100",
                rev="99",
                lot=STRESS_STRINGS["special_chars"][:10],
            ),
            create_record(
                row_number=2,
                item_code="XSS_TEST",
                item_name=STRESS_STRINGS["xml_injection"],
                carton_qty="1",
                total_qty="10",
                po="11000001",
                po_detail="00010",
                po_sub="+001",
                box="10",
                rev="01",
                lot=" " * 10,
            ),
        ]
        state.records = stress_records
        data_tab.set_records(select_index=0)
        root.update_idletasks()
        root.update()

        # Select row 0 and row 1
        data_tab._select_tree_row(0)
        root.update_idletasks()
        root.update()
        assert state.item_code_var.get() == "C" * 100

        data_tab._select_tree_row(1)
        root.update_idletasks()
        root.update()
        assert state.item_name_var.get() == STRESS_STRINGS["xml_injection"]

        violations = _check_no_zero_or_negative_geometry(data_tab, "StressRecords_Selected")
        assert not violations, f"Stress records caused geometry violations: {violations}"
    finally:
        state.po_registry.close()


def test_action_buttons_at_1000x700_minimum(tk_root):
    """Verify all 6 buttons (3 primary, 3 utility) remain clickable and width >= 70px at 1000x700."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root.geometry("1000x700+0+0")
        root.update_idletasks()
        root.update()

        buttons = _get_action_buttons(data_tab)
        expected_buttons = [
            "➕ Thêm mới",
            "💾 Cập nhật dòng",
            "🗑️ Xóa dòng",
            "📋 Điền mẫu",
            "🧹 Xóa form",
        ]

        found_names = list(buttons.keys())
        for exp in expected_buttons:
            assert exp in found_names, f"Expected button '{exp}' not found in DataTab. Found: {found_names}"

        for name, btn in buttons.items():
            bw = btn.winfo_width()
            bh = btn.winfo_height()
            state_val = btn.cget("state")
            assert bw >= 70, f"Button '{name}' width is {bw}px, expected >= 70px at 1000x700"
            assert bh >= 24, f"Button '{name}' height is {bh}px, expected >= 24px"
            assert state_val == "normal", f"Button '{name}' state is '{state_val}', expected 'normal'"

        # Test utility button actions directly
        # 1. Fill sample data
        controller.fill_sample_data()
        assert state.item_code_var.get() == "3V2ND00160"
        assert state.carton_qty_var.get() == "20"
        assert state.box_var.get() == "001/003"
        assert state.total_qty_var.get() == "60"

        # 2. Clear form must wipe every field, including Rev
        data_tab.clear_form()
        assert state.item_code_var.get() == ""
        assert state.item_name_var.get() == ""
        assert state.carton_qty_var.get() == ""
        assert state.total_qty_var.get() == ""
        assert state.po_var.get() == ""
        assert state.po_detail_var.get() == ""
        assert state.po_sub_var.get() == ""
        assert state.box_var.get() == ""
        assert state.rev_var.get() == ""
        assert state.lot_var.get() == ""
        assert state.form_mode_var.get() == "Đang tạo dòng mới"
    finally:
        state.po_registry.close()
