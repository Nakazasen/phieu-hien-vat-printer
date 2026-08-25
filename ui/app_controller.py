from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

from core.po_registry import FIXED_PO_DETAIL, FIXED_PO_SUB
from core.slip_printer_engine import (
    START_ROW,
    SlipRecord,
    auto_fill_po,
    calculate_total_qty,
    create_record,
    expand_box_sequence,
    generate_pdf_from_records,
    get_default_layout_config,
    load_layout_config,
    normalize_box,
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

    def open_qr_scan_dialog(self) -> None:
        """Open modal dialog for scanning QR, Split (分割) and Return (戻入) operations."""
        from ui.components.qr_scan_dialog import QRScanDialog
        if self.view:
            QRScanDialog(self.view, self)

    def is_tutorial_seen(self) -> bool:
        """Return True if the user has completed or seen the tutorial."""
        if self.view and hasattr(self.view, "_load_tutorial_seen_setting"):
            return self.view._load_tutorial_seen_setting()
        try:
            settings_path = self.app_state.paths.data_dir / "user_settings.json"
            if settings_path.is_file():
                data = json.loads(settings_path.read_text(encoding="utf-8-sig"))
                if isinstance(data, dict):
                    return bool(data.get("has_seen_tutorial", False))
        except Exception:  # noqa: BLE001
            pass
        return False

    def mark_tutorial_seen(self, seen: bool = True) -> None:
        """Mark tutorial as seen/completed in persistent user settings."""
        if self.view and hasattr(self.view, "_save_tutorial_seen_setting"):
            self.view._save_tutorial_seen_setting(seen)
        else:
            try:
                settings_path = self.app_state.paths.data_dir / "user_settings.json"
                data: dict[str, object] = {
                    "appearance_mode": "System",
                    "has_seen_tutorial": bool(seen),
                    "auto_suggest_tutorial": True,
                }
                if settings_path.is_file():
                    try:
                        loaded = json.loads(settings_path.read_text(encoding="utf-8-sig"))
                        if isinstance(loaded, dict):
                            data.update(loaded)
                    except Exception:  # noqa: BLE001
                        pass
                data["has_seen_tutorial"] = bool(seen)
                settings_path.parent.mkdir(parents=True, exist_ok=True)
                payload = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
                temp_path = settings_path.with_suffix(".json.tmp")
                temp_path.write_text(payload, encoding="utf-8")
                try:
                    os.replace(temp_path, settings_path)
                except OSError:
                    settings_path.write_text(payload, encoding="utf-8")
                    temp_path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass

    def get_tutorial_steps(self):
        """Returns the 4-step tutorial script matching the active view or headless state."""
        from ui.components.tutorial_script import build_tutorial_steps
        return build_tutorial_steps(self.view if self.view else None)

    def start_tutorial(self):
        """Launch the tutorial overlay via the view if present."""
        if self.view and hasattr(self.view, "start_tutorial"):
            return self.view.start_tutorial()
        return None


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

    def warn_lot_field_locked(self, _event=None) -> str:
        messagebox.showwarning(
            APP_TITLE,
            "Trường 'Ngày/Lot' được khóa không cho nhập tay để đảm bảo tính chuẩn xác của mã QR.\n\n"
            "👉 Hướng dẫn: Giá trị này sẽ được lấy tự động khi import từ Excel. Nếu bạn tạo tem thủ công và để trống ô này, "
            "phần mềm sẽ tự động điền 10 dấu cách vào mã QR theo đúng tiêu chuẩn.",
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
            raise ValueError("Bạn chưa nhập SL/thùng.")
        if not box:
            raise ValueError("Bạn chưa nhập Số thùng.")
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
            item_code = self.app_state.item_code_var.get().strip()
            item_name = self.app_state.item_name_var.get().strip()
            carton_qty = self.app_state.carton_qty_var.get().strip()
            po = self.app_state.po_var.get().strip()
            box_input = self.app_state.box_var.get().strip()
            rev = self.app_state.rev_var.get().strip()

            if not item_code:
                raise ValueError("Bạn chưa nhập Mã hàng.")
            if not item_name:
                raise ValueError("Bạn chưa nhập Tên hàng.")
            if not carton_qty:
                raise ValueError("Bạn chưa nhập SL/thùng.")
            if not box_input:
                raise ValueError("Bạn chưa nhập Số thùng.")
            validate_revision(rev)

            boxes = expand_box_sequence(box_input)

            if not po:
                po = self.app_state.po_registry.generate_po()
                po_detail = FIXED_PO_DETAIL
                po_sub = FIXED_PO_SUB
                self.app_state.po_var.set(po)
                self.app_state.po_detail_var.set(po_detail)
                self.app_state.po_sub_var.set(po_sub)
            else:
                po_detail = self.app_state.po_detail_var.get().strip() or FIXED_PO_DETAIL
                po_sub = self.app_state.po_sub_var.get().strip() or FIXED_PO_SUB

            start_row = max(r.row_number for r in self.app_state.records) + 1 if self.app_state.records else START_ROW
            new_records: list[SlipRecord] = []
            for idx, b in enumerate(boxes):
                rec = create_record(
                    row_number=start_row + idx,
                    item_code=item_code,
                    item_name=item_name,
                    carton_qty=carton_qty,
                    total_qty=calculate_total_qty(carton_qty, b),
                    po=po,
                    po_detail=po_detail,
                    po_sub=po_sub,
                    box=b,
                    rev=rev,
                    lot=self.app_state.lot_var.get(),
                )
                new_records.append(rec)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Thông tin tem chưa hợp lệ:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra và nhập đầy đủ các trường bắt buộc (*) có dấu sao đỏ trước khi nhấn '➕ Thêm mới'.",
            )
            return

        # Check for duplicate EDI codes against DB and active table (Requirement R3)
        duplicate_items: list[str] = []
        for r in new_records:
            in_db = self.app_state.po_registry.is_registered(r.po, r.po_detail, r.po_sub, r.box)
            in_table = any(
                existing.po == r.po
                and existing.po_detail == r.po_detail
                and existing.po_sub == r.po_sub
                and existing.box == r.box
                for existing in self.app_state.records
            )
            if in_db or in_table:
                location = "trong cơ sở dữ liệu" if in_db else "trong bảng hiện tại"
                duplicate_items.append(f"- PO: {r.po} | Chi tiết: {r.po_detail} | Box: {r.box} ({location})")

        if duplicate_items:
            samples = duplicate_items[:3]
            sample_str = "\n".join(samples)
            more = f"\n... và {len(duplicate_items) - 3} dòng khác." if len(duplicate_items) > 3 else ""
            confirm_msg = (
                f"⚠️ CẢNH BÁO TRÙNG LẶP MÃ EDI:\n"
                f"Mã EDI của {len(duplicate_items)} dòng tem vừa tạo đã tồn tại trong cơ sở dữ liệu chia sẻ (hoặc danh sách hiện tại):\n"
                f"{sample_str}{more}\n\n"
                "👉 Bạn có chắc chắn muốn tiếp tục thêm các dòng này vào danh sách in không?\n"
                "- Chọn 'Yes' (Có): Vẫn thêm vào bảng (dòng sẽ được tô màu ĐỎ để cảnh báo).\n"
                "- Chọn 'No' (Không): Hủy bỏ thao tác thêm mới."
            )
            if not messagebox.askyesno(APP_TITLE, confirm_msg):
                if self.view:
                    self.view.append_log("Đã hủy thêm mới do phát hiện trùng mã EDI.")
                return

        self.app_state.records.extend(new_records)
        if self.view:
            if len(new_records) == 1:
                self.view.append_log(f"Đã thêm dòng {new_records[0].row_number}: {new_records[0].item_code}")
            else:
                self.view.append_log(
                    f"Đã thêm {len(new_records)} dòng tem (Box {new_records[0].box} - {new_records[-1].box}): {item_code} (PO: {po})"
                )
            self.view.set_records(self.app_state.records, select_index=len(self.app_state.records) - 1)

    def update_selected_record(self) -> None:
        if not self.app_state.records:
            messagebox.showwarning(
                APP_TITLE,
                "Danh sách hiện đang trống, chưa có dòng nào để cập nhật.\n\n"
                "👉 Hướng dẫn: Vui lòng nhập thông tin vào form và nhấn '➕ Thêm mới' hoặc nhấn 'Import từ Excel' để tải dữ liệu vào bảng trước.",
            )
            return

        try:
            row_number = self.app_state.records[self.app_state.selected_record_index].row_number
            record = self._collect_form_record(row_number=row_number)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Không thể cập nhật dòng dữ liệu:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra lại các trường thông tin trên form (Mã hàng, Tên hàng, Số lượng, Số box, Rev) và thử lại.",
            )
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
        count = len(self.app_state.records)
        if self.app_state.records and not messagebox.askyesno(
            APP_TITLE,
            f"Bạn có chắc chắn muốn xóa toàn bộ {count} dòng dữ liệu hiện tại trong bảng không?\n\n"
            "👉 Lưu ý: Thao tác này sẽ làm trống bảng dữ liệu và không thể hoàn tác.",
        ):
            return
        self.app_state.records = []
        if self.view:
            self.view.set_records(self.app_state.records, select_index=None)
            self.view.append_log("Đã xóa toàn bộ dữ liệu trong app.")

    def import_from_excel(self) -> None:
        excel_path = self.app_state.excel_var.get().strip()
        if not excel_path:
            messagebox.showwarning(
                APP_TITLE,
                "Chưa chọn đường dẫn file Excel để import.\n\n"
                "👉 Hướng dẫn: Vui lòng nhấn nút 'Chọn' tại mục 'File Excel' ở thanh bên trái để chọn file (.xlsx), sau đó nhấn lại nút 'Import từ Excel'.",
            )
            return

        try:
            records = read_records(excel_path)
            for index, record in enumerate(records, start=1):
                try:
                    validate_revision(record.rev)
                except ValueError as exc:
                    raise ValueError(f"Dòng Excel {index}: {exc}") from exc
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Không thể đọc dữ liệu từ file Excel:\n{exc}\n\n"
                "👉 Hướng dẫn kiểm tra:\n"
                "1. Đảm bảo file Excel đúng cấu trúc mẫu (dữ liệu bắt đầu từ dòng 4).\n"
                "2. Đóng file Excel nếu đang mở trong ứng dụng khác.\n"
                "3. Đảm bảo cột Rev là 2 chữ số (từ 01 đến 99).",
            )
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
                messagebox.showerror(
                    APP_TITLE,
                    f"Lỗi trong quá trình tự động sinh số PO cho các dòng thiếu PO:\n{exc}\n\n"
                    "👉 Hướng dẫn: Vui lòng kiểm tra kết nối mạng tới cơ sở dữ liệu chia sẻ hoặc điền sẵn số PO vào file Excel trước khi import.",
                )
                if self.view:
                    self.view.append_log(f"Lỗi sinh PO tự động: {exc}")
                return

        duplicate_records: list[SlipRecord] = []
        for r in records:
            po = r.po.strip()
            if po:
                po_detail = r.po_detail.strip() or FIXED_PO_DETAIL
                po_sub = r.po_sub.strip() or FIXED_PO_SUB
                box = r.box.strip()
                if self.app_state.po_registry.is_registered(po, po_detail, po_sub, box):
                    duplicate_records.append(r)

        if duplicate_records:
            samples = [
                f"Dòng {r.row_number}: PO={r.po}, Box={r.box}"
                for r in duplicate_records[:3]
            ]
            sample_str = "\n".join(f"- {s}" for s in samples)
            more = f"\n... và {len(duplicate_records) - 3} dòng khác." if len(duplicate_records) > 3 else ""
            warning_msg = (
                f"⚠️ CẢNH BÁO TRÙNG LẶP MÃ EDI:\n"
                f"Phát hiện {len(duplicate_records)} dòng có mã EDI đã tồn tại trong cơ sở dữ liệu chia sẻ:\n"
                f"{sample_str}{more}\n\n"
                "👉 Hướng dẫn xử lý:\n"
                "- Các dòng bị trùng đã được bôi màu ĐỎ trên bảng dữ liệu để bạn dễ nhận biết.\n"
                "- Toàn bộ dữ liệu vẫn được nạp vào bảng để bạn kiểm tra.\n"
                "- Vui lòng chọn dòng màu đỏ và nhấn 'Xóa dòng' hoặc đổi lại số Box / số PO cho hợp lệ trước khi nhấn 'Tạo PDF'."
            )
            messagebox.showwarning(APP_TITLE, warning_msg)
            if self.view:
                self.view.append_log(f"Cảnh báo: Phát hiện {len(duplicate_records)} dòng trùng mã EDI trong database.")

        self.app_state.records = list(records)
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
            messagebox.showerror(
                APP_TITLE,
                f"Không thể dịch chuyển vị trí phần tử layout:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng chọn một phần tử trong danh sách và kiểm tra tọa độ X, Y có hợp lệ không.",
            )

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
            messagebox.showerror(
                APP_TITLE,
                f"Không thể thay đổi kích thước phần tử layout:\n{exc}\n\n"
                "👉 Hướng dẫn: Kích thước chiều rộng và chiều cao tối thiểu là 5.0 mm.",
            )

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
            messagebox.showerror(
                APP_TITLE,
                f"Tọa độ hoặc kích thước nhập vào không hợp lệ:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng nhập đúng định dạng số thực (ví dụ: 15.0, 24.5) cho các ô tọa độ X, Y, Chiều rộng, Chiều cao.",
            )
            return

        if self.view:
            self.view.refresh_layout_tree(select_id=item_id)
            self.view.refresh_preview_image()
            self.view.append_log(f"Đã cập nhật layout: {item_id}")

    def save_layout_config_to_disk(self) -> None:
        save_layout_config(self.app_state.layout_config, self.app_state.layout_path)
        if self.view:
            self.view.append_log(f"Đã lưu cấu hình layout: {self.app_state.layout_path}")
        messagebox.showinfo(
            APP_TITLE,
            f"Đã lưu thành công cấu hình layout vào file:\n{self.app_state.layout_path}\n\n"
            "👉 Cấu hình vị trí này sẽ được tự động ghi nhớ và áp dụng cho các lần in tiếp theo.",
        )

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
            messagebox.showerror(
                APP_TITLE,
                f"Không thể bắt đầu tạo file PDF:\n{exc}\n\n"
                "👉 Hướng dẫn:\n"
                "- Nếu chưa có dữ liệu: Vui lòng thêm dữ liệu vào bảng trước.\n"
                "- Nếu thiếu PDF mẫu: Vui lòng chọn file template.pdf hợp lệ tại thanh bên trái.",
            )
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
                messagebox.showinfo(
                    APP_TITLE,
                    f"Không thể kết nối để kiểm tra bản cập nhật:\n{exc}\n\n"
                    "👉 Hướng dẫn: Vui lòng kiểm tra lại kết nối mạng nội bộ của máy tính hoặc thử lại sau.",
                )
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
            messagebox.showwarning(
                APP_TITLE,
                "Chưa có file PDF nào được tạo trong phiên làm việc này.\n\n"
                "👉 Hướng dẫn: Vui lòng nhấn nút 'Tạo PDF' để xuất file trước khi thực hiện mở file.",
            )
            return
        if sys.platform == "win32":
            os.startfile(self.app_state.generated_output_path)

    def open_build_script(self) -> None:
        script_path = self.app_state.bundle_dir / "build_exe.bat"
        if not script_path.exists():
            messagebox.showwarning(
                APP_TITLE,
                "Không tìm thấy file kịch bản 'build_exe.bat' trong thư mục ứng dụng.\n\n"
                "👉 Lưu ý: Chức năng này chỉ khả dụng trong môi trường phát triển mã nguồn.",
            )
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
