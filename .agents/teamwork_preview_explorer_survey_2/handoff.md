# Báo Cáo Khảo Sát Nghiệp Vụ & Ánh Xạ Widget UI Cho Tính Năng Hướng Dẫn Sử Dụng (Interactive Tutorial)

## 1. Observation (Quan sát trực tiếp mã nguồn)

Khảo sát toàn bộ cấu trúc mã nguồn ứng dụng In Phiếu Hiện Vật (`d:\Sandbox\PM_in_lai_phieuhienvat`), tập trung vào 4 luồng nghiệp vụ chính và các widget giao diện tương ứng:

### 1.1. Luồng 1: Nạp dữ liệu từ Excel (Excel Data Loading)
- **Tập tin giao diện**: `ui/components/sidebar.py` và `ui/components/data_tab.py`.
- **Tập tin xử lý & Controller**: `ui/app_controller.py` và `core/slip_printer_engine.py`.
- **Các thành phần UI trực tiếp quan sát được**:
  1. *Ô nhập đường dẫn file Excel*: `ui/components/sidebar.py:34, 85-98`
     - Label: `"File Excel (nếu import)"`
     - Entry: `ctk.CTkEntry(field_row, textvariable=self.app_state.excel_var, height=40, font=ctk.CTkFont(size=13))`
     - Button "Chọn": `ctk.CTkButton(field_row, text="Chọn", command=self.controller.pick_excel_file)`
  2. *Nút bấm Import*: `ui/components/sidebar.py:45-52`
     - `ctk.CTkButton(self, text="Import từ Excel", command=self.controller.import_from_excel, height=40, ...)`
  3. *Bảng hiển thị xem trước dữ liệu (Treeview)*: `ui/components/data_tab.py:166-202`
     - Widget: `self.preview_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=5)`
     - Cột dữ liệu: `("row", "item_code", "item_name", "carton_qty", "total_qty", "qty_display", "po", "po_detail", "po_sub", "box", "rev", "lot")`
     - Cuộn: `tree_scroll_y`, `tree_scroll_x`
     - Gắn sự kiện chọn dòng: `self.preview_tree.bind("<<TreeviewSelect>>", self._on_tree_selected)`
     - Đánh dấu dòng trùng lặp: `self.preview_tree.tag_configure("duplicate", background="#FEE2E2", foreground="#991B1B")`
  4. *Bộ điều khiển phân trang / giới hạn hiển thị*: `ui/main_window.py:134-141`
     - `ctk.CTkComboBox(preview_controls, values=["20", "50", "100", "200"], variable=self.app_state.preview_limit_var, ...)`
  5. *Nhãn thống kê & trạng thái*: `ui/main_window.py:111-116`
     - `self.app_state.summary_var` (VD: `"Có 12 dòng hợp lệ"`, `"Chưa có dữ liệu"`)
     - `self.app_state.status_var`
- **Logic & Quy tắc dữ liệu Excel**:
  - Hàm `read_records(excel_file)` tại `core/slip_printer_engine.py:664-698`.
  - Bắt đầu đọc từ dòng thứ 28 (`START_ROW = 28`), lấy 10 cột A:J:
    - Cột 1 (A): Mã hàng (`item_code`)
    - Cột 2 (B): Tên hàng (`item_name`)
    - Cột 3 (C): Tổng số lượng (`total_qty`)
    - Cột 4 (D): Số lượng thùng (`carton_qty`)
    - Cột 5 (E): Số PO (`po`)
    - Cột 6 (F): PO chi tiết (`po_detail`)
    - Cột 7 (G): PO phụ (`po_sub`)
    - Cột 8 (H): Số box (`box`)
    - Cột 9 (I): Phiên bản bản vẽ (`rev`) — Bắt buộc 2 chữ số (`01` đến `99`)
    - Cột 10 (J): Ngày/Lot (`lot`) — Nếu trống thì chuẩn hóa thành 10 dấu cách (`DEFAULT_LOT_TEXT = " " * 10`)

