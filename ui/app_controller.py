from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import replace
from pathlib import Path
from tkinter import filedialog, messagebox

from core.error_logger import log_error_event
from core.part_master import (
    InspectionCSVData,
    InspectionCSVError,
    _find_inspection_csv_with_context,
    collect_inspection_diagnostics,
    find_inspection_csv_file,
    format_cav_list,
    get_inspection_data_root,
    load_cav_from_inspection_source,
    parse_inspection_csv,
    parse_manual_cav_input,
)
from core.po_registry import (
    FIXED_PO_DETAIL,
    FIXED_PO_SUB,
    DuplicateComboError,
    OfflinePOGenerationBlockedError,
)
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
    validate_records,
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


def format_error_for_user(error: BaseException | str, action: str) -> str:
    """Return a concise Vietnamese detail instead of exposing raw OS/library text."""
    detail = str(error).strip()
    vietnamese_marks = "àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđĐ"
    if isinstance(error, FileNotFoundError):
        return "Không tìm thấy tệp hoặc thư mục cần thiết. Vui lòng kiểm tra lại đường dẫn."
    if isinstance(error, PermissionError):
        return "Không có quyền truy cập tệp hoặc thư mục. Hãy đóng tệp đang mở hoặc chọn nơi lưu khác."
    if isinstance(error, IsADirectoryError):
        return "Đường dẫn đang trỏ tới thư mục thay vì tệp. Vui lòng chọn đúng tệp cần dùng."
    if isinstance(error, TimeoutError):
        return "Kết nối phản hồi quá lâu. Vui lòng kiểm tra mạng rồi thử lại."
    if isinstance(error, ConnectionError):
        return "Không thể kết nối tới dịch vụ cần thiết. Vui lòng kiểm tra mạng rồi thử lại."
    if isinstance(error, OSError):
        if getattr(error, "winerror", None) == 32 or getattr(error, "errno", None) == 13:
            return "Tệp đang được ứng dụng khác sử dụng hoặc không có quyền truy cập. Hãy đóng tệp rồi thử lại."
    if any(char in vietnamese_marks for char in detail):
        return detail
    return f"Không thể {action}. Vui lòng kiểm tra lại thông tin, đường dẫn hoặc kết nối rồi thử lại."


