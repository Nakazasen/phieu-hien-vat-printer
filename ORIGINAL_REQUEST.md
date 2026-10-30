# Original User Request

## Initial Request — 2026-08-19T10:20:21Z

```markdown
# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team (Tạo tài liệu và UI)

Bổ sung tính năng "Hướng dẫn sử dụng" (User Guide/Manual) chi tiết cho toàn bộ chương trình In Phiếu Hiện Vật để người dùng cuối có thể dễ dàng tra cứu cách dùng phần mềm.

Working directory: D:\Sandbox\PM_in_lai_phieuhienvat
Integrity mode: development

## Requirements

### R1. Xây dựng Động cơ Interactive Tutorial (UI Overlay)
Thiết kế một cơ chế overlay UI trên nền CustomTkinter/Tkinter. Khi kích hoạt, màn hình chính sẽ bị làm mờ (hoặc phủ một lớp xám bán trong suốt). Tại mỗi bước hướng dẫn, một widget cụ thể (như nút Import, ô Quét QR) sẽ được "đánh sáng" (highlight) chồi lên trên lớp phủ, kèm theo một hộp thoại (tooltip) giải thích chức năng của nó và nút "Tiếp tục".

### R2. Nội dung các bước hướng dẫn
Soạn thảo kịch bản (kết nối với các widget thực tế trên giao diện) để hướng dẫn người dùng xuyên suốt các nghiệp vụ cốt lõi:
1. Cách nạp dữ liệu từ Excel.
2. Cách dùng công cụ Quét QR (Giải thích 3 chế độ: Phân tách, Hoàn kho, Bóc tách).
3. Cách Tạo mã Auto PO.
4. Cách Tạo và In file PDF.

### R3. Nút kích hoạt & Trải nghiệm
Thêm một nút "💡 Hướng dẫn (Tutorial)" ở vị trí dễ thấy trên màn hình chính (ví dụ: góc trên cùng). Đồng thời, lưu trạng thái vào file cấu hình (ví dụ `layout_config.json` hoặc config riêng) để phần mềm tự động gợi ý chạy tutorial trong lần mở app đầu tiên của người dùng mới.

## Acceptance Criteria

### Xác minh Hiển thị & Kỹ thuật
- [ ] Chạy giả lập UI (hoặc Unit Test) chứng minh cơ chế Overlay hoạt động: Lớp phủ được tạo ra và toạ độ của widget được highlight tính toán chính xác để không che khuất phần tử cần hướng dẫn.
- [ ] Chuyển qua lại giữa các bước (Next/Back) hoạt động trơn tru, không làm treo giao diện chính (Mainloop).
- [ ] Bấm nút "Bỏ qua (Skip)" phải xoá hoàn toàn lớp overlay và trả lại giao diện bình thường ngay lập tức.

### Xác minh Nội dung
- [ ] Kịch bản đi qua ít nhất 4 bước chính trị giá trị nhất của phần mềm bằng ngôn ngữ tiếng Việt dễ hiểu.
```

## Follow-up — 2026-09-22T02:44:40Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team (Điều tra, làm giàu spec PROJECT.md, hiện thực và kiểm thử hồi quy)

Nâng cấp phần mềm In Phiếu Hiện Vật (InPhiếuHiệnVật): Tích hợp mã vạch 1D (Barcode Code128 mã hóa 10 ký tự mã linh kiện) lên tem EDI theo mẫu After (đặt ngay phía trên mã QR, chỉ hiện vạch barcode không kèm text chân) và chuyển đổi cố định 100% sang bố cục dàn trang in 6 tem / 1 tờ A4 (2 cột × 3 hàng, thay thế hẳn cơ chế 4 tem cũ). Toàn bộ đặc tả kỹ thuật phải được làm giàu trực tiếp vào spec hiện có (`PROJECT.md` và `layout_config.json`), không tạo file spec dư thừa.

Working directory: D:\Sandbox\PM_in_lai_phieuhienvat
Integrity mode: development

## Requirements

### R1. Tích hợp Barcode 1D mã linh kiện lên tem EDI
- Sử dụng thư viện `reportlab.graphics.barcode.code128` để sinh mã vạch 1D Code128 từ 10 ký tự mã linh kiện (`record.item_code[:10]`).
- Bố trí tại vị trí góc dưới bên phải trên tem EDI, ngay phía trên mã QR (như hình mẫu After).
- Chỉ hiển thị thanh mã vạch, không hiển thị dòng text chữ số bên dưới barcode (`humanReadable=False` / không vẽ text phụ).
- Khai báo và quản lý tọa độ, kích thước (`barWidth`, `barHeight`) trong `layout_config.json`, hỗ trợ `list_layout_items()` và `update_layout_item()` để có thể tương tác/xem trên giao diện Layout Tab và Canvas Preview.

