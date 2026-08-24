from __future__ import annotations

from tkinter import ttk
import customtkinter as ctk
import pytest

from core.slip_printer_engine import create_record
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel
from ui.main_window import SlipPrinterApp

RESOLUTIONS = [
    (1000, 700, "1000x700 Min"),
    (1366, 768, "1366x768 Laptop"),
    (1920, 1080, "1920x1080 Desktop"),
]


def _sample_records(count: int = 10):
    return [
        create_record(
            row_number=i,
            item_code=f"CODE-{i:03d}",
            item_name=f"Sample Product {i}",
            carton_qty="15",
            total_qty="150",
            po=f"1100{i:04d}",
            po_detail="00010",
            po_sub="+001",
            box="10",
            rev="01",
            lot=" " * 10,
        )
        for i in range(1, count + 1)
    ]


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


def test_isolated_components_responsiveness(tk_root):
    """Verify DataTab and LayoutTab responsiveness across min, laptop, and desktop resolutions."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # 1. DataTab verification
        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        state.records = _sample_records(12)
        data_tab.set_records(select_index=0)

        for width, height, label in RESOLUTIONS:
            root.geometry(f"{width}x{height}+0+0")
            root.update_idletasks()
            root.update()

            data_violations = _check_no_zero_or_negative_geometry(data_tab, "DataTab")
            assert not data_violations, f"[{label}] DataTab violations: {data_violations}"

            left_panel = getattr(data_tab, "left_panel", data_tab.winfo_children()[0])
            preview_frame = getattr(data_tab, "preview_frame", data_tab.winfo_children()[1])
            left_w = left_panel.winfo_width()
            right_w = preview_frame.winfo_width()
            total_w = left_w + right_w
            assert total_w > 0
            left_ratio = left_w / total_w
            assert 0.60 <= left_ratio <= 0.75, f"[{label}] Ratio {left_ratio:.2%} out of [60%, 75%]"

            form_frame = getattr(data_tab, "form_frame", left_panel.winfo_children()[0])
            btn_bars = [c for c in form_frame.winfo_children() if isinstance(c, ctk.CTkFrame) and len(c.winfo_children()) == 3]
            for bar in btn_bars:
                for btn in bar.winfo_children():
                    if isinstance(btn, ctk.CTkButton):
                        assert btn.winfo_width() >= 70, f"[{label}] Button {btn.cget('text')} width < 70px"

            table_frame = getattr(data_tab, "table_frame", data_tab.preview_tree.master)
            assert table_frame.winfo_height() >= 80, f"[{label}] Table height < 80px"
            assert right_w >= 150, f"[{label}] Preview width < 150px"

        # 2. LayoutTab verification
        notebook.forget(data_tab)
        data_tab.destroy()

        layout_tab = LayoutTabPanel(notebook, controller)
        notebook.add(layout_tab, text="Layout")
        layout_tab.refresh_tree()

        for width, height, label in RESOLUTIONS:
            root.geometry(f"{width}x{height}+0+0")
            root.update_idletasks()
            root.update()

            layout_violations = _check_no_zero_or_negative_geometry(layout_tab, "LayoutTab")
            assert not layout_violations, f"[{label}] LayoutTab violations: {layout_violations}"

            list_frame = getattr(layout_tab, "list_frame", layout_tab.winfo_children()[0])
            editor = getattr(layout_tab, "editor_frame", layout_tab.winfo_children()[1])
            assert list_frame.winfo_width() >= 150, f"[{label}] LayoutTab list_frame < 150px"
            assert editor.winfo_width() >= 200, f"[{label}] LayoutTab editor < 200px"
            assert len(layout_tab.layout_tree.get_children()) > 0
    finally:
        state.po_registry.close()


def test_full_application_responsiveness(tk_root):
    """Verify full SlipPrinterApp responsiveness across min, laptop, and desktop resolutions."""
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
    notebook.add(data_tab, text="Data")
    notebook.add(layout_tab, text="Layout")
    splitter.add(main_host, weight=1)

    sidebar_width = 360

    def apply_splitter_width():
        try:
            splitter.sashpos(0, sidebar_width)
        except Exception:
            pass

    try:
        state.records = _sample_records(10)
        data_tab.set_records(select_index=0)

        for width, height, label in RESOLUTIONS:
            root.geometry(f"{width}x{height}+0+0")
            root.update_idletasks()
            root.update()
            apply_splitter_width()
            root.update_idletasks()
            root.update()

            # Check window bounds and mapping
            violations = _check_no_zero_or_negative_geometry(root, "FullApp")
            assert not violations, f"[{label}] Geometry violations in FullApp: {violations}"

            # Check sidebar host or sidebar width
            sidebar_w = sidebar.winfo_width()
            assert sidebar_w >= 200, f"[{label}] Sidebar width {sidebar_w} < 200px"

            # Check table and preview in DataTab
            table_frame = getattr(data_tab, "table_frame", data_tab.preview_tree.master)
            preview_frame = getattr(data_tab, "preview_frame", data_tab.winfo_children()[1])
            assert table_frame.winfo_height() >= 80, f"[{label}] App Table height < 80px"
            assert preview_frame.winfo_width() >= 150, f"[{label}] App Preview width < 150px"

            # Check action buttons in DataTab
            form_frame = getattr(data_tab, "form_frame", data_tab.winfo_children()[0].winfo_children()[0])
            btn_bars = [c for c in form_frame.winfo_children() if isinstance(c, ctk.CTkFrame) and len(c.winfo_children()) == 3]
            for bar in btn_bars:
                for btn in bar.winfo_children():
                    if isinstance(btn, ctk.CTkButton):
                        assert btn.winfo_width() >= 70, f"[{label}] Button {btn.cget('text')} width < 70px"
    finally:
        state.po_registry.close()
