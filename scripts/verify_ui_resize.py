"""Standalone verification script for UI responsiveness across multiple screen resolutions."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from tkinter import ttk
import customtkinter as ctk

from core.slip_printer_engine import create_record
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.main_window import SlipPrinterApp

RESOLUTIONS = [
    (1000, 700, "1000x700 (Minimum Supported)"),
    (1366, 768, "1366x768 (Standard Laptop)"),
    (1920, 1080, "1920x1080 (FHD Desktop)"),
]


def generate_sample_records(count: int = 15):
    return [
        create_record(
            row_number=i,
            item_code=f"ITEM-{i:04d}",
            item_name=f"Sample Product Item {i}",
            carton_qty="20",
            total_qty="200",
            po=f"11000{i:03d}",
            po_detail="00010",
            po_sub="+001",
            box="10",
            rev="01",
            lot=" " * 10,
        )
        for i in range(1, count + 1)
    ]


def verify_widget_bounds(widget, errors: list[str], path: str = "") -> None:
    """Check that mapped widgets do not have 0 size or negative coordinates."""
    current_path = f"{path}/{widget.winfo_name()}"
    if widget.winfo_ismapped():
        w = widget.winfo_width()
        h = widget.winfo_height()
        x = widget.winfo_x()
        y = widget.winfo_y()

        if w <= 0 or h <= 0:
            errors.append(f"Zero size widget at {current_path} ({widget.winfo_class()}): {w}x{h}")
        if x < 0 or y < 0:
            errors.append(f"Negative coordinates at {current_path} ({widget.winfo_class()}): ({x}, {y})")

    for child in widget.winfo_children():
        verify_widget_bounds(child, errors, current_path)


def run_all_verifications() -> list[str]:
    errors: list[str] = []

    # 1. Verify DataTab across resolutions using a single CTk root
    print("\n--- Verifying DataTab across resolutions ---")
    root_data = ctk.CTk()
    try:
        state = AppState(root_data)
        controller = AppController(state)
        notebook = ttk.Notebook(root_data)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data Tab")
        state.records = generate_sample_records(15)
        data_tab.set_records(select_index=0)

        for width, height, label in RESOLUTIONS:
            root_data.geometry(f"{width}x{height}+0+0")
            root_data.update_idletasks()
            root_data.update()

            res_errors = []
            verify_widget_bounds(data_tab, res_errors, "DataTab")

            left_panel = data_tab.winfo_children()[0]
            preview_frame = data_tab.winfo_children()[1]
            left_w = left_panel.winfo_width()
            right_w = preview_frame.winfo_width()
            total_w = left_w + right_w

            if total_w > 0:
                left_ratio = left_w / total_w
                if not (0.60 <= left_ratio <= 0.75):
                    res_errors.append(f"[{label}] DataTab 68/32 ratio out of bounds: left={left_w} ({left_ratio:.2%}), right={right_w}")
            else:
                res_errors.append(f"[{label}] DataTab total width is 0")

            form_frame = left_panel.winfo_children()[0]
            btn_bars = [c for c in form_frame.winfo_children() if isinstance(c, ctk.CTkFrame) and len(c.winfo_children()) == 3]
            for bar_idx, bar in enumerate(btn_bars):
                for btn_idx, btn in enumerate(bar.winfo_children()):
                    if isinstance(btn, ctk.CTkButton):
                        btn_w = btn.winfo_width()
                        if btn_w < 70:
                            res_errors.append(f"[{label}] Button (bar {bar_idx}, btn {btn_idx}: '{btn.cget('text')}') width {btn_w}px < 70px")

            table_frame = left_panel.winfo_children()[1]
            table_h = table_frame.winfo_height()
            if table_h < 80:
                res_errors.append(f"[{label}] Table height {table_h}px < 80px")

            if right_w < 150:
                res_errors.append(f"[{label}] Preview width {right_w}px < 150px")

            if res_errors:
                print(f"  [FAIL] {label}: {len(res_errors)} error(s)")
                for err in res_errors:
                    print(f"     - {err}")
                errors.extend(res_errors)
            else:
                print(f"  [PASS] {label}: OK (left={left_w}px, right={right_w}px, table_h={table_h}px)")
    finally:
        root_data.destroy()

    # 2. Verify LayoutTab across resolutions
    print("\n--- Verifying LayoutTab across resolutions ---")
    root_layout = ctk.CTk()
    try:
        state = AppState(root_layout)
        controller = AppController(state)
        notebook = ttk.Notebook(root_layout)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        layout_tab = LayoutTabPanel(notebook, controller)
        notebook.add(layout_tab, text="Layout Tab")
        layout_tab.refresh_tree()

        for width, height, label in RESOLUTIONS:
            root_layout.geometry(f"{width}x{height}+0+0")
            root_layout.update_idletasks()
            root_layout.update()

            res_errors = []
            verify_widget_bounds(layout_tab, res_errors, "LayoutTab")

            list_frame = layout_tab.winfo_children()[0]
            editor = layout_tab.winfo_children()[1]

            if list_frame.winfo_width() < 150:
                res_errors.append(f"[{label}] LayoutTab list_frame width {list_frame.winfo_width()}px < 150px")
            if editor.winfo_width() < 200:
                res_errors.append(f"[{label}] LayoutTab editor width {editor.winfo_width()}px < 200px")
            if len(layout_tab.layout_tree.get_children()) == 0:
                res_errors.append(f"[{label}] LayoutTab tree has 0 items")

            if res_errors:
                print(f"  [FAIL] {label}: {len(res_errors)} error(s)")
                for err in res_errors:
                    print(f"     - {err}")
                errors.extend(res_errors)
            else:
                print(f"  [PASS] {label}: OK (list_frame={list_frame.winfo_width()}px, editor={editor.winfo_width()}px)")
    finally:
        root_layout.destroy()

    # 3. Verify Full Application Window
    print("\n--- Verifying Full Application Window across resolutions ---")
    app = SlipPrinterApp()
    try:
        for width, height, label in RESOLUTIONS:
            app.geometry(f"{width}x{height}+0+0")
            app.update_idletasks()
            app.update()

            res_errors = []
            verify_widget_bounds(app, res_errors, "App")

            if app.sidebar.winfo_width() < 200:
                res_errors.append(f"[{label}] App sidebar width {app.sidebar.winfo_width()}px < 200px")

            data_tab = app.data_tab
            left_panel = data_tab.winfo_children()[0]
            preview_frame = data_tab.winfo_children()[1]
            table_frame = left_panel.winfo_children()[1]

            if table_frame.winfo_height() < 80:
                res_errors.append(f"[{label}] App table height {table_frame.winfo_height()}px < 80px")
            if preview_frame.winfo_width() < 150:
                res_errors.append(f"[{label}] App preview width {preview_frame.winfo_width()}px < 150px")

            if res_errors:
                print(f"  [FAIL] {label}: {len(res_errors)} error(s)")
                for err in res_errors:
                    print(f"     - {err}")
                errors.extend(res_errors)
            else:
                print(f"  [PASS] {label}: OK (sidebar={app.sidebar.winfo_width()}px, table_h={table_frame.winfo_height()}px, preview_w={preview_frame.winfo_width()}px)")
    finally:
        app.destroy()

    return errors


def main() -> int:
    print("=" * 70)
    print("UI RESPONSIVENESS & RESIZE VERIFICATION HARNESS")
    print("=" * 70)

    errors = run_all_verifications()

    print("\n" + "=" * 70)
    if errors:
        print(f"FAILED: {len(errors)} issue(s) detected during UI verification.")
        return 1
    else:
        print("ALL UI RESPONSIVENESS VERIFICATIONS PASSED (0 errors).")
        return 0


if __name__ == "__main__":
    sys.exit(main())
