from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

from core.slip_printer_engine import (
    START_ROW,
    SlipRecord,
    auto_fill_po,
    calculate_total_qty,
    create_record,
    generate_pdf_from_records,
    get_default_layout_config,
    load_layout_config,
    read_records,
    save_layout_config,
    update_layout_item,
    validate_revision,
)
from ui.app_state import AppState
from updater.app_updates import (
    ApplicationUpdateError,
    application_install_root,
    install_update,
)
from updater.update_delivery import (
    UpdateDeliveryError,
    current_release_version,
    discover_update,
    fetch_update,
    load_update_config,
)

APP_TITLE = "In Phiếu Hiện Vật"

class AppController:
    def __init__(self, state: AppState):
        self.app_state = state
        self.view = None  # Cần gọi set_view(view) sau khi khởi tạo view

    def set_view(self, view):
        self.view = view

    # --- TIỆN ÍCH FILE ---
    def reset_defaults(self) -> None:
        self.app_state.excel_var.set(self.app_state._default_excel_path())
        if self.app_state.template_path.exists():
            self.app_state.template_var.set(str(self.app_state.template_path))
        else:
            self.app_state.template_var.set("")
        self.app_state.output_dir_var.set(str(self.app_state.paths.output_dir))
        self.app_state.output_name_var.set(self.app_state._default_output_name())
        self.app_state.status_var.set("Đã khôi phục đường dẫn mặc định")
        if self.view:
            self.view.append_log("Đã đặt lại đường dẫn mặc định.")

    def pick_excel_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chọn file Excel để import",
            filetypes=[("File Excel", "*.xlsx"), ("Tất cả các file", "*.*")],
            initialdir=self._existing_parent(self.app_state.excel_var.get()),
        )
        if selected:
            self.app_state.excel_var.set(selected)

    def pick_template_pdf(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chọn file PDF mẫu",
            filetypes=[("File PDF", "*.pdf"), ("Tất cả các file", "*.*")],
            initialdir=self._existing_parent(self.app_state.template_var.get()),
        )
        if selected:
            self.app_state.template_var.set(selected)
            if self.view:
                self.view.refresh_preview_image()

    def pick_output_dir(self) -> None:
        selected = filedialog.askdirectory(
            title="Chọn thư mục đầu ra",
            initialdir=self._existing_parent(self.app_state.output_dir_var.get()),
        )
        if selected:
            self.app_state.output_dir_var.set(selected)

    def _existing_parent(self, path_text: str) -> str:
        if not path_text:
            return str(self.app_state.runtime_dir)
        path = Path(path_text)
        if path.exists():
            return str(path if path.is_dir() else path.parent)
        if path.parent.exists():
            return str(path.parent)
        return str(self.app_state.runtime_dir)

    # --- DỮ LIỆU FORM ---
    def warn_lot_field_locked(self, _event=None) -> str:
        messagebox.showwarning(
            APP_TITLE,
            "Không nhập Ngày/Lot thủ công. Giá trị này chỉ lấy từ Excel; nếu để trống, QR sẽ dùng 10 dấu cách.",
        )
        return "break"

    def fill_sample_data(self) -> None:
        self.app_state.item_code_var.set("3V2ND00160")
        self.app_state.item_name_var.set("COVER RIGHT FUSER ASSY")
        self.app_state.carton_qty_var.set("20")
        self.app_state.total_qty_var.set("60")
        self.app_state.po_var.set("")
        self.app_state.po_detail_var.set("")
        self.app_state.po_sub_var.set("")
        self.app_state.box_var.set("001/003")
        self.app_state.rev_var.set("01")
        self.app_state.lot_var.set("")
        self.app_state.status_var.set("Đã điền dữ liệu mẫu. PO sẽ được tự sinh khi thêm dòng.")
        if self.view:
            self.view.append_log("Đã điền dữ liệu mẫu; PO sẽ được tự sinh khi thêm dòng.")

    def fill_lot_spaces(self) -> None:
        self.app_state.lot_var.set("")
        self.app_state.status_var.set("Ngày/Lot để trống sẽ được chuyển thành 10 dấu cách khi tạo QR.")

    def sync_total_qty(self, *_args) -> None:
        try:
            total_qty = calculate_total_qty(self.app_state.carton_qty_var.get(), self.app_state.box_var.get())
        except ValueError:
            total_qty = ""
        self.app_state.total_qty_var.set(total_qty)

    def _collect_form_record(self, *, row_number: int) -> SlipRecord:
        item_code = self.app_state.item_code_var.get().strip()
        item_name = self.app_state.item_name_var.get().strip()
        carton_qty = self.app_state.carton_qty_var.get().strip()
        total_qty = self.app_state.total_qty_var.get().strip()
        po = self.app_state.po_var.get().strip()
        box = self.app_state.box_var.get().strip()
        rev = self.app_state.rev_var.get().strip()

        if not item_code:
            raise ValueError("Bạn chưa nhập Mã hàng.")
        if not item_name:
            raise ValueError("Bạn chưa nhập Tên hàng.")
        if not carton_qty:
            raise ValueError("Bạn chưa nhập Số lượng thùng.")
        if not box:
            raise ValueError("Bạn chưa nhập Số box.")
        validate_revision(rev)

        po_detail = self.app_state.po_detail_var.get().strip()
        po_sub = self.app_state.po_sub_var.get().strip()

        record = create_record(
            row_number=row_number,
            item_code=item_code,
            item_name=item_name,
            carton_qty=carton_qty,
            total_qty=total_qty or carton_qty,
            po=po,
            po_detail=po_detail,
            po_sub=po_sub,
            box=box,
            rev=rev,
            lot=self.app_state.lot_var.get(),
        )

        if not record.po.strip():
            filled = auto_fill_po([record], self.app_state.po_registry)
            record = filled[0]
            self.app_state.po_var.set(record.po)
            self.app_state.po_detail_var.set(record.po_detail)
            self.app_state.po_sub_var.set(record.po_sub)

        return record

    def add_record(self) -> None:
        try:
            row_number = max(r.row_number for r in self.app_state.records) + 1 if self.app_state.records else START_ROW
            record = self._collect_form_record(row_number=row_number)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self.app_state.records.append(record)
        if self.view:
            self.view.append_log(f"Đã thêm dòng {record.row_number}: {record.item_code}")
            self.view.set_records(self.app_state.records, select_index=len(self.app_state.records) - 1)

    def update_selected_record(self) -> None:
        if not self.app_state.records:
            messagebox.showwarning(APP_TITLE, "Chưa có dòng nào để cập nhật.")
            return

        try:
            row_number = self.app_state.records[self.app_state.selected_record_index].row_number
            record = self._collect_form_record(row_number=row_number)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))
            return

        self.app_state.records[self.app_state.selected_record_index] = record
        if self.view:
            self.view.append_log(f"Đã cập nhật dòng {record.row_number}: {record.item_code}")
            self.view.set_records(self.app_state.records, select_index=self.app_state.selected_record_index)

    def delete_selected_record(self) -> None:
        if not self.app_state.records:
            return
        record = self.app_state.records.pop(self.app_state.selected_record_index)
        if self.view:
            self.view.append_log(f"Đã xóa dòng {record.row_number}: {record.item_code}")
            next_index = min(self.app_state.selected_record_index, len(self.app_state.records) - 1) if self.app_state.records else None
            self.view.set_records(self.app_state.records, select_index=next_index)

    def clear_all_records(self) -> None:
        if self.app_state.records and not messagebox.askyesno(APP_TITLE, "Xóa toàn bộ danh sách dữ liệu hiện tại?"):
            return
        self.app_state.records = []
        if self.view:
            self.view.set_records(self.app_state.records, select_index=None)
            self.view.append_log("Đã xóa toàn bộ dữ liệu trong app.")

    def import_from_excel(self) -> None:
        excel_path = self.app_state.excel_var.get().strip()
        if not excel_path:
            messagebox.showwarning(APP_TITLE, "Bạn chưa chọn file Excel để import.")
            return

        try:
            records = read_records(excel_path)
            for index, record in enumerate(records, start=1):
                try:
                    validate_revision(record.rev)
                except ValueError as exc:
                    raise ValueError(f"Dòng Excel {index}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Không import được Excel:\n{exc}")
            if self.view:
                self.view.append_log(f"Lỗi import Excel: {exc}")
            return

        empty_po_count = sum(1 for r in records if not r.po.strip())
        if empty_po_count > 0:
            try:
                records = auto_fill_po(records, self.app_state.po_registry)
                if self.view:
                    self.view.append_log(f"Đã tự động sinh PO cho {empty_po_count} dòng thiếu PO.")
            except Exception as exc:  # noqa: BLE001
                messagebox.showerror(APP_TITLE, f"Lỗi sinh PO tự động:\n{exc}")
                if self.view:
                    self.view.append_log(f"Lỗi sinh PO tự động: {exc}")
                return

        if self.view:
            self.view.set_records(records, select_index=0, source=f"Đã import {len(records)} dòng từ Excel: {excel_path}")

    # --- LAYOUT TAB ---
    def nudge_layout(self, dx: float, dy: float) -> None:
        item_id = self.app_state.layout_choice_var.get()
        if not item_id:
            return
        try:
            current_x = float(self.app_state.x_var.get() or 0)
            current_y = float(self.app_state.y_var.get() or 0)
            new_x = round(current_x + dx, 1)
            new_y = round(current_y + dy, 1)
            self.app_state.x_var.set(str(new_x))
            self.app_state.y_var.set(str(new_y))
            self.apply_layout_change()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Không di chuyển được:\n{exc}")

    def resize_layout(self, d_width: float, d_height: float) -> None:
        item_id = self.app_state.layout_choice_var.get()
        if not item_id:
            return
        try:
            w_str = self.app_state.width_var.get().strip()
            h_str = self.app_state.height_var.get().strip()
            if w_str and d_width != 0:
                new_w = max(5.0, round(float(w_str) + d_width, 1))
                self.app_state.width_var.set(str(new_w))
            if h_str and d_height != 0:
                new_h = max(5.0, round(float(h_str) + d_height, 1))
                self.app_state.height_var.set(str(new_h))
            self.apply_layout_change()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Không thay đổi kích thước được:\n{exc}")

    def apply_layout_change(self) -> None:
        item_id = self.app_state.layout_choice_var.get()
        if not item_id:
            return
        try:
            x = float(self.app_state.x_var.get())
            y = float(self.app_state.y_var.get())
            width = float(self.app_state.width_var.get()) if self.app_state.width_var.get().strip() else None
            height = float(self.app_state.height_var.get()) if self.app_state.height_var.get().strip() else None
            self.app_state.layout_config = update_layout_item(
                self.app_state.layout_config, item_id, x=x, y=y, width=width, height=height
            )
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, f"Không áp dụng được tọa độ:\n{exc}")
            return

        if self.view:
            self.view.refresh_layout_tree(select_id=item_id)
            self.view.refresh_preview_image()
            self.view.append_log(f"Đã cập nhật layout: {item_id}")

    def save_layout_config_to_disk(self) -> None:
        save_layout_config(self.app_state.layout_config, self.app_state.layout_path)
        if self.view:
            self.view.append_log(f"Đã lưu cấu hình layout: {self.app_state.layout_path}")
        messagebox.showinfo(APP_TITLE, f"Đã lưu cấu hình vào:\n{self.app_state.layout_path}")

    def reload_layout_config(self) -> None:
        self.app_state.layout_config = load_layout_config(self.app_state.layout_path)
        if self.view:
            self.view.refresh_layout_tree()
            self.view.refresh_preview_image()
            self.view.append_log("Đã nạp lại cấu hình layout từ file.")

    def reset_layout_config(self) -> None:
        self.app_state.layout_config = get_default_layout_config()
        if self.view:
            self.view.refresh_layout_tree()
            self.view.refresh_preview_image()
            self.view.append_log("Đã khôi phục layout mặc định.")

    # --- TIẾN TRÌNH GENERATE ---
    def start_generation(self) -> None:
        if self.view and self.view.auto_commit_form():
            self.view.append_log("Đã tự động lưu thay đổi trên form trước khi tạo PDF.")

        try:
            template_path = Path(self.app_state.template_var.get())
            output_dir = Path(self.app_state.output_dir_var.get())
            output_name = self.app_state.output_name_var.get().strip() or self.app_state._default_output_name()

            if not self.app_state.records:
                raise ValueError("Chưa có dữ liệu để tạo PDF.")
            if not template_path.is_file():
                raise ValueError("Không tìm thấy file PDF mẫu.")
            output_dir.mkdir(parents=True, exist_ok=True)
            final_name = output_name if output_name.lower().endswith(".pdf") else output_name + ".pdf"
            self.app_state.output_name_var.set(final_name)
            output_path = output_dir / final_name
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(APP_TITLE, str(exc))
            return

        records_snapshot = list(self.app_state.records)
        self.app_state.generated_output_path = None
        
        if self.view:
            self.view.on_generation_start()
            self.view.append_log(f"Bắt đầu tạo PDF: {output_path} ({len(records_snapshot)} dòng)")

        worker = threading.Thread(
            target=self._generate_worker,
            args=(output_path, records_snapshot),
            daemon=True,
        )
        worker.start()

    def _generate_worker(self, output_path: Path, records_snapshot: list[SlipRecord]) -> None:
        def on_progress(current: int, total: int, message: str) -> None:
            self.app_state.event_queue.put(("progress", (current, total, message)))

        try:
            records = generate_pdf_from_records(
                records_snapshot,
                self.app_state.template_var.get(),
                output_path,
                layout_config=self.app_state.layout_config,
                progress_callback=on_progress,
                registry=self.app_state.po_registry,
            )
        except Exception as exc:  # noqa: BLE001
            self.app_state.event_queue.put(("error", str(exc)))
            return
        self.app_state.event_queue.put(("success", (output_path, len(records))))

    # --- UPDATE ---
    def check_for_update(self, automatic: bool = False) -> None:
        if self.app_state.update_check_running:
            return
        try:
            config = load_update_config(self.app_state.paths)
            if automatic and not config["startup_check"]:
                return
            app_root = application_install_root(self.app_state.paths.installation_dir)
            current_version = current_release_version(self.app_state.paths)
        except (ApplicationUpdateError, UpdateDeliveryError, OSError) as exc:
            if not automatic:
                messagebox.showinfo(APP_TITLE, f"Chưa thể kiểm tra cập nhật: {exc}")
            return

        self.app_state.update_check_running = True
        self.app_state.status_var.set("Đang kiểm tra cập nhật...")

        def worker() -> None:
            try:
                candidate = discover_update(self.app_state.paths, current_version=current_version)
                self.app_state.event_queue.put(("update_available", (candidate, app_root, automatic)))
            except Exception as exc:  # noqa: BLE001
                self.app_state.event_queue.put(("update_error", (str(exc), automatic)))

        threading.Thread(target=worker, daemon=True).start()

    def start_update_install(self, candidate, app_root: Path) -> None:
        self.app_state.status_var.set(f"Đang tải và cài cập nhật {candidate.version}...")

        def worker() -> None:
            try:
                package_path = fetch_update(self.app_state.paths, candidate)
                state_data = install_update(
                    package_path,
                    app_root,
                    self.app_state.paths,
                    current_version=current_release_version(self.app_state.paths),
                )
                self.app_state.event_queue.put(("update_success", (state_data, app_root)))
            except Exception as exc:  # noqa: BLE001
                self.app_state.event_queue.put(("update_error", (str(exc), False)))

        threading.Thread(target=worker, daemon=True).start()

    # --- MỞ EXTERNAL RESOURCES ---
    def open_output_folder(self) -> None:
        output_dir = Path(self.app_state.output_dir_var.get())
        output_dir.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(output_dir)

    def open_generated_pdf(self) -> None:
        if not self.app_state.generated_output_path or not self.app_state.generated_output_path.exists():
            messagebox.showwarning(APP_TITLE, "Chưa có file PDF nào vừa được tạo.")
            return
        if sys.platform == "win32":
            os.startfile(self.app_state.generated_output_path)

    def open_build_script(self) -> None:
        script_path = self.app_state.bundle_dir / "build_exe.bat"
        if not script_path.exists():
            messagebox.showwarning(APP_TITLE, "Chưa tìm thấy script build_exe.bat")
            return
        if sys.platform == "win32":
            os.startfile(script_path)

    def open_project_folder(self) -> None:
        folder = self.app_state.bundle_dir if not getattr(sys, "frozen", False) else self.app_state.paths.data_dir
        if sys.platform == "win32":
            os.startfile(folder)

    def on_close(self) -> None:
        self.app_state.po_registry.close()
        if self.view:
            self.view.destroy()
