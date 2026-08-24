import sys
import customtkinter as ctk
from tkinter import ttk
from ui.main_window import SlipPrinterApp
from core.slip_printer_engine import create_record

def audit_resolution(app, width, height, sash_pos=None):
    app.geometry(f"{width}x{height}")
    if sash_pos is not None:
        try:
            app.splitter.sashpos(0, sash_pos)
        except Exception:
            pass
    app.update()
    
    data_tab = app.data_tab
    left_panel = data_tab.winfo_children()[0]
    preview_frame = data_tab.winfo_children()[1]
    
    form_frame = left_panel.winfo_children()[0]
    table_frame = left_panel.winfo_children()[1]
    
    btn_bar_1 = form_frame.winfo_children()[-2]
    btn_bar_2 = form_frame.winfo_children()[-1]
    
    # Measure entries
    po_sub_frame = None
    for child in form_frame.winfo_children():
        if isinstance(child, ctk.CTkFrame) and child not in (btn_bar_1, btn_bar_2, form_frame.winfo_children()[0]):
            po_sub_frame = child
            break

    print(f"\n=======================================================")
    print(f"RESOLUTION: {width}x{height} (Sash at: {app.splitter.sashpos(0)})")
    print(f"=======================================================")
    print(f"App Window: {app.winfo_width()}x{app.winfo_height()}")
    print(f"Sidebar: {app.sidebar.winfo_width()}x{app.sidebar.winfo_height()}")
    print(f"Content Area: width={app.splitter.winfo_width() - app.splitter.sashpos(0)}")
    print(f"DataTab Total: {data_tab.winfo_width()}x{data_tab.winfo_height()}")
    print(f"  - Left Panel (68% col 0): {left_panel.winfo_width()}x{left_panel.winfo_height()}")
    print(f"    - Form Frame: {form_frame.winfo_width()}x{form_frame.winfo_height()}")
    print(f"    - Table Frame (Treeview): {table_frame.winfo_width()}x{table_frame.winfo_height()}")
    print(f"    - Treeview widget: {data_tab.preview_tree.winfo_width()}x{data_tab.preview_tree.winfo_height()}")
    print(f"  - Preview Frame (32% col 1): {preview_frame.winfo_width()}x{preview_frame.winfo_height()}")
    print(f"    - Image Label: {data_tab.preview_image_label.winfo_width()}x{data_tab.preview_image_label.winfo_height()}")
    print(f"    - QR Box: {data_tab.qr_payload_box.winfo_width()}x{data_tab.qr_payload_box.winfo_height()}")

    # Measure action buttons
    b1_widths = [b.winfo_width() for b in btn_bar_1.winfo_children()]
    b2_widths = [b.winfo_width() for b in btn_bar_2.winfo_children()]
    print(f"  - Primary Buttons (Hàng 1) Widths: {b1_widths}")
    print(f"  - Secondary Buttons (Hàng 2) Widths: {b2_widths}")

    # Measure form entries
    po_w = data_tab.po_entry.winfo_width()
    print(f"  - PO Entry width: {po_w}px")

    # Measure PO sub frame entries
    if po_sub_frame:
        po_det_w = data_tab.po_detail_entry.winfo_width()
        po_sub_w = data_tab.po_sub_entry.winfo_width()
        print(f"  - PO Detail Entry width: {po_det_w}px, PO Sub Entry width: {po_sub_w}px")
        if po_det_w < 50 or po_sub_w < 40:
            print(f"    [WARNING] PO sub entries are heavily squeezed!")

    # Check for anomalies
    if table_frame.winfo_height() < 120:
        print(f"    [WARNING] Table frame height is very cramped (<120px): {table_frame.winfo_height()}px")
    if preview_frame.winfo_width() < 220:
        print(f"    [WARNING] Preview frame width is very narrow (<220px): {preview_frame.winfo_width()}px")

def main():
    app = SlipPrinterApp()
    app.update()
    
    # Populate mock records
    records = [
        create_record(
            row_number=i,
            item_code=f"3V2ND25420-{i}",
            item_name=f"SAMPLE PRODUCT NAME {i} VERY LONG DESCRIPTION TEXT",
            carton_qty="160",
            total_qty="1600",
            po=f"110023{i:04d}",
            po_detail="00010",
            po_sub="+001",
            box="10",
            rev="01",
            lot=" " * 10,
        )
        for i in range(1, 20)
    ]
    app.set_records(records, 0)
    app.update()

    resolutions = [
        (1000, 700),
        (1100, 700),
        (1200, 720),
        (1280, 720),
        (1366, 768),
        (1400, 900),
        (1600, 900),
        (1920, 1080),
    ]

    for w, h in resolutions:
        audit_resolution(app, w, h)

    app.destroy()

if __name__ == "__main__":
    main()
