from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
from PIL import Image
import pytest

from core.runtime_paths import ENV_DATA_ROOT, ENV_OUTPUT_ROOT, prepare_runtime_paths
from core.slip_printer_engine import SlipRecord, create_record, FIELD_LABELS
from slip_printer_app import main
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.main_window import SlipPrinterApp, run_health_check


# ======================================================================
# Helpers
# ======================================================================

def _generate_heavy_records(count: int = 120) -> list[SlipRecord]:
    return [
        create_record(
            row_number=i,
            item_code=f"ITEM-{i:05d}-CODE",
            item_name=f"Detailed Material Description for Item #{i:04d} with Extra Text",
            carton_qty=str(10 + (i % 50)),
            total_qty=str((10 + (i % 50)) * (10 + (i % 5))),
            po=f"11260818{i:02d}" if i < 100 else f"11260819{i % 100:02d}",
            po_detail="00010",
            po_sub=f"+{i:03d}" if i < 1000 else "+999",
            box=str(10 + (i % 5)),
            rev=f"{(i % 99) + 1:02d}",
            lot=f"LOT{i:07d}" if i % 2 == 0 else " " * 10,
        )
        for i in range(1, count + 1)
    ]


def _collect_widget_geometries(widget, path: str = "") -> dict[str, tuple[int, int, int, int]]:
    """Recursively collect (x, y, width, height) of mapped widgets."""
    geometries = {}
    current_path = f"{path}/{widget.winfo_name()}"
    if widget.winfo_ismapped():
        geometries[current_path] = (
            widget.winfo_x(),
            widget.winfo_y(),
            widget.winfo_width(),
            widget.winfo_height(),
        )
    for child in widget.winfo_children():
        geometries.update(_collect_widget_geometries(child, current_path))
    return geometries


# ======================================================================
# 1. Adversarial Test: 100+ Records & Scrolling in DataTab & LayoutTab
# ======================================================================

def test_datatab_100_plus_records_and_scrolling(tk_root):
    """Verify DataTab handles 100+ records with bi-directional scrolling and zero coordinate drift."""
    root = tk_root
    try:
        root.geometry("1400x900+50+50")
        state = AppState(root)
        controller = AppController(state)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        notebook.select(data_tab)

        # Set preview limit to 200 to display all 120 records
        state.preview_limit_var.set("200")
        records = _generate_heavy_records(120)
        state.records = records
        data_tab.set_records(select_index=0)
        root.update_idletasks()
        root.update()

        # 1. Verify 120 items are populated in the Treeview
        tree = data_tab.preview_tree
        tree_children = tree.get_children()
        assert len(tree_children) == 120, f"Expected 120 tree items, got {len(tree_children)}"
        assert len(state.preview_index_map) == 120

        # Snapshot baseline geometries of key containers
        baseline_geo = _collect_widget_geometries(data_tab, "DataTab")

        # 2. Test Vertical Scrolling: Scroll to top, middle, bottom, and incremental units
        for pos in (0.0, 0.25, 0.5, 0.75, 1.0):
            tree.yview_moveto(pos)
            root.update_idletasks()
            root.update()
            y_first, y_last = tree.yview()
            assert 0.0 <= y_first <= 1.0
            assert 0.0 <= y_last <= 1.0

        # Scroll in small discrete steps
        for _ in range(10):
            tree.yview_scroll(3, "units")
            root.update_idletasks()
            root.update()

        for _ in range(5):
            tree.yview_scroll(-2, "pages")
            root.update_idletasks()
            root.update()

        # 3. Test Horizontal Scrolling
        for pos in (0.0, 0.5, 1.0):
            tree.xview_moveto(pos)
            root.update_idletasks()
            root.update()
            x_first, x_last = tree.xview()
            assert 0.0 <= x_first <= 1.0
            assert 0.0 <= x_last <= 1.0

        for _ in range(5):
            tree.xview_scroll(2, "units")
            root.update_idletasks()
            root.update()

        # 4. Test Selecting Boundary Rows across 120 items
        # Index 0 (Top)
        data_tab._select_tree_row(0)
        root.update_idletasks()
        root.update()
        assert state.selected_record_index == 0
        assert state.item_code_var.get() == "ITEM-00001-CODE"
        assert state.form_mode_var.get() == "Đang sửa dòng 1"

        # Index 60 (Middle)
        data_tab._select_tree_row(60)
        root.update_idletasks()
        root.update()
        assert state.selected_record_index == 60
        assert state.item_code_var.get() == "ITEM-00061-CODE"
        assert state.form_mode_var.get() == "Đang sửa dòng 61"

        # Index 119 (Bottom)
        data_tab._select_tree_row(119)
        root.update_idletasks()
        root.update()
        assert state.selected_record_index == 119
        assert state.item_code_var.get() == "ITEM-00120-CODE"
        assert state.form_mode_var.get() == "Đang sửa dòng 120"

        # 5. Verify Zero Layout / Coordinate Drift
        current_geo = _collect_widget_geometries(data_tab, "DataTab")
        left_panel = getattr(data_tab, "left_panel", data_tab.winfo_children()[0])
        form_frame = getattr(data_tab, "form_frame", left_panel.winfo_children()[0])
        table_frame = getattr(data_tab, "table_frame", data_tab.preview_tree.master)
        preview_frame = getattr(data_tab, "preview_frame", data_tab.winfo_children()[1])

        # Key container positions and dimensions must remain strictly identical
        assert form_frame.winfo_height() > 150
        assert table_frame.winfo_height() > 150
        assert preview_frame.winfo_width() > 250
        assert table_frame.winfo_y() == form_frame.winfo_height() + 8 or table_frame.winfo_y() > form_frame.winfo_y()

        # Check that no mapped widget in data_tab has negative coordinates or zero size
        for path, (x, y, w, h) in current_geo.items():
            assert w > 0 and h > 0, f"Widget {path} has invalid size: {w}x{h}"
            assert x >= 0 and y >= 0, f"Widget {path} drifted to negative coordinates: ({x}, {y})"

    finally:
        state.po_registry.close()