---

### 1.2. Luồng 2: Công cụ Quét QR & 3 Chế độ (QR Scanner Tool & 3 Modes)
- **Tập tin giao diện & Dialog**: `ui/components/qr_scan_dialog.py`.
- **Tập tin kích hoạt**: `ui/components/sidebar.py:54-62` và `ui/components/data_tab.py:51-61`.
- **Các thành phần UI trực tiếp quan sát được**:
  1. *Nút mở Dialog từ Sidebar*: `ui/components/sidebar.py:54-62`
     - `ctk.CTkButton(self, text="⚡ Quét QR (Phân tách · Hoàn kho)", command=self.controller.open_qr_scan_dialog, height=40, fg_color="#2563EB", ...)`
  2. *Nút mở Dialog từ Header Form dữ liệu*: `ui/components/data_tab.py:51-61`
     - `ctk.CTkButton(right_header, text="📷 Quét QR", command=self.controller.open_qr_scan_dialog, height=26, width=90, fg_color="#2563EB", ...)`
  3. *Lựa chọn chế độ (Segmented Button)*: `ui/components/qr_scan_dialog.py:94-102`
     - Widget: `self.mode_segment = ctk.CTkSegmentedButton(header_frame, values=["Phân tách (分割)", "Hoàn kho (戻入)", "Bóc tách / Nhập tem"], command=self._on_mode_button_changed, selected_color="#2563EB")`
     - 3 hằng số chế độ:
       - `MODE_SPLIT = "split"`: Phân tách (分割)
       - `MODE_RETURN = "return"`: Hoàn kho (戻入)
       - `MODE_DECODE = "decode"`: Bóc tách / Nhập tem
  4. *Ô nhập chuỗi quét QR*: `ui/components/qr_scan_dialog.py:115-124`
     - Entry: `self.scan_entry = ctk.CTkEntry(scan_frame, textvariable=self.scan_input_var, placeholder_text="Quét mã QR bằng súng quét hoặc dán chuỗi 129 ký tự rồi nhấn Enter...", height=36, font=ctk.CTkFont(family="Consolas", size=12))`
     - Nút Giải mã: `self.decode_btn = ctk.CTkButton(scan_frame, text="🔍 Giải mã", command=self.process_scanned_code)`
     - Phím tắt: `<Return>` gắn trực tiếp với `self.process_scanned_code()`.
  5. *Form chi tiết tem bóc tách*: `ui/components/qr_scan_dialog.py:147-164`
     - `self.item_code_var` (Mã hàng), `self.item_name_var` (Tên hàng)
     - `self.carton_qty_var` (Số lượng / thùng), `self.box_var` (Số box, mặc định `"1"`)
     - `self.total_qty_var` (Tổng số lượng, tự tính), `self.rev_var` (Rev, mặc định `"01"`)
     - `self.po_var` (PO gốc, readonly), `self.po_detail_var` (PO chi tiết mới sinh, editable)
     - `self.po_sub_var` (PO phụ, mặc định `+001`), `self.lot_var` (Ngày / Lot)
  6. *Ô xem trước chuỗi mã QR tạo ra*: `ui/components/qr_scan_dialog.py:184-190`
     - `self.payload_box = ctk.CTkTextbox(form_frame, height=45, font=ctk.CTkFont(family="Consolas", size=11))`
     - Nhãn đếm ký tự: `self.char_count_var` (Hiển thị `"Độ dài QR: 129 ký tự"`)
  7. *Nút xác nhận hành động*: `ui/components/qr_scan_dialog.py:208-238`
     - Nút "➕ Thêm vào danh sách in": `confirm_and_add_records()`
     - Nút "📋 Điền vào Form chính": `apply_to_main_form()`
     - Nút "Đóng": `destroy()`