class AppController:
    def __init__(self, state: AppState):
        self.app_state = state
        self.view = None  # Cần gọi set_view(view) sau khi khởi tạo view
        self._last_auto_po: str | None = None
        self._last_added_item_code: str | None = None
        self._last_resolved_cav_item_code: str = ""
        self._last_resolved_cav_not_found: bool = False
        self._last_found_csv_path: Path | None = None
        self._last_csv_lookup_error: str = ""
        self._cav_cache: dict[
            tuple[str, str, str],
            tuple[float, list[int], InspectionCSVData | None, str, Path | None, str],
        ] = {}
        self._cav_cache_ttl_seconds: float = 30.0

    def clear_cav_cache(self) -> None:
        """Invalidate the in-memory CAV resolution cache."""
        self._cav_cache.clear()

    def _app_version_str(self) -> str:
        try:
            return current_release_version(self.app_state.paths)
        except Exception:  # noqa: BLE001
            return "unknown"

    def set_view(self, view):
        self.view = view

    def open_qr_scan_dialog(self) -> None:
        """Open modal dialog for scanning QR, Split (分割) and Return (戻入) operations."""
        from ui.components.qr_scan_dialog import QRScanDialog
        if self.view:
            QRScanDialog(self.view, self)

    def on_paper_size_changed(self, target_size: str) -> None:
        """Handle paper size selection change between A4 and Letter."""
        target = target_size.strip()
        if target.lower() == "letter":
            from ui.components.letter_warning_dialog import LetterWarningDialog

            def _on_confirm() -> None:
                self.app_state.paper_size_var.set("Letter")
                if self.view and hasattr(self.view, "_save_paper_size_setting"):
                    self.view._save_paper_size_setting("Letter")
                if self.view and hasattr(self.view, "sidebar"):
                    self.view.sidebar.sync_paper_size_ui()
                if self.view and hasattr(self.view, "data_tab"):
                    self.view.data_tab.set_records(select_index=self.app_state.selected_record_index)
                if self.view:
                    self.view.append_log("Đã chọn khổ giấy: Letter (In 4 tem/trang, 100% không co hình, khe hở 5.0mm).")

            def _on_cancel() -> None:
                self.app_state.paper_size_var.set("A4")
                if self.view and hasattr(self.view, "sidebar"):
                    self.view.sidebar.sync_paper_size_ui()
                if self.view and hasattr(self.view, "data_tab"):
                    self.view.data_tab.set_records(select_index=self.app_state.selected_record_index)
                if self.view:
                    self.view.append_log("Đã hủy chuyển sang Letter, tiếp tục dùng khổ A4 chuẩn (6 tem/trang).")

            if self.view:
                LetterWarningDialog(self.view, on_confirm=_on_confirm, on_cancel=_on_cancel)
            else:
                _on_confirm()
        else:
            self.app_state.paper_size_var.set("A4")
            if self.view and hasattr(self.view, "_save_paper_size_setting"):
                self.view._save_paper_size_setting("A4")
            if self.view and hasattr(self.view, "sidebar"):
                self.view.sidebar.sync_paper_size_ui()
            if self.view and hasattr(self.view, "data_tab"):
                self.view.data_tab.set_records(select_index=self.app_state.selected_record_index)
            if self.view:
                self.view.append_log("Đã chọn khổ giấy: A4 chuẩn (In 6 tem/trang, 100% không co hình, khe hở 5.0mm).")

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
            title="Chọn tệp Excel để nhập dữ liệu",
            filetypes=[("Tệp Excel", "*.xlsx"), ("Tất cả tệp", "*.*")],
            initialdir=self._existing_parent(self.app_state.excel_var.get()),
        )
        if selected:
            self.app_state.excel_var.set(selected)

    def pick_template_pdf(self) -> None:
        selected = filedialog.askopenfilename(
            title="Chọn tệp PDF mẫu",
            filetypes=[("Tệp PDF", "*.pdf"), ("Tất cả tệp", "*.*")],
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
            "👉 Hướng dẫn: Giá trị này sẽ được lấy tự động khi nhập từ Excel. Nếu bạn tạo tem thủ công và để trống ô này, "
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
        cav_no = self._resolve_active_cav_for_form(item_code=item_code, rev=rev)
        self.app_state.cav_var.set(cav_no)

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
            cav_no=cav_no,
        )

        if not record.po.strip():
            filled = auto_fill_po([record], self.app_state.po_registry)
            record = filled[0]
            self.app_state.po_var.set(record.po)
            self.app_state.po_detail_var.set(record.po_detail)
            self.app_state.po_sub_var.set(record.po_sub)

        return record

    def _build_records_diagnostics(self, records: list[SlipRecord] | None = None) -> dict[str, Any]:
        """Build a concise diagnostic snapshot of a record list for operational logs."""
        target = list(records) if records is not None else list(getattr(self.app_state, "records", []))
        unique_pos = sorted({r.po.strip() for r in target if r.po.strip()})
        unique_items = sorted({r.item_code.strip() for r in target if r.item_code.strip()})
        samples = [
            {
                "row": r.row_number,
                "item_code": r.item_code,
                "po": r.po,
                "po_detail": r.po_detail,
                "po_sub": r.po_sub,
                "box": r.box,
                "rev": r.rev,
                "cav_no": getattr(r, "cav_no", ""),
            }
            for r in target[:12]
        ]
        return {
            "record_count": len(target),
            "unique_pos": unique_pos,
            "unique_items": unique_items,
            "sample_rows": samples,
        }

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
            cav_no = self._resolve_active_cav_for_form(item_code=item_code, rev=rev)
            self.app_state.cav_var.set(cav_no)

            boxes = expand_box_sequence(box_input)

            po_from_form = self.app_state.po_var.get().strip()
            is_manual_override = getattr(self.app_state, "manual_po_override", False)

            needs_auto_po = False
            if not po_from_form:
                needs_auto_po = True
            elif not is_manual_override:
                last_auto = getattr(self, "_last_auto_po", None)
                last_item = getattr(self, "_last_added_item_code", None)
                leaked_from_record = any(
                    r.po.strip() == po_from_form and r.item_code.strip() != item_code
                    for r in self.app_state.records
                )
                leaked_from_last = bool(last_auto and po_from_form == last_auto and item_code != last_item)
                already_exported_auto = bool(
                    last_auto
                    and po_from_form == last_auto
                    and any(
                        self.app_state.po_registry.is_registered(po_from_form, FIXED_PO_DETAIL, FIXED_PO_SUB, b)
                        for b in boxes
                    )
                )
                if leaked_from_record or leaked_from_last or already_exported_auto:
                    needs_auto_po = True

            if needs_auto_po:
                po = self.app_state.po_registry.generate_po()
                po_detail = FIXED_PO_DETAIL
                po_sub = FIXED_PO_SUB
                self._last_auto_po = po
                self.app_state.po_var.set(po)
                self.app_state.po_detail_var.set(po_detail)
                self.app_state.po_sub_var.set(po_sub)
            else:
                po = po_from_form
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
                    cav_no=cav_no,
                )
                new_records.append(rec)
        except OfflinePOGenerationBlockedError as exc:
            messagebox.showerror(
                APP_TITLE,
                f"Không thể tự động sinh số PO:\n{format_error_for_user(exc, 'tạo số PO')}\n\n"
                "👉 Hướng dẫn:\n"
                "- Do mất kết nối cơ sở dữ liệu LAN dùng chung, tính năng tự sinh số PO đã bị khóa để tránh trùng lặp.\n"
                "- Vui lòng kiểm tra lại dây mạng LAN hoặc bấm nút '🔓' bên cạnh ô PO để nhập số PO thủ công do Quản lý cấp.",
            )
            return
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Thông tin tem chưa hợp lệ:\n{format_error_for_user(exc, 'thêm tem')}\n\n"
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
            user_confirmed_dup = bool(messagebox.askyesno(APP_TITLE, confirm_msg))
            log_error_event(
                "ADD_RECORD_DUPLICATE_WARNING",
                f"Cảnh báo trùng mã EDI khi thêm mới {len(new_records)} dòng cho mã '{item_code}' (PO: {po}). Người dùng chọn: {'Tiếp tục thêm' if user_confirmed_dup else 'Hủy'}.",
                item_code=item_code,
                diagnostics={
                    "po": po,
                    "duplicate_count": len(duplicate_items),
                    "duplicate_samples": duplicate_items[:10],
                    "user_confirmed": user_confirmed_dup,
                    "active_table": self._build_records_diagnostics(self.app_state.records),
                },
                app_version=self._app_version_str(),
            )
            if not user_confirmed_dup:
                if self.view:
                    self.view.append_log("Đã hủy thêm mới do phát hiện trùng mã EDI.")
                return

        self.app_state.records.extend(new_records)
        log_error_event(
            "ADD_RECORD",
            f"Đã thêm {len(new_records)} dòng tem vào bảng (Mã: {item_code}, PO: {po}, Box: {new_records[0].box}..{new_records[-1].box}). Tổng số dòng trên bảng: {len(self.app_state.records)}.",
            item_code=item_code,
            diagnostics={
                "added_count": len(new_records),
                "po": po,
                "po_detail": po_detail,
                "po_sub": po_sub,
                "box_start": new_records[0].box,
                "box_end": new_records[-1].box,
                "rev": rev,
                "cav_no": cav_no,
                "active_table": self._build_records_diagnostics(self.app_state.records),
            },
            app_version=self._app_version_str(),
        )
        if (
            hasattr(self.app_state, "part_master")
            and item_code
            and item_name
            and rev
            and not self.is_inspection_source_available()
        ):
            try:
                cav_to_save = format_cav_list(self.app_state.valid_cavs) if self.app_state.valid_cavs else None
                self.app_state.part_master.upsert(
                    item_code, item_name, rev, cav_list=cav_to_save, carton_qty=carton_qty
                )
            except ValueError:
                pass

        self._last_added_item_code = item_code
        self.app_state.po_var.set(po)
        self.app_state.po_detail_var.set(po_detail)
        self.app_state.po_sub_var.set(po_sub)

        if self.view:
            if hasattr(self.view, "append_log"):
                if len(new_records) == 1:
                    self.view.append_log(f"Đã thêm dòng {new_records[0].row_number}: {new_records[0].item_code}")
                else:
                    self.view.append_log(
                        f"Đã thêm {len(new_records)} dòng tem (Box {new_records[0].box} - {new_records[-1].box}): {item_code} (PO: {po})"
                    )
            if hasattr(self.view, "set_records"):
                self.view.set_records(self.app_state.records, select_index=len(self.app_state.records) - 1)

    def update_selected_record(self) -> None:
        if not self.app_state.records:
            messagebox.showwarning(
                APP_TITLE,
                "Danh sách hiện đang trống, chưa có dòng nào để cập nhật.\n\n"
                "👉 Hướng dẫn: Vui lòng nhập thông tin vào biểu mẫu và nhấn '➕ Thêm mới' hoặc nhấn 'Nhập từ Excel' để tải dữ liệu vào bảng trước.",
            )
            return

        try:
            row_number = self.app_state.records[self.app_state.selected_record_index].row_number
            record = self._collect_form_record(row_number=row_number)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Không thể cập nhật dòng dữ liệu:\n{format_error_for_user(exc, 'cập nhật dòng dữ liệu')}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra lại các trường thông tin trên biểu mẫu (Mã hàng, Tên hàng, Số lượng, Số box, Rev) và thử lại.",
            )
            return

        self.app_state.records[self.app_state.selected_record_index] = record
        if (
            hasattr(self.app_state, "part_master")
            and record.item_code
            and record.item_name
            and record.rev
            and not self.is_inspection_source_available()
        ):
            try:
                cav_to_save = format_cav_list(self.app_state.valid_cavs) if self.app_state.valid_cavs else None
                self.app_state.part_master.upsert(
                    record.item_code,
                    record.item_name,
                    record.rev,
                    cav_list=cav_to_save,
                    carton_qty=record.carton_qty,
                )
            except ValueError:
                pass
        if self.view:
            self.view.append_log(f"Đã cập nhật dòng {record.row_number}: {record.item_code}")
            self.view.set_records(self.app_state.records, select_index=self.app_state.selected_record_index)

    def delete_selected_record(self, require_confirm: bool = False) -> None:
        if not self.app_state.records:
            return
        idx = self.app_state.selected_record_index
        if idx < 0 or idx >= len(self.app_state.records):
            return
        record = self.app_state.records[idx]
        if require_confirm:
            if not messagebox.askyesno(
                "Xác nhận xóa tem",
                f"Bạn có chắc muốn xóa dòng {record.row_number} (Mã hàng: {record.item_code}) khỏi bảng không?\n\n"
                "👉 Thao tác xóa sẽ loại bỏ tem này khỏi danh sách in.",
            ):
                return
        record = self.app_state.records.pop(idx)
        if self.view:
            self.view.append_log(f"Đã xóa dòng {record.row_number}: {record.item_code}")
            next_index = min(idx, len(self.app_state.records) - 1) if self.app_state.records else None
            self.view.set_records(self.app_state.records, select_index=next_index)

    def clear_all_records(self) -> None:
        count = len(self.app_state.records)
        if self.app_state.records and not messagebox.askyesno(
            APP_TITLE,
            f"Bạn có chắc chắn muốn xóa toàn bộ {count} dòng dữ liệu hiện tại trong bảng không?\n\n"
            "👉 Lưu ý: Thao tác này sẽ làm trống bảng dữ liệu và không thể hoàn tác.",
        ):
            return
        cleared_snapshot = self._build_records_diagnostics(self.app_state.records)
        self.app_state.records = []
        self._last_auto_po = None
        if not getattr(self.app_state, "manual_po_override", False):
            self.app_state.po_var.set("")
            self.app_state.po_detail_var.set("")
            self.app_state.po_sub_var.set("")
        log_error_event(
            "CLEAR_ALL_RECORDS",
            f"Người dùng đã xóa toàn bộ {count} dòng tem khỏi bảng danh sách chờ in.",
            diagnostics={"cleared_count": count, "cleared_records": cleared_snapshot},
            app_version=self._app_version_str(),
        )
        if self.view:
            self.view.set_records(self.app_state.records, select_index=None)
            self.view.append_log("Đã xóa toàn bộ dữ liệu trong app.")

    def import_from_excel(self) -> None:
        excel_path = self.app_state.excel_var.get().strip()
        if not excel_path:
            messagebox.showwarning(
                APP_TITLE,
                "Chưa chọn đường dẫn tệp Excel để nhập dữ liệu.\n\n"
                "👉 Hướng dẫn: Vui lòng nhấn nút 'Chọn' tại mục 'Tệp Excel' ở thanh bên trái để chọn tệp (.xlsx), sau đó nhấn lại nút 'Nhập từ Excel'.",
            )
            return

        try:
            records = read_records(excel_path)
            for index, record in enumerate(records, start=1):
                try:
                    validate_revision(record.rev)
                except ValueError as exc:
                    raise ValueError(
                        f"Dòng Excel {index}: {format_error_for_user(exc, 'đọc dữ liệu trong dòng Excel')}"
                    ) from exc
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Không thể đọc dữ liệu từ tệp Excel:\n{format_error_for_user(exc, 'đọc dữ liệu từ tệp Excel')}\n\n"
                "👉 Hướng dẫn kiểm tra:\n"
                "1. Đảm bảo tệp Excel đúng cấu trúc mẫu (dữ liệu bắt đầu từ dòng 4).\n"
                "2. Đóng tệp Excel nếu đang mở trong ứng dụng khác.\n"
                "3. Đảm bảo cột Rev là 2 chữ số (từ 01 đến 99).",
            )
            if self.view:
                self.view.append_log(f"Lỗi nhập dữ liệu Excel: {format_error_for_user(exc, 'đọc tệp Excel')}")
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
                    f"Lỗi trong quá trình tự động sinh số PO cho các dòng thiếu PO:\n{format_error_for_user(exc, 'tạo số PO')}\n\n"
                    "👉 Hướng dẫn: Vui lòng kiểm tra kết nối mạng tới cơ sở dữ liệu chia sẻ hoặc điền sẵn số PO vào tệp Excel trước khi nhập.",
                )
                if self.view:
                    self.view.append_log(f"Lỗi sinh PO tự động: {format_error_for_user(exc, 'tạo số PO')}")
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

        enriched_records: list[SlipRecord] = []
        rev_mismatch_notes: list[str] = []
        csv_warning_notes: list[str] = []
        seen_csv_warning_codes: set[str] = set()
        latest_csv_by_code: dict[str, InspectionCSVData | None] = {}

        for r in records:
            c_code = r.item_code.strip().upper()
            c_rev = r.rev.strip()
            cav_str = getattr(r, "cav_no", "").strip()
            rev_csv: InspectionCSVData | None = None
            latest_csv: InspectionCSVData | None = None
            if c_code:
                valid_cavs, rev_csv, _src = self.resolve_cav_for_item(c_code, preferred_rev=c_rev)
                if not cav_str and valid_cavs:
                    cav_str = format_cav_list(valid_cavs)
                    r = replace(r, cav_no=cav_str)

                if rev_csv is not None:
                    if c_code in latest_csv_by_code:
                        latest_csv = latest_csv_by_code[c_code]
                    elif rev_csv.is_from_old_archive or len(rev_csv.active_revisions) > 1:
                        _, latest_csv, _ = self.resolve_cav_for_item(c_code, preferred_rev=None)
                        latest_csv_by_code[c_code] = latest_csv
                    else:
                        latest_csv = rev_csv
                        latest_csv_by_code[c_code] = latest_csv

                    if latest_csv is not None and c_rev and c_rev != latest_csv.revision:
                        archive_tag = (
                            f" [đã lấy CAV từ bản lưu 'old/{rev_csv.file_path.name}']"
                            if (rev_csv.is_from_old_archive and rev_csv.revision == c_rev)
                            else ""
                        )
                        rev_mismatch_notes.append(
                            f"Dòng {r.row_number} ({c_code}): Excel ghi Rev {c_rev}, "
                            f"nhưng Server QC hiện tại là Rev {latest_csv.revision} "
                            f"(file {latest_csv.file_path.name}, Ver {latest_csv.version}){archive_tag}"
                        )
                    if latest_csv is not None and latest_csv.warnings and c_code not in seen_csv_warning_codes:
                        seen_csv_warning_codes.add(c_code)
                        for w in latest_csv.warnings:
                            csv_warning_notes.append(f"Mã {c_code}: {w}")
            enriched_records.append(r)
        records = enriched_records

        if rev_mismatch_notes or csv_warning_notes:
            sections: list[str] = []
            if rev_mismatch_notes:
                samples = rev_mismatch_notes[:5]
                more = (
                    f"\n... và {len(rev_mismatch_notes) - 5} dòng lệch Revision khác."
                    if len(rev_mismatch_notes) > 5
                    else ""
                )
                sections.append(
                    f"Phát hiện {len(rev_mismatch_notes)} dòng trong Excel có Revision khác với bản mới nhất trên Server QC:\n"
                    + "\n".join(f"- {s}" for s in samples)
                    + more
                )
            if csv_warning_notes:
                w_samples = csv_warning_notes[:3]
                sections.append(
                    "Cảnh báo dữ liệu CSV trên Server QC:\n"
                    + "\n".join(f"- {w}" for w in w_samples)
                )
            rev_warn_msg = (
                "⚠️ CẢNH BÁO LỆCH REVISION / PHIÊN BẢN DỮ LIỆU CSV QC:\n\n"
                + "\n\n".join(sections)
                + "\n\n👉 Hướng dẫn xử lý:\n"
                "- Nếu đang in bù hàng tồn kho của Revision cũ (running change), hãy kiểm tra kỹ đúng lô hàng thực tế.\n"
                "- Nếu linh kiện đã nâng lên Revision mới, vui lòng cập nhật lại cột Rev trong Excel hoặc sửa trực tiếp trên biểu mẫu trước khi in!"
            )
            messagebox.showwarning(APP_TITLE, rev_warn_msg)
            if self.view:
                for note in rev_mismatch_notes:
                    self.view.append_log(f"⚠️ Cảnh báo lệch Rev Excel vs Server QC: {note}")
                for w_note in csv_warning_notes:
                    self.view.append_log(f"⚠️ Cảnh báo CSV QC: {w_note}")

        self.app_state.records = list(records)
        log_error_event(
            "EXCEL_IMPORT",
            f"Đã nhập {len(records)} dòng từ Excel '{excel_path}' (tự sinh PO: {empty_po_count}, trùng DB: {len(duplicate_records)}, lệch Rev: {len(rev_mismatch_notes)}).",
            diagnostics={
                "excel_path": excel_path,
                "imported_count": len(records),
                "auto_filled_po_count": empty_po_count,
                "duplicate_count": len(duplicate_records),
                "rev_mismatch_count": len(rev_mismatch_notes),
                "records_summary": self._build_records_diagnostics(records),
            },
            app_version=self._app_version_str(),
        )
        if hasattr(self.app_state, "part_master"):
            inspection_online = self.is_inspection_source_available()
            for r in records:
                try:
                    c_code = r.item_code.strip().upper()
                    c_name = r.item_name.strip()
                    c_rev = r.rev.strip()
                    latest_csv = latest_csv_by_code.get(c_code)
                    if latest_csv is not None:
                        self.app_state.part_master.upsert(
                            latest_csv.item_code,
                            latest_csv.item_name.strip().upper() or c_name,
                            latest_csv.revision,
                            cav_list=latest_csv.cav_text,
                            carton_qty=latest_csv.pcs_per_box,
                        )
                    elif not inspection_online and c_code and c_name and c_rev:
                        self.app_state.part_master.upsert(c_code, c_name, c_rev)
                except ValueError:
                    pass
        if self.view:
            self.view.set_records(records, select_index=0, source=f"Đã nhập {len(records)} dòng từ Excel: {excel_path}")

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
                f"Không thể dịch chuyển vị trí phần tử bố cục:\n{format_error_for_user(exc, 'dịch chuyển phần tử bố cục')}\n\n"
                "👉 Hướng dẫn: Vui lòng chọn một phần tử trong danh sách và kiểm tra tọa độ X, Y có hợp lệ không.",
            )

    def resize_layout(self, d_width: float, d_height: float) -> None:
        item_id = self.app_state.layout_choice_var.get()
        if not item_id:
            return
        try:
            w_str = self.app_state.width_var.get().strip()
            h_str = self.app_state.height_var.get().strip()
            is_barcode = "barcode" in item_id.lower() or item_id in self.app_state.layout_config.get("barcode_positions", {})
            if is_barcode:
                if w_str and d_width != 0:
                    step = 0.05 if d_width > 0 else -0.05
                    new_w = max(0.1, round(float(w_str) + step, 2))
                    self.app_state.width_var.set(str(new_w))
                if h_str and d_height != 0:
                    step_h = 1.0 if d_height > 0 else -1.0
                    new_h = max(2.0, round(float(h_str) + step_h, 1))
                    self.app_state.height_var.set(str(new_h))
            else:
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
                f"Không thể thay đổi kích thước phần tử bố cục:\n{format_error_for_user(exc, 'thay đổi kích thước phần tử bố cục')}\n\n"
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
                f"Tọa độ hoặc kích thước nhập vào không hợp lệ:\n{format_error_for_user(exc, 'cập nhật bố cục')}\n\n"
                "👉 Hướng dẫn: Vui lòng nhập đúng định dạng số thực (ví dụ: 15.0, 24.5) cho các ô tọa độ X, Y, Chiều rộng, Chiều cao.",
            )
            return

        if self.view:
            self.view.refresh_layout_tree(select_id=item_id)
            self.view.refresh_preview_image()
            self.view.append_log(f"Đã cập nhật bố cục: {item_id}")

    def save_layout_config_to_disk(self) -> None:
        save_layout_config(self.app_state.layout_config, self.app_state.layout_path)
        if self.view:
            self.view.append_log(f"Đã lưu cấu hình bố cục: {self.app_state.layout_path}")
        messagebox.showinfo(
            APP_TITLE,
            f"Đã lưu thành công cấu hình bố cục vào tệp:\n{self.app_state.layout_path}\n\n"
            "👉 Cấu hình vị trí này sẽ được tự động ghi nhớ và áp dụng cho các lần in tiếp theo.",
        )

    def on_layout_option_changed(self) -> None:
        """Handle toggle changes for new template display options."""
        if "options" not in self.app_state.layout_config:
            self.app_state.layout_config["options"] = {}
        is_hide_total = self.app_state.opt_hide_total_qty_var.get()
        is_hide_pkg = self.app_state.opt_hide_package_qty_var.get()
        self.app_state.layout_config["options"]["hide_total_qty_on_slip"] = is_hide_total
        self.app_state.layout_config["options"]["hide_package_qty_box"] = is_hide_pkg
        save_layout_config(self.app_state.layout_config, self.app_state.layout_path)
        if self.view:
            if hasattr(self.view, "layout_tab") and hasattr(self.view.layout_tab, "sync_option_ui"):
                self.view.layout_tab.sync_option_ui()
            self.view.refresh_preview_image()
            msg = f"Đã lưu tùy chọn tem: [SL: {'Chỉ in 1 thùng' if is_hide_total else 'In kèm tổng SL'}] | [PACKAGE QTY: {'Ẩn' if is_hide_pkg else 'Hiện'}]"
            self.view.append_log(msg)

    def reload_layout_config(self) -> None:
        self.app_state.layout_config = load_layout_config(self.app_state.layout_path)
        opts = self.app_state.layout_config.get("options", {})
        self.app_state.opt_hide_total_qty_var.set(bool(opts.get("hide_total_qty_on_slip", True)))
        self.app_state.opt_hide_package_qty_var.set(bool(opts.get("hide_package_qty_box", True)))
        if self.view:
            self.view.refresh_layout_tree()
            if hasattr(self.view, "layout_tab") and hasattr(self.view.layout_tab, "sync_option_ui"):
                self.view.layout_tab.sync_option_ui()
            self.view.refresh_preview_image()
            self.view.append_log("Đã nạp lại cấu hình bố cục từ tệp.")

    def reset_layout_config(self) -> None:
        self.app_state.layout_config = get_default_layout_config()
        opts = self.app_state.layout_config.get("options", {})
        self.app_state.opt_hide_total_qty_var.set(bool(opts.get("hide_total_qty_on_slip", True)))
        self.app_state.opt_hide_package_qty_var.set(bool(opts.get("hide_package_qty_box", True)))
        save_layout_config(self.app_state.layout_config, self.app_state.layout_path)
        if self.view:
            self.view.refresh_layout_tree()
            if hasattr(self.view, "layout_tab") and hasattr(self.view.layout_tab, "sync_option_ui"):
                self.view.layout_tab.sync_option_ui()
            self.view.refresh_preview_image()
            self.view.append_log("Đã khôi phục bố cục mặc định.")

    # --- TIẾN TRÌNH GENERATE ---
    def start_generation(self) -> None:
        if hasattr(self.app_state, "split_cav_var") and self.app_state.split_cav_var.get() and not self.app_state.selected_cavs:
            messagebox.showerror(
                APP_TITLE,
                "Đang bật 'Tách CAV' nhưng chưa chọn CAV nào.\n\n"
                "👉 Hướng dẫn: Vui lòng chọn ít nhất một CAV hợp lệ hoặc tắt 'Tách CAV' trước khi tạo PDF / in tem.",
            )
            return

        if self.view and self.view.auto_commit_form():
            self.view.append_log("Đã tự động lưu thay đổi trên biểu mẫu trước khi tạo PDF.")

        try:
            template_path = Path(self.app_state.template_var.get())
            output_dir = Path(self.app_state.output_dir_var.get())
            output_name = self.app_state.output_name_var.get().strip() or self.app_state._default_output_name()

            if not self.app_state.records:
                raise ValueError("Chưa có dữ liệu để tạo PDF.")
            records_snapshot = validate_records(self.app_state.records)
            if not template_path.is_file():
                raise ValueError("Không tìm thấy tệp PDF mẫu.")
            final_name = output_name if output_name.lower().endswith(".pdf") else output_name + ".pdf"
            output_path = output_dir / final_name
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                APP_TITLE,
                f"Không thể bắt đầu tạo tệp PDF:\n{format_error_for_user(exc, 'bắt đầu tạo tệp PDF')}\n\n"
                "👉 Hướng dẫn:\n"
                "- Nếu chưa có dữ liệu: Vui lòng thêm dữ liệu vào bảng trước.\n"
                "- Nếu thiếu PDF mẫu: Vui lòng chọn tệp template.pdf hợp lệ tại thanh bên trái.",
            )
            return

        records_snapshot, previously_exported, repeated_in_list = self._filter_new_records(records_snapshot)
        skipped_count = previously_exported + repeated_in_list
        if skipped_count and not records_snapshot:
            message = (
                "Không có tem mới để xuất.\n\n"
                f"{previously_exported} tem đã được xuất trước đó; "
                f"{repeated_in_list} dòng bị lặp trong danh sách.\n\n"
                "Bảng dữ liệu vẫn được giữ nguyên. Hãy kiểm tra các dòng tô đỏ rồi thử lại."
            )
            log_error_event(
                "DUPLICATE_EXPORT_BLOCKED",
                f"Chặn tạo PDF vì toàn bộ {skipped_count} dòng trên bảng đều đã được xuất hoặc bị lặp ({previously_exported} đã xuất, {repeated_in_list} lặp).",
                diagnostics={
                    "previously_exported": previously_exported,
                    "repeated_in_list": repeated_in_list,
                    "active_table": self._build_records_diagnostics(self.app_state.records),
                },
                app_version=self._app_version_str(),
            )
            if self.view:
                self.view.show_duplicate_export_info(message)
            return

        if skipped_count:
            confirmed = bool(
                self.view
                and self.view.confirm_export_new_only(
                    previously_exported=previously_exported,
                    repeated_in_list=repeated_in_list,
                    new_count=len(records_snapshot),
                )
            )
            log_error_event(
                "DUPLICATE_EXPORT_PROMPT",
                (
                    f"Hộp thoại phát hiện {previously_exported} tem đã xuất trước đó, {repeated_in_list} dòng lặp; "
                    f"có {len(records_snapshot)} tem mới. Người dùng chọn: "
                    f"{'Chỉ xuất tem mới' if confirmed else 'Hủy'}."
                ),
                diagnostics={
                    "previously_exported": previously_exported,
                    "repeated_in_list": repeated_in_list,
                    "new_count": len(records_snapshot),
                    "user_confirmed_export_new_only": confirmed,
                    "active_table": self._build_records_diagnostics(self.app_state.records),
                    "new_records": self._build_records_diagnostics(records_snapshot),
                },
                app_version=self._app_version_str(),
            )
            if not confirmed:
                return

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            self.app_state.output_name_var.set(final_name)
        except OSError as exc:
            messagebox.showerror(APP_TITLE, f"Không thể chuẩn bị thư mục lưu PDF:\n{format_error_for_user(exc, 'chuẩn bị thư mục lưu PDF')}", parent=self.view)
            return

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

    def _filter_new_records(self, records: list[SlipRecord]) -> tuple[list[SlipRecord], int, int]:
        """Keep first-time PO/Box combinations and count rows already accounted for."""
        new_records: list[SlipRecord] = []
        seen: set[tuple[str, str, str, str]] = set()
        previously_exported = 0
        repeated_in_list = 0

        for record in records:
            if not record.po.strip():
                new_records.append(record)
                continue

            key = (record.po, record.po_detail, record.po_sub, record.box)
            if key in seen:
                repeated_in_list += 1
                continue
            seen.add(key)

            if self.app_state.po_registry.is_registered(*key):
                previously_exported += 1
                continue
            new_records.append(record)

        return new_records, previously_exported, repeated_in_list

    def _generate_worker(self, output_path: Path, records_snapshot: list[SlipRecord]) -> None:
        def on_progress(current: int, total: int, message: str) -> None:
            self.app_state.event_queue.put(("progress", (current, total, message)))

        try:
            paper_size_val = self.app_state.paper_size_var.get() if hasattr(self.app_state, "paper_size_var") else "A4"
            records = generate_pdf_from_records(
                records_snapshot,
                self.app_state.template_var.get(),
                output_path,
                layout_config=self.app_state.layout_config,
                progress_callback=on_progress,
                registry=self.app_state.po_registry,
                paper_size=paper_size_val,
            )
        except DuplicateComboError as exc:
            err_msg = format_error_for_user(exc, 'kiểm tra tem trùng khi tạo PDF')
            log_error_event(
                "PDF_EXPORT_DUPLICATE_RACE",
                f"Xung đột đăng ký trùng tem từ máy khác khi đang tạo PDF: {err_msg}",
                diagnostics=self._build_records_diagnostics(records_snapshot),
                error=exc,
                app_version=self._app_version_str(),
            )
            self.app_state.event_queue.put(("duplicate_race", err_msg))
            return
        except Exception as exc:  # noqa: BLE001
            err_msg = format_error_for_user(exc, 'tạo tệp PDF')
            log_error_event(
                "PDF_EXPORT_ERROR",
                f"Lỗi khi tạo tệp PDF '{output_path}': {err_msg}",
                diagnostics=self._build_records_diagnostics(records_snapshot),
                error=exc,
                app_version=self._app_version_str(),
            )
            self.app_state.event_queue.put(("error", err_msg))
            return
        self.app_state.event_queue.put(("success", (output_path, len(records), list(records))))

    def on_pdf_export_completed(
        self,
        exported_records: list[SlipRecord] | None,
        output_path: Path,
        record_count: int,
        page_count: int,
        paper_size: str,
    ) -> None:
        """Clean up exported records from the active print queue after successful PDF generation and log the event."""
        exported_list = list(exported_records) if exported_records else []
        exported_keys = {
            (
                r.po.strip(),
                r.po_detail.strip() or FIXED_PO_DETAIL,
                r.po_sub.strip() or FIXED_PO_SUB,
                r.box.strip(),
            )
            for r in exported_list
            if r.po.strip()
        }
        before_count = len(self.app_state.records)
        remaining: list[SlipRecord] = []
        for r in self.app_state.records:
            po_val = r.po.strip()
            if not po_val:
                remaining.append(r)
                continue
            key = (
                po_val,
                r.po_detail.strip() or FIXED_PO_DETAIL,
                r.po_sub.strip() or FIXED_PO_SUB,
                r.box.strip(),
            )
            if key in exported_keys or self.app_state.po_registry.is_registered(*key):
                continue
            remaining.append(r)

        removed_count = before_count - len(remaining)
        self.app_state.records = remaining
        self._last_auto_po = None
        if not remaining and not getattr(self.app_state, "manual_po_override", False):
            self.app_state.po_var.set("")
            self.app_state.po_detail_var.set("")
            self.app_state.po_sub_var.set("")

        log_error_event(
            "PDF_EXPORT_SUCCESS",
            (
                f"Đã xuất thành công {record_count} tem ({page_count} trang {paper_size}) ra tệp '{output_path}'. "
                f"Đã tự động dọn {removed_count} dòng đã xuất khỏi bảng chờ in (còn lại {len(remaining)} dòng)."
            ),
            diagnostics={
                "output_path": str(output_path),
                "exported_count": record_count,
                "page_count": page_count,
                "paper_size": paper_size,
                "removed_from_queue_count": removed_count,
                "remaining_queue_count": len(remaining),
                "exported_records": self._build_records_diagnostics(exported_list),
            },
            app_version=self._app_version_str(),
        )

        if self.view:
            if hasattr(self.view, "set_records"):
                self.view.set_records(
                    self.app_state.records,
                    select_index=0 if self.app_state.records else None,
                )
            if removed_count > 0 and hasattr(self.view, "append_log"):
                self.view.append_log(
                    f"Đã tự động làm sạch {removed_count} dòng tem vừa xuất khỏi danh sách chờ in."
                )

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
                    f"Không thể kết nối để kiểm tra bản cập nhật:\n{format_error_for_user(exc, 'kiểm tra bản cập nhật')}\n\n"
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
                self.app_state.event_queue.put(("update_error", (format_error_for_user(exc, 'kiểm tra bản cập nhật'), automatic)))

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
                self.app_state.event_queue.put(("update_error", (format_error_for_user(exc, 'tải hoặc cài đặt bản cập nhật'), False)))

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
                "Chưa có tệp PDF nào được tạo trong phiên làm việc này.\n\n"
                "👉 Hướng dẫn: Vui lòng nhấn nút 'Tạo PDF' để xuất tệp trước khi mở.",
            )
            return
        if sys.platform == "win32":
            os.startfile(self.app_state.generated_output_path)

    def open_build_script(self) -> None:
        script_path = self.app_state.bundle_dir / "build_exe.bat"
        if not script_path.exists():
            messagebox.showwarning(
                APP_TITLE,
                "Không tìm thấy tệp kịch bản 'build_exe.bat' trong thư mục ứng dụng.\n\n"
                "👉 Lưu ý: Chức năng này chỉ khả dụng trong môi trường phát triển mã nguồn.",
            )
            return
        if sys.platform == "win32":
            os.startfile(script_path)

    def open_project_folder(self) -> None:
        folder = self.app_state.bundle_dir if not getattr(sys, "frozen", False) else self.app_state.paths.data_dir
        if sys.platform == "win32":
            os.startfile(folder)

    # --- CAV No. & PART MASTER ---
    def is_inspection_source_available(self) -> bool:
        """Return True if the Inspection_data root directory exists and is accessible."""
        custom_root = None
        if hasattr(self.app_state, "inspection_root_var"):
            raw_root = self.app_state.inspection_root_var.get().strip()
            if raw_root:
                custom_root = raw_root
        try:
            return get_inspection_data_root(custom_root).is_dir()
        except OSError:
            return False

    def resolve_cav_for_item(
        self,
        item_code: str,
        preferred_rev: str | None = None,
        *,
        use_cache: bool = True,
    ) -> tuple[list[int], InspectionCSVData | None, str]:
        """Resolve valid CAV list for item_code: prioritize Inspection CSV master, fallback to PartMaster DB only when offline."""
        clean_code = (item_code or "").strip().upper()
        self._last_found_csv_path = None
        self._last_csv_lookup_error = ""
        if not clean_code:
            return [], None, "empty"

        custom_root = None
        if hasattr(self.app_state, "inspection_root_var"):
            raw_root = self.app_state.inspection_root_var.get().strip()
            if raw_root:
                custom_root = raw_root

        cache_key = (
            str(custom_root or ""),
            clean_code,
            str(preferred_rev or "").strip(),
        )
        now_mono = time.monotonic()
        if use_cache and cache_key in self._cav_cache:
            cached_ts, c_cavs, c_data, c_src, c_path, c_err = self._cav_cache[cache_key]
            if (now_mono - cached_ts) < self._cav_cache_ttl_seconds:
                self._last_found_csv_path = c_path
                self._last_csv_lookup_error = c_err
                return list(c_cavs), c_data, c_src

        csv_file: Path | None = None
        csv_data: InspectionCSVData | None = None
        try:
            csv_file, active_files, active_revs, is_from_old = _find_inspection_csv_with_context(
                clean_code,
                preferred_rev=preferred_rev,
                inspection_root=custom_root,
            )
            self._last_found_csv_path = csv_file
            csv_data = parse_inspection_csv(csv_file)
            if csv_data.item_code.strip().upper() != clean_code:
                csv_data.item_code = clean_code
            csv_data.active_csv_files = active_files
            csv_data.active_revisions = active_revs
            csv_data.is_from_old_archive = bool(is_from_old or csv_data.is_from_old_archive)
            combined_warnings = list(csv_data.warnings)
            if len(active_revs) > 1:
                revs_str = ", ".join(f"Rev {r}" for r in active_revs)
                files_str = ", ".join(active_files)
                combined_warnings.append(
                    f"Thư mục gốc của mã '{clean_code}' đang tồn tại đồng thời nhiều Revision ({revs_str}: {files_str}) "
                    f"do QC chưa chuyển file cũ vào thư mục 'old'. Đang sử dụng file '{csv_file.name}' (Rev {csv_data.rev}, Ver {csv_data.version})."
                )
            csv_data.warnings = tuple(combined_warnings)
        except Exception as exc:  # noqa: BLE001
            self._last_csv_lookup_error = str(exc)
            csv_data = None
            if self.is_inspection_source_available() or csv_file is not None:
                evt_type = "CSV_PARSE_ERROR" if csv_file is not None else "ITEM_CODE_NOT_FOUND"
                log_error_event(
                    evt_type,
                    str(exc),
                    item_code=clean_code,
                    csv_path=csv_file,
                    diagnostics=collect_inspection_diagnostics(
                        clean_code,
                        inspection_root=custom_root,
                        csv_file=csv_file,
                    ),
                    error=exc,
                    app_version=self._app_version_str(),
                )

        if csv_data is not None:
            result = (list(csv_data.valid_cavs), csv_data, "csv")
            self._cav_cache[cache_key] = (
                now_mono,
                list(csv_data.valid_cavs),
                csv_data,
                "csv",
                self._last_found_csv_path,
                self._last_csv_lookup_error,
            )
            return result

        if not self.is_inspection_source_available() and hasattr(self.app_state, "part_master"):
            entry = self.app_state.part_master.get(clean_code)
            if entry is not None and entry.valid_cavs:
                self._cav_cache[cache_key] = (
                    now_mono,
                    list(entry.valid_cavs),
                    None,
                    "master",
                    self._last_found_csv_path,
                    self._last_csv_lookup_error,
                )
                return list(entry.valid_cavs), None, "master"

        self._cav_cache[cache_key] = (
            now_mono,
            [],
            None,
            "none",
            self._last_found_csv_path,
            self._last_csv_lookup_error,
        )
        return [], None, "none"

    def _resolve_active_cav_for_form(self, *, item_code: str, rev: str) -> str:
        """Determine the active CAV No. string for the current form state and enforce Split CAV rules."""
        clean_code = (item_code or "").strip().upper()
        clean_rev = (rev or "").strip()
        last_rev = getattr(self, "_last_resolved_cav_rev", "")
        if clean_code and (
            (clean_code != getattr(self, "_last_resolved_cav_item_code", "") and not self.app_state.valid_cavs)
            or (clean_rev and clean_rev != last_rev and getattr(self.app_state, "cav_source", "none") == "csv")
        ):
            valid_cavs, csv_data, source = self.resolve_cav_for_item(clean_code, preferred_rev=clean_rev)
            if csv_data is not None and (not clean_rev or csv_data.revision == clean_rev or not self.app_state.valid_cavs):
                self.app_state.valid_cavs = list(valid_cavs)
                self.app_state.cav_source = source
                self._last_resolved_cav_item_code = clean_code
                self._last_resolved_cav_rev = csv_data.revision
                if not self.app_state.split_cav_var.get():
                    self.app_state.selected_cavs = list(valid_cavs)
                    if valid_cavs:
                        self.app_state.cav_var.set(format_cav_list(valid_cavs))

        cav_source = getattr(self.app_state, "cav_source", "none")
        raw_manual = self.app_state.cav_var.get().strip()

        # When CSV is unavailable (fallback mode), allow manual CAV input (1..16) directly on the form
        if cav_source != "csv" and raw_manual and (not self.app_state.split_cav_var.get() or not self.app_state.valid_cavs):
            parsed_manual = parse_manual_cav_input(raw_manual)
            self.app_state.valid_cavs = list(parsed_manual)
            self.app_state.selected_cavs = list(parsed_manual)
            self.app_state.cav_source = "master"
            if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
                self.view.data_tab.sync_cav_ui()

        if self.app_state.split_cav_var.get():
            if not self.app_state.selected_cavs:
                raise ValueError(
                    "Đang bật 'Tách CAV' nhưng chưa chọn CAV nào. Vui lòng chọn ít nhất một CAV hợp lệ!"
                )
            invalid = [c for c in self.app_state.selected_cavs if c not in self.app_state.valid_cavs]
            if invalid:
                raise ValueError(
                    f"CAV đã chọn ({', '.join(str(x) for x in invalid)}) không nằm trong danh sách CAV hợp lệ ({format_cav_list(self.app_state.valid_cavs)})!"
                )
            return format_cav_list(self.app_state.selected_cavs)

        if self.app_state.valid_cavs:
            return format_cav_list(self.app_state.valid_cavs)
        if raw_manual:
            parsed_manual = parse_manual_cav_input(raw_manual)
            return format_cav_list(parsed_manual)
        return ""

    def on_rev_input_changed(self, *_args) -> None:
        """Re-resolve CSV data (including 'old/' archive subfolder) when user manually changes Revision on the form."""
        raw_code = self.app_state.item_code_var.get().strip().upper()
        raw_rev = self.app_state.rev_var.get().strip()
        if not raw_code or not (len(raw_rev) == 2 and raw_rev.isdigit() and 1 <= int(raw_rev) <= 99):
            return
        if raw_rev == getattr(self, "_last_resolved_cav_rev", ""):
            return

        valid_cavs, csv_data, source = self.resolve_cav_for_item(raw_code, preferred_rev=raw_rev)
        if csv_data is not None and csv_data.revision == raw_rev:
            self.app_state.valid_cavs = list(valid_cavs)
            self.app_state.cav_source = source
            self._last_resolved_cav_item_code = raw_code
            self._last_resolved_cav_rev = csv_data.revision
            if csv_data.pcs_per_box is not None:
                self.app_state.carton_qty_var.set(str(csv_data.pcs_per_box))
            if self.app_state.split_cav_var.get():
                self.app_state.selected_cavs = [c for c in self.app_state.selected_cavs if c in valid_cavs]
                self.app_state.cav_var.set(format_cav_list(self.app_state.selected_cavs))
            else:
                self.app_state.selected_cavs = list(valid_cavs)
                self.app_state.cav_var.set(format_cav_list(valid_cavs))
            if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
                self.view.data_tab.sync_cav_ui()

            cav_display = format_cav_list(valid_cavs) or "Không có"
            archive_note = " từ thư mục lưu trữ 'old'" if csv_data.is_from_old_archive else ""
            msg = (
                f"📦 Đã nạp dữ liệu Rev {raw_rev}{archive_note} "
                f"(file: {csv_data.file_path.name} · Ver {csv_data.version}, CAV: {cav_display})"
            )
            self.app_state.status_var.set(msg)
            if self.view:
                self.view.append_log(msg)
                self.view.refresh_preview_image()
        elif csv_data is not None and csv_data.revision != raw_rev:
            self._last_resolved_cav_rev = raw_rev
            warn_msg = (
                f"⚠️ Đang nhập thủ công Rev {raw_rev} — Không tìm thấy file CSV cho Rev {raw_rev} (kể cả trong 'old'). "
                f"Server QC hiện đang ở Rev {csv_data.revision} ({csv_data.file_path.name})."
            )
            self.app_state.status_var.set(warn_msg)
            if self.view:
                self.view.append_log(warn_msg)

    def on_manual_cav_entry_committed(self, *_args) -> None:
        """Validate and apply manual CAV input (1..16) typed directly into CAV No. when CSV is unavailable."""
        if getattr(self.app_state, "cav_source", "none") == "csv":
            return
        if self.app_state.split_cav_var.get() and self.app_state.valid_cavs:
            return

        raw_cav = self.app_state.cav_var.get().strip()
        if not raw_cav:
            self.app_state.valid_cavs = []
            self.app_state.selected_cavs = []
            if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
                self.view.data_tab.sync_cav_ui()
            if self.view:
                self.view.refresh_preview_image()
            return

        try:
            parsed = parse_manual_cav_input(raw_cav)
        except ValueError as err:
            messagebox.showwarning(APP_TITLE, str(err))
            self.app_state.cav_var.set(format_cav_list(self.app_state.valid_cavs))
            return

        formatted = format_cav_list(parsed)
        self.app_state.valid_cavs = list(parsed)
        self.app_state.selected_cavs = list(parsed)
        self.app_state.cav_var.set(formatted)
        self.app_state.cav_source = "master"

        item_code = self.app_state.item_code_var.get().strip().upper()
        item_name = self.app_state.item_name_var.get().strip()
        rev = self.app_state.rev_var.get().strip()
        if hasattr(self.app_state, "part_master") and item_code and item_name and rev:
            try:
                self.app_state.part_master.upsert(item_code, item_name, rev, cav_list=formatted)
            except ValueError:
                pass

        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()
        if self.view:
            self.view.refresh_preview_image()

    def sync_cav_state_for_record(self, record: SlipRecord) -> None:
        """Synchronize valid_cavs and selected_cavs when a record row is selected in the table."""
        clean_code = record.item_code.strip().upper()
        valid_cavs, _csv_data, source = self.resolve_cav_for_item(clean_code, preferred_rev=record.rev)
        self.app_state.cav_source = source
        self._last_resolved_cav_item_code = clean_code

        rec_cavs: list[int] = []
        if record.cav_no.strip():
            try:
                rec_cavs = parse_manual_cav_input(record.cav_no)
            except ValueError:
                rec_cavs = []

        if not valid_cavs and rec_cavs:
            valid_cavs = list(rec_cavs)
        self.app_state.valid_cavs = list(valid_cavs)

        if self.app_state.split_cav_var.get():
            if rec_cavs and all(c in valid_cavs for c in rec_cavs):
                self.app_state.selected_cavs = list(rec_cavs)
            else:
                self.app_state.selected_cavs = [c for c in self.app_state.selected_cavs if c in valid_cavs]
        else:
            self.app_state.selected_cavs = list(valid_cavs)

        self.app_state.cav_var.set(record.cav_no)
        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()

    def on_split_cav_toggled(self) -> None:
        """Handle toggling of 'Tách CAV' switch on the input/print screen."""
        is_split = bool(self.app_state.split_cav_var.get())
        if is_split and not self.app_state.valid_cavs and getattr(self.app_state, "cav_source", "none") != "csv":
            raw_cav = self.app_state.cav_var.get().strip()
            if raw_cav:
                try:
                    parsed = parse_manual_cav_input(raw_cav)
                    self.app_state.valid_cavs = list(parsed)
                    self.app_state.cav_source = "master"
                except ValueError as err:
                    messagebox.showwarning(APP_TITLE, str(err))
                    self.app_state.split_cav_var.set(False)
                    return

        valid_cavs = list(self.app_state.valid_cavs)
        if is_split:
            self.app_state.selected_cavs = []
            self.app_state.cav_var.set("")
        else:
            self.app_state.selected_cavs = list(valid_cavs)
            self.app_state.cav_var.set(format_cav_list(valid_cavs))

        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()
        if self.view:
            self.view.refresh_preview_image()

    def set_cav_selection(self, cav_num: int, is_selected: bool) -> None:
        """Select or deselect a single CAV number in Split CAV mode."""
        num = int(cav_num)
        if num not in self.app_state.valid_cavs:
            raise ValueError(
                f"CAV {num} không nằm trong danh sách CAV hợp lệ ({format_cav_list(self.app_state.valid_cavs)})!"
            )
        current = set(self.app_state.selected_cavs)
        if is_selected:
            current.add(num)
        else:
            current.discard(num)
        self.app_state.selected_cavs = sorted(current)
        if self.app_state.split_cav_var.get():
            self.app_state.cav_var.set(format_cav_list(self.app_state.selected_cavs))
        else:
            self.app_state.cav_var.set(format_cav_list(self.app_state.valid_cavs))

        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()
        if self.view:
            self.view.refresh_preview_image()

    def set_selected_cavs(self, cavs: Iterable[int]) -> None:
        """Replace the active selected CAV list in Split CAV mode, rejecting any CAV not in valid_cavs."""
        normalized: list[int] = []
        seen: set[int] = set()
        for item in cavs:
            num = int(item)
            if num not in self.app_state.valid_cavs:
                raise ValueError(
                    f"CAV {num} không nằm trong danh sách CAV hợp lệ ({format_cav_list(self.app_state.valid_cavs)})!"
                )
            if num not in seen:
                seen.add(num)
                normalized.append(num)
        self.app_state.selected_cavs = sorted(normalized)
        if self.app_state.split_cav_var.get():
            self.app_state.cav_var.set(format_cav_list(self.app_state.selected_cavs))
        else:
            self.app_state.cav_var.set(format_cav_list(self.app_state.valid_cavs))

        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()
        if self.view:
            self.view.refresh_preview_image()

    def on_item_code_input_changed(self, *_args, force_reload: bool = False) -> None:
        """Auto-fill item_name, rev, carton_qty (pcs/box), and CAV No. from Inspection CSV / Part Master."""
        raw_code = self.app_state.item_code_var.get().strip().upper()
        if not raw_code:
            self.app_state.valid_cavs = []
            self.app_state.selected_cavs = []
            self.app_state.cav_source = "none"
            self.app_state.cav_var.set("")
            self._last_resolved_cav_item_code = ""
            self._last_resolved_cav_not_found = False
            if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
                self.view.data_tab.sync_cav_ui()
            return

        prev_code = getattr(self, "_last_resolved_cav_item_code", "")
        is_focus_out_only = bool(_args) and not force_reload
        if (
            is_focus_out_only
            and raw_code == prev_code
            and (
                (
                    self.app_state.item_name_var.get().strip()
                    and self.app_state.carton_qty_var.get().strip()
                    and self.app_state.rev_var.get().strip()
                )
                or getattr(self, "_last_resolved_cav_not_found", False)
            )
        ):
            return

        if prev_code and raw_code != prev_code:
            self.app_state.split_cav_var.set(False)
            self.app_state.form_mode_var.set("Đang tạo dòng mới")
            if not getattr(self.app_state, "manual_po_override", False):
                self.app_state.po_var.set("")
                self.app_state.po_detail_var.set("")
                self.app_state.po_sub_var.set("")

        if force_reload:
            self.clear_cav_cache()

        inspection_online = self.is_inspection_source_available()
        valid_cavs, csv_data, source = self.resolve_cav_for_item(
            raw_code,
            preferred_rev=None,
            use_cache=not force_reload,
        )
        entry = (
            self.app_state.part_master.get(raw_code)
            if (not inspection_online and hasattr(self.app_state, "part_master"))
            else None
        )
        self.app_state.valid_cavs = list(valid_cavs)
        self.app_state.cav_source = source
        self._last_resolved_cav_item_code = raw_code
        self._last_resolved_cav_rev = (
            csv_data.revision
            if csv_data is not None
            else (entry.rev if entry is not None else "")
        )
        self._last_resolved_cav_not_found = csv_data is None and entry is None

        if csv_data is not None:
            self.app_state.item_name_var.set(csv_data.item_name.strip().upper())
            self.app_state.rev_var.set(csv_data.revision)
            self.app_state.carton_qty_var.set(
                str(csv_data.pcs_per_box) if csv_data.pcs_per_box is not None else ""
            )

            if (
                hasattr(self.app_state, "part_master")
                and self.app_state.item_name_var.get().strip()
                and self.app_state.rev_var.get().strip()
            ):
                try:
                    self.app_state.part_master.upsert(
                        csv_data.item_code,
                        self.app_state.item_name_var.get().strip(),
                        self.app_state.rev_var.get().strip(),
                        cav_list=csv_data.cav_text,
                        carton_qty=csv_data.pcs_per_box,
                    )
                except ValueError:
                    pass
        elif entry is not None:
            self.app_state.item_name_var.set(entry.item_name)
            self.app_state.rev_var.set(entry.rev)
            self.app_state.carton_qty_var.set(entry.carton_qty if entry.carton_qty else "")
        else:
            if inspection_online and hasattr(self.app_state, "part_master"):
                try:
                    self.app_state.part_master.delete(raw_code)
                except Exception:  # noqa: BLE001
                    pass
            if inspection_online or force_reload or (prev_code and raw_code != prev_code):
                self.app_state.item_name_var.set("")
                self.app_state.rev_var.set("")
                self.app_state.carton_qty_var.set("")

        if self.app_state.split_cav_var.get():
            self.app_state.selected_cavs = [c for c in self.app_state.selected_cavs if c in valid_cavs]
            self.app_state.cav_var.set(format_cav_list(self.app_state.selected_cavs))
        else:
            self.app_state.selected_cavs = list(valid_cavs)
            self.app_state.cav_var.set(format_cav_list(valid_cavs))

        if self.view and hasattr(self.view, "data_tab") and hasattr(self.view.data_tab, "sync_cav_ui"):
            self.view.data_tab.sync_cav_ui()

        if csv_data is not None:
            cav_display = format_cav_list(valid_cavs) or "Không có"
            pcs_val = self.app_state.carton_qty_var.get().strip()
            pcs_note = f", SL/thùng: {pcs_val}" if pcs_val else ""
            archive_tag = " [từ thư mục 'old']" if csv_data.is_from_old_archive else ""
            src_label = f"CSV: {csv_data.file_path.name} · Ver {csv_data.version}{archive_tag}"
            if csv_data.warnings:
                warn_summary = " | ".join(csv_data.warnings)
                self.app_state.status_var.set(
                    f"⚠️ Mã {raw_code} (Rev: {self.app_state.rev_var.get()}{pcs_note}, CAV: {cav_display} - {src_label}) — {warn_summary}"
                )
                if self.view:
                    for w in csv_data.warnings:
                        self.view.append_log(f"⚠️ CẢNH BÁO DỮ LIỆU CSV ({raw_code}): {w}")
                warn_key = (raw_code, str(csv_data.file_path), csv_data.warnings)
                if force_reload or warn_key != getattr(self, "_last_warned_csv_key", None):
                    self._last_warned_csv_key = warn_key
                    messagebox.showwarning(
                        APP_TITLE,
                        f"⚠️ CẢNH BÁO DỮ LIỆU CSV QC ({raw_code}):\n\n"
                        + "\n\n".join(f"- {w}" for w in csv_data.warnings)
                        + "\n\n👉 Vui lòng kiểm tra kỹ Revision thực tế của lô hàng trước khi in!",
                    )
            else:
                self.app_state.status_var.set(
                    f"Đã nạp thông tin mã {raw_code} (Rev: {self.app_state.rev_var.get()}{pcs_note}, CAV: {cav_display} - nguồn: {src_label})"
                )
            if self.view:
                self.view.append_log(
                    f"Mã {raw_code}: Tên='{self.app_state.item_name_var.get()}', Rev={self.app_state.rev_var.get()}{pcs_note}, CAV hợp lệ = [{cav_display}] (nguồn: {src_label})"
                )
        elif entry is not None:
            cav_display = format_cav_list(valid_cavs) or "Không có"
            pcs_val = self.app_state.carton_qty_var.get().strip()
            pcs_note = f", SL/thùng: {pcs_val}" if pcs_val else ""
            offline_msg = (
                f"⚠️ Mất kết nối Server CSV QC — Mã {raw_code} đang dùng dữ liệu lưu tạm "
                f"(Rev: {self.app_state.rev_var.get()}{pcs_note}, CAV: {cav_display} - nguồn: Danh mục Master). "
                "Vui lòng kiểm tra kỹ Rev thực tế!"
            )
            self.app_state.status_var.set(offline_msg)
            if self.view:
                self.view.append_log(offline_msg)
        else:
            found_csv = getattr(self, "_last_found_csv_path", None)
            err_detail = getattr(self, "_last_csv_lookup_error", "")
            if found_csv is not None:
                not_found_status = (
                    f"⚠️ Tìm thấy tệp '{found_csv.name}' của mã '{raw_code}' nhưng lỗi đọc cấu trúc: {err_detail}"
                )
                popup_msg = (
                    f"Đã tìm thấy tệp CSV của mã '{raw_code}':\n{found_csv}\n\n"
                    f"Tuy nhiên không thể đọc dữ liệu bên trong tệp:\n{err_detail}\n\n"
                    "👉 Chi tiết lỗi đã được ghi tự động vào thư mục error_log trên LAN."
                )
            elif inspection_online:
                not_found_status = (
                    f"❌ Mã hàng '{raw_code}' không tồn tại trong thư mục dữ liệu gốc (Inspection_data)!"
                )
                popup_msg = (
                    f"Mã hàng '{raw_code}' không tồn tại trong thư mục dữ liệu gốc (Inspection_data)!\n\n"
                    "👉 Vui lòng kiểm tra lại chính xác từng ký tự của Mã hàng đã nhập."
                )
            else:
                not_found_status = (
                    f"❌ Không tìm thấy dữ liệu cho mã '{raw_code}'. Vui lòng kiểm tra lại Mã hàng hoặc nhập thủ công."
                )
                popup_msg = (
                    f"Không tìm thấy dữ liệu cho mã '{raw_code}'.\n\n"
                    "👉 Vui lòng kiểm tra lại kết nối tới thư mục Inspection_data hoặc nhập thủ công."
                )
            self.app_state.status_var.set(not_found_status)
            if self.view:
                self.view.append_log(not_found_status)
            if force_reload or inspection_online:
                messagebox.showwarning(APP_TITLE, popup_msg)

    def save_part_master(self) -> None:
        """Validate and save/update part master record from Master tab."""
        code = self.app_state.master_item_code_var.get().strip().upper()
        name = self.app_state.master_item_name_var.get().strip()
        rev = self.app_state.master_rev_var.get().strip()
        cav_raw = self.app_state.master_cav_var.get().strip() if hasattr(self.app_state, "master_cav_var") else ""

        try:
            saved = self.app_state.part_master.upsert(code, name, rev, cav_list=cav_raw)
            self.clear_cav_cache()
            if hasattr(self.app_state, "master_cav_var"):
                self.app_state.master_cav_var.set(saved.cav_list)
            cav_note = f", CAV: {saved.cav_list}" if saved.cav_list else ""
            self.app_state.master_status_var.set(
                f"Đã lưu vào danh mục linh kiện: {saved.item_code} - {saved.item_name} (Rev {saved.rev}{cav_note})"
            )
            if self.view:
                self.view.append_log(
                    f"Danh mục linh kiện: Đã lưu {saved.item_code} ({saved.item_name} - Rev {saved.rev}{cav_note})"
                )
                if hasattr(self.view, "part_master_tab"):
                    self.view.part_master_tab.refresh_table()
            if self.app_state.item_code_var.get().strip().upper() == saved.item_code:
                self.on_item_code_input_changed()
        except ValueError as err:
            messagebox.showwarning("Lỗi danh mục linh kiện", format_error_for_user(err, 'lưu thông tin linh kiện'))
            self.app_state.master_status_var.set(f"Lỗi: {format_error_for_user(err, 'lưu thông tin linh kiện')}")

    def delete_part_master(self) -> None:
        """Delete selected part master record."""
        code = self.app_state.master_item_code_var.get().strip().upper()
        if not code:
            messagebox.showwarning("Xóa linh kiện", "Vui lòng chọn hoặc nhập mã linh kiện cần xóa!")
            return
        if not messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa mã linh kiện '{code}' khỏi danh mục?"):
            return
        deleted = self.app_state.part_master.delete(code)
        if deleted:
            self.clear_cav_cache()
            self.app_state.master_status_var.set(f"Đã xóa linh kiện khỏi danh mục: {code}")
            self.clear_part_master_form()
            if self.view:
                self.view.append_log(f"Danh mục linh kiện: Đã xóa mã {code}")
                if hasattr(self.view, "part_master_tab"):
                    self.view.part_master_tab.refresh_table()
        else:
            messagebox.showwarning("Xóa linh kiện", f"Không tìm thấy mã linh kiện '{code}' trong danh mục!")

    def clear_part_master_form(self) -> None:
        """Reset Master tab form to blank."""
        self.app_state.master_item_code_var.set("")
        self.app_state.master_item_name_var.set("")
        self.app_state.master_rev_var.set("01")
        if hasattr(self.app_state, "master_cav_var"):
            self.app_state.master_cav_var.set("")
        self.app_state.master_status_var.set("Sẵn sàng nhập linh kiện mới")

    def search_part_master(self, *_args) -> None:
        """Refresh Master tab table with filter query."""
        if self.view and hasattr(self.view, "part_master_tab"):
            self.view.part_master_tab.refresh_table()

    def on_close(self) -> None:
        self.app_state.po_registry.close()
        if hasattr(self.app_state, "part_master"):
            self.app_state.part_master.close()
        if self.view:
            self.view.destroy()