### R2. Chuyển đổi cố định bố cục in sang 6 tem / 1 tờ A4
- Cập nhật module `core/slip_printer_engine.py`: Chuyển đổi hằng số và thuật toán từ 4 tem/trang (`EDI_COLUMNS = 2, EDI_ROWS = 2, EDI_PER_A4_PAGE = 4`) thành 6 tem/trang (`EDI_COLUMNS = 2, EDI_ROWS = 3, EDI_PER_A4_PAGE = 6`).
- Tính toán kích thước destination box trên khổ A4 portrait sao cho vừa vặn cân đối, bảo đảm tỷ lệ gốc của tem, khoảng cách hàng/cột (`column_gap`, `row_gap`) và lề (`top_margin`, `left_margin`) thuận tiện cho công nhân cắt gập.
- Cập nhật hàm tính số trang in: Số trang xuất ra bằng $\lceil \text{số tem} / 6 \rceil$.

### R3. Làm giàu Spec hiện có (`PROJECT.md`) & Cập nhật Báo cáo Kaizen
- Không tạo file spec mới độc lập; cập nhật và bổ sung trực tiếp vào `PROJECT.md` (thêm Feature Inventory, Milestones, Interface Contracts cho Barcode 1D và 6-tem A4 Layout).
- Cập nhật số liệu và nội dung trong `docs/BAO_CAO_KAIZEN_IN_PHIEU_HIEN_VAT.md` để phản ánh bước tiến từ 4 tem/A4 lên 6 tem/A4 và tích hợp mã vạch 1D cho XNHH.

### R4. Đảm bảo kiểm thử tự động & Không lỗi hồi quy
- Bổ sung các unit/integration test trong `tests/` để xác minh:
  1. Mã Barcode 1D sinh ra đúng nội dung 10 ký tự mã linh kiện, không vỡ trang.
  2. File PDF sinh ra từ danh sách tem chia chính xác 6 tem trên mỗi trang A4.
  3. Tất cả các tính năng hiện có (quét QR, Auto PO, Import Excel, Live Preview, Export PDF) tiếp tục hoạt động bình thường, toàn bộ test suite `pytest` đạt 100% PASS.

## Acceptance Criteria

### Barcode 1D Verification
- [ ] Barcode 1D xuất hiện ở vị trí trên mã QR trên mỗi tem in và trên Canvas Preview.
- [ ] Barcode 1D chỉ chứa thanh vạch mã hóa chuỗi 10 ký tự mã linh kiện (không có text chân đè lên giao diện).
- [ ] Cấu hình barcode nằm trong `layout_config.json`, được nạp đúng vào `list_layout_items()` và có thể di chuyển bằng D-Pad nếu cần.

### 6-Slips per A4 Verification
- [ ] File PDF kết quả khi in từ 1..6 tem nằm trọn trong 1 trang A4; từ 7..12 tem tự động sang trang thứ 2 (chính xác 6 tem/trang).
- [ ] Tỷ lệ tem không bị méo mó, các trường thông tin (Mã hàng, Số lượng, PO, QR, Barcode) sắc nét, rõ ràng, căn lề chuẩn xác.

### Spec & Regression Verification
- [ ] `PROJECT.md` được làm giàu đầy đủ với các mục tính năng mới.
- [ ] `pytest tests/` chạy thành công 100% không phát sinh bất kỳ lỗi hồi quy nào.

## Follow-up — 2026-09-22T03:57:29Z

CRITICAL USER DIRECTIVE:
1. Do NOT package or release any new application version (DO NOT run package_app.py or build_installer.bat, do NOT bump release.json).
2. Do NOT commit or push changes to git repository.
3. Keep all modifications strictly in the local working directory so the user can directly test printing and scanning at the Oricon gate to verify if their laser scanners read Code 128 or if there is any conflict with Code 39 tags.

## Follow-up — 2026-09-23T14:43:41Z

Yêu cầu nâng cấp bố cục in tem và khổ giấy cho xưởng sản xuất:
1. **Khoảng cách khe hở đường dao (Blade Cut Clearance Margin):**
   - Hiện tại in 6 tem trên khổ A4 không có khe hở (0 pt gap), gây khó khăn khi cắt số lượng lớn bằng bàn cắt giấy dập cơ học.
   - Bổ sung khe hở giữa các tem từ 4.5mm -> 5.0mm (cả khe hở cột và hàng) để người dùng đi đường dao dập dễ dàng mà không bị phạm vào viền tem.
   - Bổ sung khe hở giữa các tem từ 4.5mm -> 5.0mm (cả khe hở cột và hàng) để người dùng đi đường dao dập dễ dàng mà không bị phạm vào viền tem. *(Lưu ý: Đề xuất ban đầu thăm dò 5.0mm cho cả hàng và cột trên A4; sau khi phân tích hình học vật lý không đủ chỗ nếu giữ 100% kích thước tem, yêu cầu này đã được chuẩn hóa và thay thế bởi Quyết định chốt Phương án 2 tại Mục 2 bên dưới: A4 khe cột 5.0mm & khe hàng 2.32mm; Letter khe cột & hàng 5.0mm).*
   - Hỗ trợ đường kẻ đứt mờ (hairline dashed cut lines) tại tâm các khe hở để hỗ trợ căn dao.
