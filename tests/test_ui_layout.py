import customtkinter as ctk
from tkinter import ttk
import pytest
from ui.app_controller import AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.layout_tab import LayoutTabPanel
from core.slip_printer_engine import create_record


def test_datatab_layout_and_responsive_height(tk_root):
    root = tk_root
    
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)
        
        tab = DataTabPanel(notebook, controller)
        notebook.add(tab, text="Data")
        
        # Check that left panel has form (weight 0) and table (weight 1)
        left_panel = getattr(tab, "left_panel", tab.winfo_children()[0])
        form_frame = getattr(tab, "form_frame", left_panel.winfo_children()[0])
        table_frame = getattr(tab, "table_frame", tab.preview_tree.master)
        preview_frame = getattr(tab, "preview_frame", tab.winfo_children()[1])
        
        # Populate test records
        records = [
            create_record(
                row_number=i,
                item_code=f"CODE-{i}",
                item_name=f"Product {i}",
                carton_qty="10",
                total_qty="100",
                po=f"PO-{i}",
                po_detail=f"DET-{i}",
                po_sub=f"SUB-{i}",
                box="10",
                rev="01",
                lot=" " * 10,
            )
            for i in range(1, 15)
        ]
        state.records = records
        tab.set_records(select_index=0)
        root.update_idletasks()
        root.update()
        
        # 1. Verify table has significant height (>150px) at standard size
        assert table_frame.winfo_height() > 150, f"Table height too small: {table_frame.winfo_height()}"
        assert len(tab.preview_tree.get_children()) == 14
        
        # 2. Verify form fields populated correctly
        assert state.item_code_var.get() == "CODE-1"
        assert state.item_name_var.get() == "Product 1"
        assert state.carton_qty_var.get() == "10"
        
        # 3. Simulate Maximize
        root.geometry("1920x1080+50+50")
        root.update_idletasks()
        root.update()
        assert table_frame.winfo_height() > 200, f"Table height shrunk on maximize: {table_frame.winfo_height()}"
        
        # 4. Simulate Small laptop screen (1280x720)
        root.geometry("1280x720+50+50")
        root.update_idletasks()
        root.update()
        assert table_frame.winfo_height() > 100, f"Table height disappeared on small screen: {table_frame.winfo_height()}"
        
        # 5. Test row selection
        tab._select_tree_row(2)
        assert state.item_code_var.get() == "CODE-3"
        
        # 6. Test clear form (must clear every field including Rev)
        tab.clear_form()
        assert state.item_code_var.get() == ""
        assert state.rev_var.get() == ""
        assert state.form_mode_var.get() == "Đang tạo dòng mới"

        # 7. Test Add Record (Thêm mới) with Auto PO Generation
        state.item_code_var.set("3V2ND25420")
        state.item_name_var.set("Tên hàng test")
        state.carton_qty_var.set("160")
        state.box_var.set("10")
        state.rev_var.set("01")
        
        initial_count = len(state.records)
        controller.add_record()
        assert len(state.records) == initial_count + 10
        newest = state.records[-1]
        assert newest.item_code == "3V2ND25420"
        assert newest.po.startswith("11")
        assert newest.po_detail == "00010"
        assert newest.po_sub == "+001"
        assert newest.box == "010/010"
        # 8. Verify preview_frame is never crushed (has width >= 250px)
        assert preview_frame.winfo_width() > 250, f"Preview frame squished: {preview_frame.winfo_width()}"

        # 9. Verify Action Button Bars have spacious width (>150px per button)
        btn_bars = [c for c in form_frame.winfo_children() if isinstance(c, ctk.CTkFrame) and len([b for b in c.winfo_children() if isinstance(b, ctk.CTkButton)]) == 3]
        add_btn = [b for b in btn_bars[0].winfo_children() if isinstance(b, ctk.CTkButton)][0]
        assert add_btn.winfo_width() > 150, f"Button width too narrow: {add_btn.winfo_width()}px"
    finally:
        state.po_registry.close()


def test_layout_tab_rendering(tk_root):
    root = tk_root
    root.geometry("1280x720+50+50")
    
    state = AppState(root)
    controller = AppController(state)
    try:
        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True)
        
        layout_tab = LayoutTabPanel(notebook, controller)
        notebook.add(layout_tab, text="Layout")
        layout_tab.refresh_tree()
        root.update_idletasks()
        root.update()
        
        list_frame = getattr(layout_tab, "list_frame", layout_tab.winfo_children()[0])
        editor = getattr(layout_tab, "editor_frame", layout_tab.winfo_children()[1])
        
        assert list_frame.winfo_width() > 200
        assert editor.winfo_width() > 300
        assert len(layout_tab.layout_tree.get_children()) > 0
        
        # Test nudge and step change
        layout_tab.step_size_var.set("15")
        layout_tab._nudge(1, 0)
    finally:
        state.po_registry.close()


def test_theme_mode_switching_and_persistence(tk_root):
    """Verify theme modes (Dark, Light, System) switch cleanly and persist settings to disk."""
    import json
    from ui.main_window import SlipPrinterApp

    root = tk_root
    state = AppState(root)
    try:
        # Create a mock/lightweight instance binding to test methods
        dummy = SlipPrinterApp.__new__(SlipPrinterApp)
        dummy.app_state = state
        dummy._current_theme_mode = "System"

        # 1. Test Saving Setting
        dummy._save_theme_setting("Light")
        settings_file = state.paths.data_dir / "user_settings.json"
        assert settings_file.is_file()
        saved = json.loads(settings_file.read_text(encoding="utf-8"))
        assert saved.get("appearance_mode") == "Light"

        # 2. Test Loading Setting
        loaded = dummy._load_theme_setting()
        assert loaded == "Light"

        # 3. Test Display Label
        assert dummy._get_display_theme_label("Light") == "Sáng ☀️"
        assert dummy._get_display_theme_label("Dark") == "Tối 🌙"
        assert dummy._get_display_theme_label("System") == "Hệ thống 🖥️"

        # 4. Test Mode Transition Mapping
        dummy._on_theme_changed("Tối 🌙")
        assert dummy._current_theme_mode == "Dark"

        saved_dark = json.loads(settings_file.read_text(encoding="utf-8"))
        assert saved_dark.get("appearance_mode") == "Dark"
    finally:
        state.po_registry.close()