- **Logic & Thuật toán 3 Chế độ**:
  - Định dạng chuỗi QR chuẩn 129 ký tự (`build_qr_payload` / `parse_qr_payload` tại `core/slip_printer_engine.py:430-550`):
    - `[0:10]`: PO (10 ký tự)
    - `[10:15]`: PO chi tiết (5 ký tự)
    - `[15:19]`: PO phụ (4 ký tự, mặc định `+001`)
    - `[23:35]`: Tổng SL (12 ký tự: 8 số + `0000`)
    - `[35:60]`: Mã hàng & Rev (25 ký tự)
    - `[60:72]`: Lặp lại Tổng SL (12 ký tự)
    - `[72:98]`: Lot (26 ký tự)
    - `[98:122]`: 24 khoảng trắng
    - `[122:129]`: Box (7 ký tự: `001/003`)
  - **Chế độ 1 - Phân tách (分割 - `MODE_SPLIT`)**:
    - Gọi `generate_split_po_detail(po, current_details)` tại `core/po_registry.py:340-356`.
    - Sinh PO chi tiết dạng `10010`, `20010`, `30010`, ..., `90010` (đúng 5 ký tự).
    - Giới hạn: Tối đa 9 lần phân tách cho mỗi số PO.
  - **Chế độ 2 - Hoàn kho (戻入 - `MODE_RETURN`)**:
    - Gọi `generate_return_po_detail(po, current_details)` tại `core/po_registry.py:358-374`.
    - Sinh PO chi tiết dạng `11010`, `21010`, `31010`, ..., `91010` (đúng 5 ký tự).
    - Giới hạn: Tối đa 9 lần hoàn kho cho mỗi số PO.
  - **Chế độ 3 - Bóc tách / Nhập tem (`MODE_DECODE`)**:
    - Giữ nguyên PO chi tiết gốc từ tem đã quét (hoặc mặc định `00010`).

---

### 1.3. Luồng 3: Tạo mã Auto PO (Auto PO Creation)
- **Tập tin giao diện & Controller**: `ui/components/data_tab.py:86-107`, `ui/app_controller.py:187-235`, `core/po_registry.py:177-234`.
- **Các thành phần UI trực tiếp quan sát được**:
  1. *Cụm PO trên Form nhập liệu chính*: `ui/components/data_tab.py:86-106`
     - Ô PO: `self.po_entry` (`self.app_state.po_var`, state="disabled")
     - Ô PO chi tiết: `self.po_detail_entry` (`self.app_state.po_detail_var`, state="disabled")
     - Ô PO phụ: `self.po_sub_entry` (`self.app_state.po_sub_var`, state="disabled")
  2. *Nút Thêm mới*: `ui/components/data_tab.py:127-131`
     - `ctk.CTkButton(btn_bar_1, text="➕ Thêm mới", command=self.controller.add_record, fg_color="#10B981")`
  3. *Nút Điền mẫu*: `ui/components/data_tab.py:154-158`
     - `ctk.CTkButton(btn_bar_2, text="📋 Điền mẫu", command=self.controller.fill_sample_data)`
  4. *Tab Lịch sử Đăng ký EDI (Tra cứu PO)*: `ui/components/history_tab.py:24-32`
     - Thẻ KPI "🔢 Số PO tiếp theo": `self.app_state.history_next_po_var`
     - Bảng `self.history_tree` hiển thị các trường `created_at`, `po`, `po_detail`, `po_sub`, `box`
- **Quy tắc & Cấu trúc mã PO tự sinh**:
  - Định dạng: `11YYMMDDNN` (10 chữ số):
    - `11`: Tiền tố cố định (`AUTO_PO_PREFIX = "11"`).
    - `YY`: 2 số cuối của năm hiện tại (VD: `26` cho năm 2026).
    - `MM`: Tháng 2 chữ số (VD: `08`).
    - `DD`: Ngày 2 chữ số (VD: `19`).
    - `NN`: Số thứ tự chạy hàng ngày từ `01` đến `99` (Atomic increment trong SQLite `po_sequence`).
  - Giá trị mặc định đi kèm:
    - PO chi tiết: `00010` (`FIXED_PO_DETAIL`)
    - PO phụ: `+001` (`FIXED_PO_SUB`)
  - Quy tắc xử lý đa box (Multi-box series):
    - Khi nhập số box dạng `3` hoặc `001/003`, hàm `expand_box_sequence` sinh ra các bản ghi `001/003`, `002/003`, `003/003`.
    - Tất cả các box trong cùng một lô sẽ **dùng chung một số PO duy nhất**, đảm bảo tính toàn vẹn nghiệp vụ.

