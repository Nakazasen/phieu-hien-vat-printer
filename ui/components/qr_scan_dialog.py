from __future__ import annotations

from typing import TYPE_CHECKING
from tkinter import messagebox
import customtkinter as ctk

from core.slip_printer_engine import (
    FIXED_PO_SUB,
    START_ROW,
    QRParsedData,
    SlipRecord,
    calculate_total_qty,
    create_record,
    expand_box_sequence,
    normalize_box,
    parse_qr_payload,
    validate_revision,
)

if TYPE_CHECKING:
    from ui.app_controller import AppController


class QRScanPanel(ctk.CTkFrame):
    """Reusable QR scan surface: mode selection, gun/paste input, decoded form and actions.

    Can be embedded directly in a Notebook tab (embedded=True) or hosted inside
    the modal QRScanDialog (embedded=False).
    """

    MODE_SPLIT = "split"
    MODE_RETURN = "return"
    MODE_DECODE = "decode"
    MODE_SPLIT_LABEL = "Ph\u00e2n t\u00e1ch (\u5206\u5272)"
    MODE_RETURN_LABEL = "Ho\u00e0n kho (\u623b\u5165)"
    MODE_REISSUE_LABEL = "In l\u1ea1i (\u518d\u767a\u884c)"

    def __init__(self, parent, controller: AppController, embedded: bool = False, **kwargs):
        super().__init__(parent, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state
        self.embedded = embedded

        # Variables
        self.mode_var = ctk.StringVar(value=self.MODE_SPLIT)
        self.scan_input_var = ctk.StringVar()
        self.item_code_var = ctk.StringVar()
        self.item_name_var = ctk.StringVar()
        self.carton_qty_var = ctk.StringVar()
        self.box_var = ctk.StringVar(value="1")
        self.total_qty_var = ctk.StringVar()
        self.rev_var = ctk.StringVar(value="01")
        self.po_var = ctk.StringVar()
        self.po_detail_var = ctk.StringVar()
        self.source_po_detail = ""
        self.po_sub_var = ctk.StringVar(value=FIXED_PO_SUB)
        self.lot_var = ctk.StringVar()
        self.status_msg_var = ctk.StringVar(value="Sẵn sàng quét mã QR...")
        self.char_count_var = ctk.StringVar(value="Độ dài QR: 0 ký tự")

        # Traces for auto-recalculation
        self.carton_qty_var.trace_add("write", self._on_qty_or_box_changed)
        self.box_var.trace_add("write", self._on_qty_or_box_changed)
        self.item_code_var.trace_add("write", self._update_payload_preview)
        self.rev_var.trace_add("write", self._update_payload_preview)
        self.lot_var.trace_add("write", self._update_payload_preview)
        self.po_detail_var.trace_add("write", self._update_payload_preview)

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # 1. TOP HEADER & MODE SELECTION
        header_frame = ctk.CTkFrame(self, corner_radius=10)
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        header_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="Nghiệp vụ áp dụng:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, padx=(14, 8), pady=12, sticky="w")

        self.mode_segment = ctk.CTkSegmentedButton(
            header_frame,
            values=[self.MODE_SPLIT_LABEL, self.MODE_RETURN_LABEL, self.MODE_REISSUE_LABEL],
            command=self._on_mode_button_changed,
            font=ctk.CTkFont(size=12, weight="bold"),
            selected_color="#2563EB",
        )
        self.mode_segment.set(self.MODE_SPLIT_LABEL)
        self.mode_segment.grid(row=0, column=1, padx=(0, 14), pady=12, sticky="ew")

        # 2. SCAN INPUT AREA (GUN / PASTE)
        scan_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=("gray90", "gray18"))
        scan_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 8))
        scan_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            scan_frame,
            text="📷 Quét mã QR (Súng bắn mã hoặc dán chuỗi QR vào đây):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, padx=14, pady=(10, 4), sticky="w")

        self.scan_entry = ctk.CTkEntry(
            scan_frame,
            textvariable=self.scan_input_var,
            placeholder_text="Quét mã QR bằng súng quét hoặc dán chuỗi 129 ký tự rồi nhấn Enter...",
            height=36,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.scan_entry.grid(row=1, column=0, padx=(14, 8), pady=(0, 10), sticky="ew")
        self.scan_entry.bind("<Return>", lambda _e: self.process_scanned_code())

        self.decode_btn = ctk.CTkButton(
            scan_frame,
            text="📖 Đọc tem",
            width=90,
            height=36,
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.process_scanned_code,
        )
        self.decode_btn.grid(row=1, column=1, padx=(0, 14), pady=(0, 10))

        # 3. DECODED DETAILS & EDIT FORM
        form_frame = ctk.CTkFrame(self, corner_radius=10)
        form_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
        form_frame.grid_columnconfigure((1, 3), weight=1)

        ctk.CTkLabel(
            form_frame,
            text="Chi tiết thông tin tem sau khi bóc tách & chuyển đổi:",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=4, padx=14, pady=(10, 6), sticky="w")

        # Row 1: Item code & Item name
        self._add_field(form_frame, 1, 0, "Mã hàng (*):", self.item_code_var)
        self._add_field(form_frame, 1, 2, "Tên hàng (*):", self.item_name_var)

        # Row 2: Carton Qty & Box count
        self._add_field(form_frame, 2, 0, "Số lượng / thùng (*):", self.carton_qty_var)
        self._add_field(form_frame, 2, 2, "Số thùng (hoặc 001/00N):", self.box_var)

        # Row 3: Total Qty & Rev
        self._add_field(form_frame, 3, 0, "Tổng số lượng:", self.total_qty_var, readonly=True)
        self._add_field(form_frame, 3, 2, "Rev (*) (01–99):", self.rev_var)

        # Row 4: PO & PO Detail
        self._add_field(form_frame, 4, 0, "PO gốc (*):", self.po_var, readonly=True)
        self._add_field(form_frame, 4, 2, "PO chi tiết mới (*):", self.po_detail_var)

        # Row 5: PO Sub & Lot
        self._add_field(form_frame, 5, 0, "PO phụ:", self.po_sub_var, readonly=True)
        self._add_field(form_frame, 5, 2, "Ngày / Lot:", self.lot_var)

        # Live Payload Preview
        preview_header = ctk.CTkFrame(form_frame, fg_color="transparent")
        preview_header.grid(row=6, column=0, columnspan=4, sticky="ew", padx=14, pady=(8, 2))
        preview_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            preview_header,
            text="Chuỗi QR tạo ra (129 ký tự tiêu chuẩn):",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            preview_header,
            textvariable=self.char_count_var,
            font=ctk.CTkFont(size=11),
            text_color="#10B981",
        ).grid(row=0, column=1, sticky="e")

        self.payload_box = ctk.CTkTextbox(
            form_frame,
            height=45,
            font=ctk.CTkFont(family="Consolas", size=11),
        )
        self.payload_box.grid(row=7, column=0, columnspan=4, sticky="ew", padx=14, pady=(0, 10))
        self.payload_box.configure(state="disabled")

        # 4. FOOTER & ACTIONS
        footer_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        footer_frame.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        footer_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            footer_frame,
            textvariable=self.status_msg_var,
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray60"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        btn_row = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew")

        if self.embedded:
            # Embedded tab mode: two primary actions side by side
            btn_row.grid_columnconfigure((0, 1), weight=1)

            ctk.CTkButton(
                btn_row,
                text="➕ Thêm vào danh sách in",
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#10B981",
                hover_color="#059669",
                text_color="white",
                command=self.confirm_and_add_records,
            ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

            ctk.CTkButton(
                btn_row,
                text="📋 Điền vào Form chính",
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#2563EB",
                hover_color="#1D4ED8",
                text_color="white",
                command=self.apply_to_main_form,
            ).grid(row=0, column=1, sticky="ew", padx=(4, 0))
        else:
            btn_row.grid_columnconfigure((0, 1, 2), weight=1)

            ctk.CTkButton(
                btn_row,
                text="➕ Thêm vào danh sách in",
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#10B981",
                hover_color="#059669",
                text_color="white",
                command=self.confirm_and_add_records,
            ).grid(row=0, column=0, sticky="ew", padx=(0, 4))

            ctk.CTkButton(
                btn_row,
                text="📋 Điền vào Form chính",
                height=36,
                font=ctk.CTkFont(size=12, weight="bold"),
                fg_color="#2563EB",
                hover_color="#1D4ED8",
                text_color="white",
                command=self.apply_to_main_form,
            ).grid(row=0, column=1, sticky="ew", padx=4)

            ctk.CTkButton(
                btn_row,
                text="Đóng",
                height=36,
                fg_color=("gray80", "gray30"),
                hover_color=("gray70", "gray40"),
                text_color=("black", "white"),
                command=self.master.destroy,
            ).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def focus_scan_entry(self) -> None:
        """Move keyboard focus to the QR scan input field."""
        try:
            self.scan_entry.focus_set()
        except Exception:  # noqa: BLE001
            pass

    def _add_field(
        self,
        parent: ctk.CTkFrame,
        row: int,
        col: int,
        label: str,
        variable: ctk.StringVar,
        readonly: bool = False,
    ) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=11, weight="bold")).grid(
            row=row, column=col, sticky="w", padx=(14, 4), pady=3
        )
        entry = ctk.CTkEntry(parent, textvariable=variable, height=28, font=ctk.CTkFont(size=12))
        entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 14 if col == 2 else 8), pady=3)
        if readonly:
            entry.configure(state="readonly")
        return entry

    def _on_mode_button_changed(self, choice: str) -> None:
        if "分割" in choice:
            self.mode_var.set(self.MODE_SPLIT)
        elif "戻入" in choice:
            self.mode_var.set(self.MODE_RETURN)
        else:
            self.mode_var.set(self.MODE_DECODE)

        po = self.po_var.get().strip()
        if po:
            self._generate_target_po_detail(po)
            self._update_payload_preview()

    def _generate_target_po_detail(
        self,
        po: str,
        base_detail: str | None = None,
    ) -> tuple[str, bool]:
        mode = self.mode_var.get()
        source_detail = base_detail or self.source_po_detail or self.po_detail_var.get() or "00010"
        current_details = [
            r.po_detail for r in self.app_state.records if r.po.strip() == po
        ]

        error = False
        try:
            if mode == self.MODE_SPLIT:
                detail = self.app_state.po_registry.generate_split_po_detail(
                    po,
                    source_detail,
                    current_details,
                )
            elif mode == self.MODE_RETURN:
                detail = self.app_state.po_registry.generate_return_po_detail(
                    po,
                    source_detail,
                    current_details,
                )
            else:
                detail = source_detail
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Vượt quá giới hạn PO chi tiết",
                f"Không thể tự động sinh PO chi tiết mới cho số PO '{po}':\n{exc}\n\n"
                "👉 Hướng dẫn: Đã đạt số lượng phân tách/hoàn kho tối đa cho số PO này. Vui lòng kiểm tra lại lịch sử đăng ký hoặc sử dụng số PO mới.",
            )
            self.status_msg_var.set(f"⚠️ {exc}")
            detail = self.po_detail_var.get() or "00010"
            error = True

        self.po_detail_var.set(detail)
        return detail, error

    def _on_qty_or_box_changed(self, *_args) -> None:
        try:
            total_qty = calculate_total_qty(self.carton_qty_var.get(), self.box_var.get())
        except ValueError:
            total_qty = ""
        self.total_qty_var.set(total_qty)
        self._update_payload_preview()

    def process_scanned_code(self) -> None:
        raw_code = self.scan_input_var.get().strip()
        if not raw_code:
            messagebox.showwarning(
                "Chưa có mã QR",
                "Ô quét mã QR đang trống.\n\n"
                "👉 Hướng dẫn: Vui lòng dùng súng quét mã bắn vào mã QR trên tem hoặc dán chuỗi ký tự QR (129 ký tự) vào ô nhập liệu rồi nhấn '📖 Đọc tem'.",
            )
            return

        try:
            parsed: QRParsedData = parse_qr_payload(raw_code)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Lỗi giải mã mã QR",
                f"Chuỗi mã QR không đúng định dạng tiêu chuẩn (129 ký tự):\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra lại tem hiện vật gốc hoặc thực hiện quét lại mã QR.",
            )
            self.status_msg_var.set(f"Lỗi: {exc}")
            return

        item_name = ""
        for r in self.app_state.records:
            if r.item_code == parsed.item_code and r.item_name:
                item_name = r.item_name
                break

        self.item_code_var.set(parsed.item_code)
        self.item_name_var.set(item_name)
        self.carton_qty_var.set(parsed.carton_qty)
        self.box_var.set(parsed.box)
        self.total_qty_var.set(parsed.total_qty)
        self.rev_var.set(parsed.rev)
        self.po_var.set(parsed.po)
        self.source_po_detail = parsed.po_detail
        self.po_detail_var.set(parsed.po_detail)
        self.po_sub_var.set(parsed.po_sub or FIXED_PO_SUB)
        self.lot_var.set(parsed.lot)

        new_detail, error = self._generate_target_po_detail(parsed.po, parsed.po_detail)

        if not error:
            mode_name = (
                "Phân tách (分割)"
                if self.mode_var.get() == self.MODE_SPLIT
                else "Hoàn kho (戻入)"
                if self.mode_var.get() == self.MODE_RETURN
                else self.MODE_REISSUE_LABEL
            )
            name_note = " | Nhập Tên hàng trước khi thêm tem" if not item_name else ""
            self.status_msg_var.set(
                f"✅ Đã bóc tách QR: {parsed.item_code} | PO gốc: {parsed.po} -> Chi tiết mới: {new_detail} ({mode_name}){name_note}"
            )
        self._update_payload_preview()

    def _update_payload_preview(self, *_args) -> None:
        try:
            item_code = self.item_code_var.get().strip()
            rev = self.rev_var.get().strip() or "01"
            carton_qty = self.carton_qty_var.get().strip() or "1"
            box = self.box_var.get().strip() or "1"
            po = self.po_var.get().strip() or "1126010101"
            po_detail = self.po_detail_var.get().strip() or "00010"
            po_sub = self.po_sub_var.get().strip() or FIXED_PO_SUB
            lot = self.lot_var.get()

            dummy = create_record(
                row_number=1,
                item_code=item_code,
                item_name=self.item_name_var.get() or "Item",
                carton_qty=carton_qty,
                total_qty=self.total_qty_var.get() or carton_qty,
                po=po,
                po_detail=po_detail,
                po_sub=po_sub,
                box=box,
                rev=rev if (len(rev) == 2 and rev.isdigit()) else "01",
                lot=lot,
            )
            payload = dummy.qr_payload
            self.char_count_var.set(f"Độ dài QR: {len(payload)} ký tự")
            self.payload_box.configure(state="normal")
            self.payload_box.delete("1.0", "end")
            self.payload_box.insert("1.0", payload)
            self.payload_box.configure(state="disabled")
        except Exception:  # noqa: BLE001
            pass

    def _build_records_to_insert(self) -> list[SlipRecord]:
        item_code = self.item_code_var.get().strip()
        item_name = self.item_name_var.get().strip()
        carton_qty = self.carton_qty_var.get().strip()
        box_input = self.box_var.get().strip()
        rev = self.rev_var.get().strip()
        po = self.po_var.get().strip()
        po_detail = self.po_detail_var.get().strip()
        po_sub = self.po_sub_var.get().strip() or FIXED_PO_SUB
        lot = self.lot_var.get()

        if not item_code:
            raise ValueError("Mã hàng không được để trống.")
        if not item_name:
            raise ValueError("Tên hàng không được để trống.")
        if not carton_qty:
            raise ValueError("SL/thùng không được để trống.")
        if not box_input:
            raise ValueError("Số thùng không được để trống.")
        if not po:
            raise ValueError("PO không được để trống.")
        if not po_detail:
            raise ValueError("PO chi tiết không được để trống.")
        validate_revision(rev)

        boxes = expand_box_sequence(box_input)
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
                lot=lot,
            )
            new_records.append(rec)
        return new_records

    def confirm_and_add_records(self) -> None:
        try:
            records = self._build_records_to_insert()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Thông tin tem chưa hợp lệ",
                f"Không thể thêm tem vào danh sách in:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra và điền đầy đủ các thông tin bắt buộc (*) như Mã hàng, Tên hàng, Số lượng, Số box, Rev trước khi thêm.",
            )
            return

        self.app_state.records.extend(records)
        if self.mode_var.get() == self.MODE_SPLIT and self.source_po_detail:
            next_detail, error = self._generate_target_po_detail(
                self.po_var.get().strip(),
                self.source_po_detail,
            )
            if not error:
                self.status_msg_var.set(
                    f"Đã thêm {len(records)} tem. Nhập số lượng tách tiếp theo để phát hành mã {next_detail}."
                )
                self._update_payload_preview()
        mode_name = (
            "Phân tách (分割)"
            if self.mode_var.get() == self.MODE_SPLIT
            else "Hoàn kho (戻入)"
            if self.mode_var.get() == self.MODE_RETURN
            else self.MODE_REISSUE_LABEL
        )
        log_msg = f"Đã thêm {len(records)} tem từ nghiệp vụ {mode_name}: {records[0].item_code} (PO: {records[0].po}, Chi tiết: {records[0].po_detail})"
        if self.controller.view:
            self.controller.view.append_log(log_msg)
            self.controller.view.set_records(
                self.app_state.records,
                select_index=len(self.app_state.records) - 1,
            )

        self.status_msg_var.set(f"✅ {log_msg}. Sẵn sàng quét tem tiếp theo.")
        self.scan_input_var.set("")
        self.focus_scan_entry()

    def apply_to_main_form(self) -> None:
        try:
            records = self._build_records_to_insert()
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror(
                "Thông tin tem chưa hợp lệ",
                f"Không thể điền thông tin tem vào form chính:\n{exc}\n\n"
                "👉 Hướng dẫn: Vui lòng kiểm tra và hoàn thiện các trường dữ liệu trên cửa sổ quét QR trước khi điền vào form chính.",
            )
            return

        first = records[0]
        self.app_state.item_code_var.set(first.item_code)
        self.app_state.item_name_var.set(first.item_name)
        self.app_state.carton_qty_var.set(first.carton_qty)
        self.app_state.total_qty_var.set(first.total_qty)
        self.app_state.box_var.set(self.box_var.get().strip())
        self.app_state.rev_var.set(first.rev)
        self.app_state.po_var.set(first.po)
        self.app_state.po_detail_var.set(first.po_detail)
        self.app_state.po_sub_var.set(first.po_sub)
        self.app_state.lot_var.set("" if first.lot == (" " * 10) else first.lot)
        self.app_state.status_var.set(f"Đã nạp dữ liệu từ nghiệp vụ QR: {first.item_code} (PO chi tiết: {first.po_detail})")
        if self.controller.view:
            self.controller.view.append_log("Đã điền thông tin QR vào form chính.")

        if self.embedded:
            # Seamless flow: jump straight to the data tab so the operator can continue working
            self._switch_to_data_tab()
        else:
            self.master.destroy()

    def _switch_to_data_tab(self) -> None:
        view = self.controller.view
        notebook = getattr(view, "notebook", None)
        if notebook is not None:
            try:
                notebook.select(0)
            except Exception:  # noqa: BLE001
                pass