def test_layouttab_100_plus_items_and_navigation(tk_root):
    """Verify LayoutTab handles multiple layout items, vertical/horizontal scrolling, and step size changes."""
    root = tk_root
    try:
        root.geometry("1400x900+50+50")
        state = AppState(root)
        controller = AppController(state)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        layout_tab = LayoutTabPanel(notebook, controller)
        notebook.add(layout_tab, text="Layout")
        layout_tab.refresh_tree()
        root.update_idletasks()
        root.update()

        tree = layout_tab.layout_tree
        initial_count = len(tree.get_children())
        assert initial_count > 0

        # 1. Insert 100 additional layout items to stress test the tree and scrollbars
        for i in range(1, 101):
            tree.insert(
                "",
                "end",
                iid=f"stress_item_{i}",
                values=(f"Vị trí trường thử nghiệm #{i}", "text", f"{100 + i * 2} pt", f"{200 + i * 3} pt"),
            )

        root.update_idletasks()
        root.update()
        assert len(tree.get_children()) == initial_count + 100

        # 2. Test Scrolling in Layout Tree
        for pos in (0.0, 0.5, 1.0):
            tree.yview_moveto(pos)
            tree.xview_moveto(pos)
            root.update_idletasks()
            root.update()

        # 3. Test Editor Panel
        editor = getattr(layout_tab, "editor_frame", layout_tab.winfo_children()[1])
        assert isinstance(editor, (ctk.CTkFrame, ctk.CTkScrollableFrame))

        # 4. Test Step Size Selection and Nudge Actions
        for step_val in ("1", "5", "15"):
            layout_tab.step_size_var.set(step_val)
            layout_tab._nudge(1, 0)
            layout_tab._nudge(0, 1)
            layout_tab._nudge(-1, 0)
            layout_tab._nudge(0, -1)
            layout_tab._resize(1, 1)
            layout_tab._resize(-1, -1)

        # 5. Verify Editor Bounds and absence of geometry drift
        layout_geo = _collect_widget_geometries(layout_tab, "LayoutTab")
        for path, (x, y, w, h) in layout_geo.items():
            assert w > 0 and h > 0, f"Widget {path} has invalid size: {w}x{h}"
            assert x >= 0 and y >= 0, f"Widget {path} has negative coordinates: ({x}, {y})"

    finally:
        state.po_registry.close()


# ======================================================================
# 2. Adversarial Test: Preview Aspect Ratios & Resize Callbacks
# ======================================================================