---

### 1.4. Luồng 4: Tạo và In file PDF (PDF Generation & Printing)
- **Tập tin giao diện**: `ui/components/sidebar.py`, `ui/components/data_tab.py`, `ui/main_window.py`.
- **Tập tin xử lý Engine**: `core/slip_printer_engine.py:827-1012`.
- **Các thành phần UI trực tiếp quan sát được**:
  1. *Ô chọn File PDF mẫu (Template)*: `ui/components/sidebar.py:35`
     - Entry: `self.app_state.template_var`
     - Nút "Chọn": `self.controller.pick_template_pdf`
  2. *Ô chọn Thư mục đầu ra*: `ui/components/sidebar.py:36`
     - Entry: `self.app_state.output_dir_var`
     - Nút "Chọn": `self.controller.pick_output_dir`
  3. *Ô Tên file đầu ra*: `ui/components/sidebar.py:41-43`
     - Entry: `self.app_state.output_name_var` (Mặc định: `YYMMDD_HHMMSS.pdf`)
  4. *Nút hành động chính "Tạo PDF"*: `ui/components/sidebar.py:64-74`
     - Widget: `self.generate_button = ctk.CTkButton(self, text="Tạo PDF", height=48, font=ctk.CTkFont(size=16, weight="bold"), command=self.controller.start_generation, fg_color="#10B981")`
  5. *Nút "Mở PDF vừa tạo"*: `ui/components/sidebar.py:76-83`
     - `ctk.CTkButton(self, text="Mở PDF vừa tạo", command=self.controller.open_generated_pdf, ...)`
  6. *Khung xem trước trang in (Preview Frame)*: `ui/components/data_tab.py:206-234`
     - Label ảnh preview: `self.preview_image_label` (hiển thị `self.app_state.current_preview_image`)
     - Hộp hiển thị chuỗi QR: `self.qr_payload_box`
     - Nút "🔄 Làm mới xem trước": `self.refresh_preview_image`
  7. *Thanh tiến trình & Nhật ký*: `ui/main_window.py:178-185`
     - `self.progress = ctk.CTkProgressBar(footer, height=10)`
     - `self.log_box = ctk.CTkTextbox(footer, height=45)`
- **Quy trình ghép & dàn trang in A4**:
  - Bước 1: Validate dữ liệu và đăng ký khóa `(po, po_detail, po_sub, box)` vào SQLite `po_registry` để chống in trùng.
  - Bước 2: Tạo lớp vẽ ReportLab canvas chứa 2 mã QR (mã đầy đủ và mã 122 ký tự) cùng các trường văn bản theo layout.
  - Bước 3: Ghép lớp vẽ với `template.pdf` theo từng lô 500 bản ghi (`BATCH_SIZE = 500`) để tối ưu bộ nhớ RAM.
  - Bước 4: Cắt góc phần tư trên-phải (EDI label: `558.6, 0.0, 841.92, 287.76` pt) và dàn đều **4 tem trên 1 trang A4 khổ dọc** (2 cột x 2 dòng, `EDI_PER_A4_PAGE = 4`).
  - Bước 5: Nén file đầu ra bằng PyMuPDF (`garbage=4, deflate=True`) và gửi thông báo hoàn tất cùng số trang A4: `(record_count + 3) // 4`.

---

## 2. Logic Chain (Chuỗi suy luận từ quan sát đến thiết kế Tutorial)