2. **Hỗ trợ đa khổ giấy A4 và Letter (Dual Paper Size Selection):**
   - Bổ sung tùy chọn chọn khổ giấy in A4 hoặc Letter trên giao diện để khi hết giấy A4, xưởng có thể dùng giấy Letter in thay thế.
   - **Quyết định chốt Phương án 2 (100% không co hình):**
     * **TUYỆT ĐỐI KHÔNG CO HÌNH:** Giữ nguyên 100% tỷ lệ gốc ($273.12 \times 276.24\text{ pt}$) để bảo đảm độ chính xác của mã vạch Oricon và máy quét XNHH.
     * **Khổ A4:** In 6 tem / trang (2 cột × 3 hàng). Khe hở cột $5.0\text{ mm}$, khe hở hàng $2.32\text{ mm}$ (dồn toàn bộ khoảng thừa chiều dài của A4 vào khe ngang).
     * **Khổ Letter:** In 4 tem / trang (2 cột × 2 hàng, do Letter ngắn hơn A4 17.6mm không đủ chứa 3 hàng tem gốc). Khe hở cột và hàng đều đạt chuẩn $5.0\text{ mm}$.
     * **Cảnh báo trực quan (`LetterWarningDialog`):** Bắt buộc hiển thị modal có hình ảnh minh họa kỹ thuật (`letter_explanation.png`) giải thích lý do in 4 tem khi người dùng chọn Letter.
   - Ghi nhớ tùy chọn khổ giấy vào cấu hình người dùng `user_settings.json`.
3. **Quy trình triển khai:**
   - Dùng Speckit để lên kế hoạch và thực hiện; ưu tiên làm giàu trực tiếp vào các tài liệu đặc tả hiện có (`PROJECT.md`, `ORIGINAL_REQUEST.md`).

## Follow-up — 2026-09-23 (Duplicate Export UX)

1. Before creating a PDF, check each non-empty `(PO, PO detail, PO sub, Box)` against the shared registry and against earlier rows in the current list.
2. If some rows were already exported or are repeated in the current list, explain the counts in plain Vietnamese and offer **Chỉ xuất tem mới** or **Hủy**. Keep every row in the user's data table.
3. If every row is already accounted for, explain that no PDF was created and that the data remains in the table.
4. Explain the existing red row highlight in the table. Keep the shared SQLite uniqueness check as the final guard if another workstation exports during the prompt.
5. Enrich the existing `PROJECT.md` feature inventory, R6 milestone, and interface contract. Do not create another specification file.

## Follow-up — 2026-09-23T16:53:48Z (/ui-ux-pro-max)

Nâng cấp UI/UX Pro Max theo quy chuẩn Speckit (làm giàu đặc tả hiện có, không tạo spec mới, bảo đảm 100% an toàn cho Core):
1. **Thanh Sidebar (Cấu trúc Card & Công thái học)**:
   - Gom cụm điều khiển thành 3 nhóm Card tinh tế: Khổ giấy in (ở đầu tiên), Dữ liệu & Xuất bản (Excel, Tạo PDF, Mở PDF), Cấu hình đầu ra (PDF mẫu, Thư mục, Tên file).
   - Nút hành động chính Tạo PDF nổi bật theo hiệu ứng Von Restorff (Emerald Green `#10B981`, chiều cao chuẩn 48px).
2. **Tab Dữ liệu (Trực quan hóa & Phím tắt)**:
   - Hiển thị badge thống kê động (Live Metrics Chip): số lượng tem và số trang dự kiến theo khổ in đã chọn.
   - Thêm trạng thái rỗng (Empty State) hướng dẫn người dùng khi chưa có dữ liệu.
   - Bổ sung phím tắt `<Delete>` xóa dòng trên Treeview, `<Return>` thêm dòng trên form.
3. **Hộp thoại Cảnh báo Letter (LetterWarningDialog)**:
   - Bắt phím `<Escape>` để hủy/đóng modal, `<Return>` để kích hoạt nút hành động an toàn, focus tự động.
4. **Cam kết an toàn tuyệt đối**:
   - Không thay đổi bất kỳ dòng mã nào trong thư mục `core/`. Toàn bộ test suite phải tiếp tục PASS 100%.

## Follow-up — 2026-09-23 (Việt hóa giao diện và thông báo lỗi)

- Việt hóa nhãn, hướng dẫn, trạng thái và thông báo lỗi do ứng dụng tạo để người dùng không phải đọc thuật ngữ kỹ thuật tiếng Anh.
- Không hiển thị nguyên văn lỗi từ Windows hoặc thư viện; thay bằng hướng dẫn ngắn gọn phù hợp với thao tác đang thực hiện.
- Giữ nguyên tên định dạng, mã nghiệp vụ và tên trường in chuẩn như PDF, Excel, QR, PO, Rev và `PACKAGE QTY`.
- Bổ sung yêu cầu vào hạng mục UI/UX R7 trong `PROJECT.md`; không tạo tài liệu đặc tả mới.