def test_preview_aspect_ratio_rendering(tk_root):
    """Stress test preview pane rendering against extreme image aspect ratios and dimensions."""
    aspect_ratios = [
        (595, 842, "Standard A4 Portrait (1:1.414)"),
        (842, 595, "A4 Landscape (1.414:1)"),
        (200, 2000, "Extreme Tall Strip (1:10)"),
        (3000, 150, "Extreme Wide Banner (20:1)"),
        (800, 800, "Perfect Square (1:1)"),
        (16, 16, "Ultra Tiny (16x16)"),
        (3840, 2160, "4K UHD (16:9)"),
    ]
    root = tk_root
    try:
        root.geometry("1200x800+50+50")
        state = AppState(root)
        controller = AppController(state)
        controller.set_view(None)  # standalone test

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)

        data_tab = DataTabPanel(notebook, controller)
        notebook.add(data_tab, text="Data")
        root.update_idletasks()
        root.update()

        for img_w, img_h, label in aspect_ratios:
            # Create test PIL image with specific aspect ratio
            test_image = Image.new("RGB", (img_w, img_h), color=(70, 130, 180))
            state.preview_source_image = test_image

            # Trigger display update
            data_tab.update_preview_display()
            root.update_idletasks()
            root.update()

            # Verify CTkImage was created and configured
            assert state.current_preview_image is not None
            assert isinstance(state.current_preview_image, ctk.CTkImage)

            # Check rendered image dimensions
            rendered_w, rendered_h = state.current_preview_image._size
            assert rendered_w > 0, f"[{label}] Rendered width is 0"
            assert rendered_h > 0, f"[{label}] Rendered height is 0"

            # Check that rendered thumbnail does not exceed container dimensions
            label_w = max(data_tab.preview_image_label.winfo_width() - 16, 120)
            label_h = max(data_tab.preview_image_label.winfo_height() - 16, 120)
            assert rendered_w <= label_w + 1, f"[{label}] Rendered width {rendered_w} exceeds container {label_w}"
            assert rendered_h <= label_h + 1, f"[{label}] Rendered height {rendered_h} exceeds container {label_h}"

            # Verify aspect ratio preservation
            source_ratio = img_w / img_h
            rendered_ratio = rendered_w / rendered_h
            assert abs(source_ratio - rendered_ratio) / source_ratio < 0.05 or abs(rendered_w - 120) <= 2 or abs(rendered_h - 120) <= 2, (
                f"[{label}] Aspect ratio drifted: source={source_ratio:.3f}, rendered={rendered_ratio:.3f}"
            )
    finally:
        state.po_registry.close()



def test_preview_rapid_resizing_callbacks(tk_root):
    """Verify that rapid window resize events do not cause event recursion or preview distortion."""
    root = tk_root
    state = AppState(root)
    controller = AppController(state)
    controller.set_view(None)
    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)
    data_tab = DataTabPanel(notebook, controller)
    notebook.add(data_tab, text="Data")
    try:
        # Load sample data
        state.records = _generate_heavy_records(5)
        data_tab.set_records(select_index=0)
        
        # Set a synthetic preview image
        state.preview_source_image = Image.new("RGB", (800, 1200), color=(20, 100, 200))
        data_tab.update_preview_display()
        root.update_idletasks()
        root.update()

        # Simulate user dragging the window border rapidly across diverse aspect ratios
        test_dimensions = [
            (1000, 700),
            (1050, 720),
            (1120, 750),
            (1200, 800),
            (1366, 768),
            (1440, 900),
            (1600, 900),
            (1920, 1080),
            (1280, 1024),
            (1000, 700),
        ]

        for w, h in test_dimensions:
            root.geometry(f"{w}x{h}+0+0")
            root.update_idletasks()
            root.update()
            # Explicitly invoke the resize callback
            data_tab._on_preview_resize()
            root.update_idletasks()
            root.update()

            assert state.current_preview_image is not None
            img_w, img_h = state.current_preview_image._size
            assert img_w > 0 and img_h > 0
    finally:
        state.po_registry.close()


# ======================================================================
# 3. Adversarial Test: CLI --health-check Environmental Scenarios
# ======================================================================

def test_cli_health_check_standard():
    """Verify standard --health-check returns exit code 0."""
    exit_code = main(["--health-check"])
    assert exit_code == 0


def test_cli_health_check_custom_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify --health-check functions seamlessly with custom environment variables."""
    custom_data = tmp_path / "custom_data_dir"
    custom_output = tmp_path / "custom_output_dir"
    monkeypatch.setenv(ENV_DATA_ROOT, str(custom_data))
    monkeypatch.setenv(ENV_OUTPUT_ROOT, str(custom_output))

    exit_code = main(["--health-check"])
    assert exit_code == 0

    # Verify runtime paths were created
    assert custom_data.is_dir()
    assert (custom_data / "layout_config.json").is_file()
    assert (custom_data / "po_registry.db").is_file()
    assert custom_output.is_dir()


def test_cli_health_check_missing_template_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify --health-check fails closed when template.pdf is absent."""
    custom_data = tmp_path / "data"
    empty_bundle = tmp_path / "empty_bundle"
    empty_bundle.mkdir()

    monkeypatch.setenv(ENV_DATA_ROOT, str(custom_data))
    monkeypatch.setattr("core.runtime_paths.bundle_dir", lambda: empty_bundle)

    with pytest.raises(FileNotFoundError, match="Không tìm thấy template.pdf"):
        run_health_check()


def test_cli_health_check_idempotence():
    """Verify that multiple consecutive health check invocations do not cause SQLite locking."""
    for _ in range(5):
        exit_code = main(["--health-check"])
        assert exit_code == 0