class QRScanDialog(ctk.CTkToplevel):
    """Modal dialog hosting QRScanPanel for scanning QR, Split (分割) and Return (戻入) operations.

    All attributes and methods of the underlying QRScanPanel are accessible
    directly on the dialog instance via delegation.
    """

    MODE_SPLIT = QRScanPanel.MODE_SPLIT
    MODE_RETURN = QRScanPanel.MODE_RETURN
    MODE_DECODE = QRScanPanel.MODE_DECODE
    MODE_SPLIT_LABEL = QRScanPanel.MODE_SPLIT_LABEL
    MODE_RETURN_LABEL = QRScanPanel.MODE_RETURN_LABEL
    MODE_REISSUE_LABEL = QRScanPanel.MODE_REISSUE_LABEL

    def __init__(self, parent, controller: AppController):
        super().__init__(parent)
        self.controller = controller

        self.title("Quét QR Nghiệp vụ — Phân tách (分割) & Hoàn kho (戻入)")
        self.geometry("740x680")
        self.minsize(680, 600)
        self.transient(parent)

        self.panel = QRScanPanel(self, controller, embedded=False)
        self.panel.pack(fill="both", expand=True)

        # Center on parent window
        self.update_idletasks()
        try:
            px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(10, px)}+{max(10, py)}")
        except Exception:  # noqa: BLE001
            pass

        self.grab_set()
        self.panel.focus_scan_entry()

    def __getattr__(self, name: str):
        panel = self.__dict__.get("panel")
        if panel is not None:
            try:
                return getattr(panel, name)
            except AttributeError:
                pass
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}"
        )
