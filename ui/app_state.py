from __future__ import annotations

import queue
from datetime import datetime
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from core.po_registry import PORegistry
from core.runtime_paths import RuntimePaths, prepare_runtime_paths
from core.slip_printer_engine import SlipRecord, load_layout_config


class AppState:
    def __init__(self, root: ctk.CTk | None = None, paths: RuntimePaths | None = None):
        self.root = root

        # Backend paths and registry
        self.paths: RuntimePaths = paths if paths is not None else prepare_runtime_paths()
        self.bundle_dir = self.paths.bundle_dir
        self.runtime_dir = self.paths.data_dir
        self.layout_path = self.paths.layout_path
        self.template_path = self.paths.template_path
        self.layout_config = load_layout_config(self.layout_path)
        self.po_registry = PORegistry(self.paths.registry_path)

        # In-memory data
        self.records: list[SlipRecord] = []
        self.preview_index_map: list[int] = []
        self.selected_record_index: int = 0
        self.preview_source_image: Image.Image | None = None
        self.current_preview_image: ctk.CTkImage | None = None

        # App flow state
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.generated_output_path: Path | None = None
        self.update_check_running: bool = False

        # Tkinter Variables (Bound to UI)
        self.excel_var = ctk.StringVar(master=self.root, value=self._default_excel_path())
        self.template_var = ctk.StringVar(master=self.root, value=str(self.template_path) if self.template_path.exists() else "")
        self.output_dir_var = ctk.StringVar(master=self.root, value=str(self.paths.output_dir))
        self.output_name_var = ctk.StringVar(master=self.root, value=self._default_output_name())
        self.status_var = ctk.StringVar(master=self.root, value="Sẵn sàng")
        self.summary_var = ctk.StringVar(master=self.root, value="Chưa có dữ liệu")
        self.preview_limit_var = ctk.StringVar(master=self.root, value="50")
        self.form_mode_var = ctk.StringVar(master=self.root, value="Đang tạo dòng mới")

        # Form fields
        self.item_code_var = ctk.StringVar(master=self.root)
        self.item_name_var = ctk.StringVar(master=self.root)
        self.carton_qty_var = ctk.StringVar(master=self.root)
        self.total_qty_var = ctk.StringVar(master=self.root)
        self.po_var = ctk.StringVar(master=self.root)
        self.po_detail_var = ctk.StringVar(master=self.root)
        self.po_sub_var = ctk.StringVar(master=self.root)
        self.box_var = ctk.StringVar(master=self.root)
        self.rev_var = ctk.StringVar(master=self.root)
        self.lot_var = ctk.StringVar(master=self.root)

        # Layout editor fields
        self.layout_choice_var = ctk.StringVar(master=self.root, value="")
        self.layout_label_var = ctk.StringVar(master=self.root, value="")
        self.layout_field_var = ctk.StringVar(master=self.root, value="")
        self.x_var = ctk.StringVar(master=self.root, value="")
        self.y_var = ctk.StringVar(master=self.root, value="")
        self.width_var = ctk.StringVar(master=self.root, value="")
        self.height_var = ctk.StringVar(master=self.root, value="")

        # History fields
        self.history_search_var = ctk.StringVar(master=self.root, value="")
        self.history_total_var = ctk.StringVar(master=self.root, value="0")
        self.history_today_var = ctk.StringVar(master=self.root, value="0")
        self.history_next_po_var = ctk.StringVar(master=self.root, value="--")
        self.history_status_var = ctk.StringVar(master=self.root, value="")

    def _default_excel_path(self) -> str:
        default_path = self.bundle_dir / "DummySlip.xlsx"
        return str(default_path) if default_path.exists() else ""

    def _default_output_name(self) -> str:
        return datetime.now().strftime("%y%m%d_%H%M%S") + ".pdf"