```
[Mục tiêu: Xây dựng Interactive Tutorial Overlay cho 4 bước nghiệp vụ cốt lõi]
                             │
     ┌───────────────────────┼───────────────────────┬───────────────────────┐
     ▼                       ▼                       ▼                       ▼
【Bước 1: Nạp Excel】   【Bước 2: Quét QR】     【Bước 3: Auto PO】    【Bước 4: Tạo PDF】
- Widget mục tiêu:      - Widget mục tiêu:      - Widget mục tiêu:     - Widget mục tiêu:
  * Nút "Chọn" Excel      * Nút "⚡ Quét QR"      * Ô "PO (tự sinh)"     * Nút "Tạo PDF"
  * Nút "Import Excel"      (Sidebar hoặc Form)   * Ô "PO chi tiết"      * Khung xem trước
  * Bảng `preview_tree`   * Segmented 3 chế độ    * Nút "➕ Thêm mới"    * Nút "Mở PDF"
- Hướng dẫn người dùng:   * Ô nhập QR súng bắn    * Nút "📋 Điền mẫu"  - Hướng dẫn người dùng:
  * File mẫu chuẩn từ     * Nút "➕ Thêm ds in" - Hướng dẫn người dùng:  * Xem trước tem & QR
    dòng 28.             - Hướng dẫn người dùng:  * Cơ chế sinh mã 10    * Tự động dàn 4 tem
  * Cảnh báo dòng đỏ      * Phân tách (10010..)    chữ số 11YYMMDDNN     trên 1 trang A4.
    khi trùng mã EDI.     * Hoàn kho (11010..)   * Dùng chung 1 PO     * Mở file để in ra máy
                          * Bóc tách tem gốc.      cho lô nhiều Box.     in Kyocera/A4.
```

### Bảng Tổng Hợp Chi Tiết Đối Tượng Widget Cho 4 Bước Tutorial:

| Bước Tutorial | Tên Bước Hướng Dẫn | Widget Target (Cần Highlight / Tooltip) | Vị Trí / Đường Dẫn Code | Biến / Callback Kèm Theo |
| :--- | :--- | :--- | :--- | :--- |
| **Bước 1** | **Nạp dữ liệu từ file Excel** | `sidebar.excel_field_row` & Nút `Import từ Excel` | `ui/components/sidebar.py:34, 45-52` | `app_state.excel_var`<br>`controller.import_from_excel` |
| | | Bảng dữ liệu `preview_tree` | `ui/components/data_tab.py:177` | `app_state.records`<br>`app_state.preview_index_map` |
| **Bước 2** | **Công cụ Quét QR & 3 Chế độ** | Nút `⚡ Quét QR` (Sidebar hoặc Form) | `ui/components/sidebar.py:54`<br>`ui/components/data_tab.py:51` | `controller.open_qr_scan_dialog` |
| | | `QRScanDialog.mode_segment` (3 Chế độ) | `ui/components/qr_scan_dialog.py:94` | `mode_var` (`split`, `return`, `decode`) |
| | | `QRScanDialog.scan_entry` (Ô quét mã) | `ui/components/qr_scan_dialog.py:115` | `scan_input_var`<br>`process_scanned_code` |
| | | `QRScanDialog.payload_box` (Chuỗi 129 ký tự) | `ui/components/qr_scan_dialog.py:184` | `char_count_var` |
| **Bước 3** | **Tạo mã Auto PO thông minh** | Cụm ô PO (`po_entry`, `po_detail`, `po_sub`) | `ui/components/data_tab.py:86-106` | `app_state.po_var`<br>`app_state.po_detail_var` |
| | | Nút `➕ Thêm mới` & Nút `📋 Điền mẫu` | `ui/components/data_tab.py:127, 154` | `controller.add_record`<br>`controller.fill_sample_data` |
| | | Tab `Lịch sử Đăng ký EDI` (KPI `next_po`) | `ui/components/history_tab.py:31` | `app_state.history_next_po_var` |
| **Bước 4** | **Xem trước & Tạo file in PDF** | Khung xem trước `preview_image_label` | `ui/components/data_tab.py:216` | `app_state.current_preview_image` |
| | | Nút chính `Tạo PDF` (`generate_button`) | `ui/components/sidebar.py:64` | `controller.start_generation` |
| | | Nút `Mở PDF vừa tạo` | `ui/components/sidebar.py:76` | `controller.open_generated_pdf` |

