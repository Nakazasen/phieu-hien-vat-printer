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
