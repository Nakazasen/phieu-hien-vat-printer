"""Standalone empirical adversarial stress-test runner."""

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
from ui.components.history_tab import HistoryTabPanel
from ui.main_window import SlipPrinterApp

RESIZE_SEQUENCE = [
    (1920, 1080, "FHD Desktop 1920x1080"),
    (1000, 700, "Minimum Supported 1000x700 (Step 1)"),
    (1366, 768, "Standard Laptop 1366x768"),
    (1000, 700, "Minimum Supported 1000x700 (Step 2)"),
]

STRESS_STRINGS = {
    "500_chars": "A" * 500,
    "special_chars": r"!@#$%^&*()_+{}[]|:;\"'<>,.?/~`-=±§",
    "vietnamese": "Sản phẩm linh kiện điện tử kiểm tra độ bền nhiệt độ cao Ắ, Ộ, Ữ, Đ, ề, ố, ỹ",
    "unicode_cjk": "テスト部品名称データ_製品管理番号_品質保証基準_漢字カナ",
    "emojis": "🔥✨🎉🚀📦💾📋🧹🎯📐⚙️🕒📊",
    "xml_tags": "<script>alert('xss')</script><xml><tag attr='value'>data</tag>",
}


def _check_bounds(widget, errors: list[str], path: str = "") -> None:
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
        _check_bounds(child, errors, current_path)


def run_adversarial_tests() -> int:
    print("=" * 80)
    print("EMPIRICAL ADVERSARIAL STRESS TEST SUITE")
    print("=" * 80)
    total_errors: list[str] = []

    # 1. Extreme Resizing Sequence
    print("\n>>> Phase 1: Extreme Resizing Sequence (1920x1080 -> 1000x700 -> 1366x768 -> 1000x700)")
    app = SlipPrinterApp()
    try:
        app.app_state.records = [
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
            for i in range(1, 11)
        ]
        app.data_tab.set_records(select_index=0)

        for step_idx, (w, h, label) in enumerate(RESIZE_SEQUENCE, 1):
            app.geometry(f"{w}x{h}+0+0")
            app.update_idletasks()
            app.update()
            app._apply_splitter_width()
            app.update_idletasks()
            app.update()

            step_errors = []
            _check_bounds(app, step_errors, f"Step{step_idx}")

            data_tab = app.data_tab
            left_p = data_tab.winfo_children()[0]
            right_p = data_tab.winfo_children()[1]
            left_w = left_p.winfo_width()
            right_w = right_p.winfo_width()
            total_w = left_w + right_w
            ratio = (left_w / total_w) if total_w > 0 else 0.0

            sidebar_w = app.sidebar.winfo_width()
            table_h = left_p.winfo_children()[1].winfo_height()

            print(f"  [Step {step_idx}] {label}:")
            print(f"    - Window: {app.winfo_width()}x{app.winfo_height()} | Sidebar: {sidebar_w}px")
            print(f"    - DataTab Left Panel: {left_w}px ({ratio:.1%}) | Right Preview: {right_w}px")
            print(f"    - Table Height: {table_h}px")

            if not (0.60 <= ratio <= 0.75):
                step_errors.append(f"DataTab 68/32 ratio deviation: {ratio:.1%}")
            if sidebar_w < 200:
                step_errors.append(f"Sidebar width too small: {sidebar_w}px")
            if table_h < 80:
                step_errors.append(f"Table height too small: {table_h}px")
            if right_w < 150:
                step_errors.append(f"Preview width too small: {right_w}px")

            if step_errors:
                print(f"    -> FAILED with {len(step_errors)} errors:")
                for e in step_errors:
                    print(f"       * {e}")
                total_errors.extend(step_errors)
            else:
                print(f"    -> PASSED (0 violations)")
    finally:
        app.destroy()

    # 2. Maximum Length Strings & Special Characters
    print("\n>>> Phase 2: Form Input Stress (500 chars, Unicode, Special Characters, Emojis, XML)")
    root = ctk.CTk()
    try:
        state = AppState(root)
        controller = AppController(state)
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root.geometry("1000x700+0+0")
        root.update_idletasks()
        root.update()

        for key, val in STRESS_STRINGS.items():
            state.item_code_var.set(f"C_{val[:60]}")
            state.item_name_var.set(f"N_{val}")
            state.carton_qty_var.set("12345")
            state.total_qty_var.set("123450")
            state.po_var.set(f"PO_{val[:20]}")
            state.lot_var.set(val[:40])

            root.update_idletasks()
            root.update()

            stress_errors = []
            _check_bounds(data_tab, stress_errors, f"Stress_{key}")
            if stress_errors:
                print(f"  [FAIL] Input stress '{key}': {len(stress_errors)} error(s)")
                total_errors.extend(stress_errors)
            else:
                print(f"  [PASS] Input stress '{key}': OK")
    finally:
        root.destroy()

    # 3. Action Buttons clickable and >= 70px at 1000x700
    print("\n>>> Phase 3: Action Buttons Clickability & Width at 1000x700")
    root_btn = ctk.CTk()
    try:
        state = AppState(root_btn)
        controller = AppController(state)
        notebook = ttk.Notebook(root_btn)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root_btn.geometry("1000x700+0+0")
        root_btn.update_idletasks()
        root_btn.update()

        left_panel = data_tab.winfo_children()[0]
        form_frame = left_panel.winfo_children()[0]

        btn_bars = [c for c in form_frame.winfo_children() if isinstance(c, ctk.CTkFrame) and len(c.winfo_children()) == 3]
        print(f"  Found {len(btn_bars)} button bars (expected 2)")

        button_records = []
        for bar_idx, bar in enumerate(btn_bars, 1):
            for btn in bar.winfo_children():
                if isinstance(btn, ctk.CTkButton):
                    text = btn.cget("text")
                    w = btn.winfo_width()
                    h = btn.winfo_height()
                    st = btn.cget("state")
                    button_records.append((text, w, h, st))
                    print(f"    - Button '{text}': Width={w}px, Height={h}px, State={st}")
                    if w < 70:
                        err = f"Button '{text}' width {w}px < 70px"
                        print(f"      [FAIL] {err}")
                        total_errors.append(err)
                    if st != "normal":
                        err = f"Button '{text}' state is {st}, expected 'normal'"
                        print(f"      [FAIL] {err}")
                        total_errors.append(err)

        if len(button_records) < 6:
            err = f"Expected 6 buttons, found {len(button_records)}"
            print(f"  [FAIL] {err}")
            total_errors.append(err)
        else:
            print(f"  [PASS] All 6 buttons verified with width >= 70px and state='normal'")
    finally:
        root_btn.destroy()

    print("\n" + "=" * 80)
    if total_errors:
        print(f"ADVERSARIAL STRESS TEST FAILED with {len(total_errors)} issue(s).")
        return 1
    else:
        print("ALL ADVERSARIAL STRESS TESTS PASSED EMPIRICALLY (0 violations).")
        return 0


if __name__ == "__main__":
    sys.exit(run_adversarial_tests())