---

## 3. Caveats (Các điểm cần lưu ý kỹ thuật khi triển khai Tutorial Overlay)

1. **CustomTkinter Widget Bounding Box**:
   - Các widget của CustomTkinter (như `CTkButton`, `CTkEntry`, `CTkFrame`) là wrapper trên nền Tkinter Canvas.
   - Để lấy tọa độ chính xác của widget trên màn hình cho lớp phủ Overlay: cần gọi `widget.winfo_rootx()`, `widget.winfo_rooty()`, `widget.winfo_width()`, `widget.winfo_height()` sau khi `update_idletasks()` đã hoàn tất.
2. **Tab Switching & Visibility**:
   - `DataTabPanel`, `LayoutTabPanel`, `HistoryTabPanel` nằm trong `ttk.Notebook`. Nếu một bước tutorial trỏ vào widget thuộc tab khác, hệ thống Tutorial Engine phải chủ động chuyển tab (`notebook.select(...)`) trước khi highlight widget.
3. **Modal Dialog (QR Scanner)**:
   - `QRScanDialog` là một cửa sổ `CTkToplevel` modal riêng biệt. Tutorial cho bước 2 có thể giải thích trực tiếp nút bấm trên màn hình chính, hoặc hiển thị ảnh mockup / hướng dẫn tương tác trong dialog khi người dùng mở lên.
4. **Trạng thái cấu hình lần đầu mở App**:
   - Trạng thái hoàn thành tutorial cần được lưu trong `user_settings.json` (tại `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`) để không làm phiền người dùng ở các lần khởi động tiếp theo trừ khi họ chủ động bấm nút "💡 Hướng dẫn".

---

## 4. Conclusion (Kết luận đánh giá)

1. Toàn bộ 4 luồng nghiệp vụ cốt lõi đã được khảo sát tường tận từ UI widget, state variable, controller callback cho đến logic nền tảng của PO Registry và PDF Rendering Engine.
2. Các widget mục tiêu đều có định danh rõ ràng, dễ dàng truy xuất thông qua cấu trúc đối tượng `SlipPrinterApp` -> `sidebar`, `data_tab`, `history_tab`, `layout_tab` và `controller`.
3. Kịch bản hướng dẫn người dùng đã có đầy đủ dữ liệu ngữ nghĩa chuẩn xác theo đúng quy trình thực tế của nhà máy:
   - Nạp Excel dòng 28 -> Kiểm tra bảng -> Quét QR phân tách/hoàn kho -> Tự sinh PO 11YYMMDDNN -> Dàn trang in 4 tem A4.
4. Tài liệu này cung cấp đầy đủ cơ sở kỹ thuật để đội ngũ triển khai bắt tay vào xây dựng module Interactive Tutorial UI Overlay.

---

## 5. Verification Method (Phương pháp kiểm chứng độc lập)

1. **Kiểm tra cú pháp & tính hợp lệ của mã nguồn**:
   ```powershell
   python -m py_compile slip_printer_app.py ui/main_window.py ui/app_controller.py ui/app_state.py ui/components/sidebar.py ui/components/data_tab.py ui/components/qr_scan_dialog.py ui/components/history_tab.py ui/components/layout_tab.py core/slip_printer_engine.py core/po_registry.py
   ```
2. **Chạy kiểm thử đơn vị hiện có của dự án**:
   ```powershell
   pytest tests/
   ```
3. **Kiểm tra trực tiếp các widget bằng mã lệnh Python interactive hoặc health-check**:
   ```powershell
   python slip_printer_app.py --health-check
   ```
