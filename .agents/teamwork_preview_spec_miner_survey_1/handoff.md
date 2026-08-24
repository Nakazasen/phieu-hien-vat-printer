# Báo Cáo Khai Thác Đặc Tả Kỹ Thuật (Specification Mining Report)
## Tính năng Hướng Dẫn Sử Dụng Tương Tác (Interactive Step-by-Step Tutorial) & Cơ Chế Lưu Trữ Cấu Hình

**Mã Agent**: `teamwork_preview_spec_miner_survey_1`  
**Archetype**: `teamwork_preview_spec_miner`  
**Dự án**: Phần mềm In Phiếu Hiện Vật (`InPhieuHienVat`)  
**Tài liệu tham chiếu**: `ORIGINAL_REQUEST.md`, `core/runtime_paths.py`, `core/slip_printer_engine.py`, `ui/main_window.py`, `ui/app_controller.py`, `ui/app_state.py`, `ui/components/*`.

---

## Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Configuration Persistence | `user_settings.json` Store | Lưu trữ cấu hình giao diện và tùy chọn người dùng (giao diện Sáng/Tối, trạng thái đã xem hướng dẫn `has_seen_tutorial`, cờ tự động gợi ý `auto_suggest_tutorial`). Lưu tại `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json`. | JSON key-value pairs (dict) | File `user_settings.json` được ghi định dạng UTF-8 indent=2 | Trả về giá trị mặc định an toàn nếu file hỏng hoặc không tồn tại | `ui/main_window.py:401-423`, `core/runtime_paths.py:52-61` |
| 2 | Configuration Persistence | `layout_config.json` Store | Cấu hình tọa độ in ấn tem PDF và vị trí mã QR (font, qr_positions, text_positions). Được nạp khi khởi động và sao chép an toàn từ bundle sang data_dir. | Đường dẫn file hoặc cấu hình dict | File `layout_config.json` | Tự động khôi phục cấu hình mặc định `get_default_layout_config()` nếu thiếu | `core/slip_printer_engine.py:317-337`, `core/runtime_paths.py:140-143` |
| 3 | Tutorial State Management | First-Launch Detection & Auto-Prompt | Phát hiện người dùng mới khởi chạy ứng dụng lần đầu (khi `has_seen_tutorial` là False hoặc chưa tồn tại trong `user_settings.json`) để hiển thị hộp thoại gợi ý chạy tutorial tự động sau khi giao diện đã sẵn sàng (100-300ms sau mainloop). | Cờ `has_seen_tutorial`, `auto_suggest_tutorial` trong `user_settings.json` | Modal thông báo gợi ý xem hướng dẫn [Xem ngay / Để sau / Không nhắc lại] | Bỏ qua nếu cấu hình bị lỗi, không chặn luồng khởi động chính | `ORIGINAL_REQUEST.md:30`, `ui/main_window.py:65-68` |
| 4 | UI Placement | "💡 Hướng dẫn (Tutorial)" Trigger Button | Nút kích hoạt hướng dẫn thủ công tại thanh Header điều khiển trên cùng góc phải (`header -> preview_controls` cạnh nút "Kiểm tra bản cập nhật"), có màu nhấn nổi bật (#F59E0B Amber Gold) để người dùng có thể mở lại hướng dẫn bất kỳ lúc nào. | Click chuột / Phím tắt | Khởi chạy Interactive Tutorial Overlay từ Bước 1 | Vô hiệu hóa hoặc debounce khi tutorial đang chạy để tránh mở lặp | `ui/main_window.py:107-150`, `ORIGINAL_REQUEST.md:29-31` |
| 5 | Interactive UI Overlay Engine | Dynamic Spotlight & Scrim Layer | Lớp phủ làm tối màn hình (scrim) kèm cơ chế "khoét sáng" (spotlight highlight) làm nổi bật widget mục tiêu của từng bước, gắn kèm tooltip bong bóng chỉ dẫn tương tác. | Widget mục tiêu, tiêu đề bước, nội dung hướng dẫn, vị trí tooltip (top/bottom/left/right) | Canvas/Frame scrim overlay trên cửa sổ chính, Spotlight viền sáng, Card Tooltip nổi | Tự động căn chỉnh lại nếu cửa sổ bị resize; fallback về modal trung tâm nếu widget không tìm thấy | `ORIGINAL_REQUEST.md:19-21`, `ui/main_window.py:81-100` |
| 6 | Tutorial Content (Step 1) | Hướng dẫn Import Excel | Bước 1 hướng dẫn nạp dữ liệu từ file Excel (`.xlsx`) hoặc sử dụng file mẫu mặc định (`DummySlip.xlsx`), kiểm tra bảng xem trước danh sách tem. | Focus vào nút "Import từ Excel" và ô chọn đường dẫn tại Sidebar | Spotlight trên Sidebar Import Button, Tooltip hướng dẫn thao tác nạp Excel | Hiển thị thông báo nếu file Excel không hợp lệ | `ORIGINAL_REQUEST.md:24`, `ui/components/sidebar.py:34-53` |
| 7 | Tutorial Content (Step 2) | Hướng dẫn Quét QR Đa Năng | Bước 2 hướng dẫn mở công cụ Quét QR thông minh và giải thích 3 chế độ nghiệp vụ: Phân tách (分割 - tách thùng lớn ra nhiều hộp nhỏ), Hoàn kho (戻入 - thêm tiền tố R và tăng số lần hoàn), Bóc tách / Nhập tem (chuỗi 129 ký tự tiêu chuẩn). | Focus vào nút `⚡ Quét QR` trên Sidebar / Data Tab | Spotlight trên nút Quét QR, Tooltip giải thích 3 chế độ nghiệp vụ | Chặn thao tác nền trong khi tutorial đang mở | `ORIGINAL_REQUEST.md:25`, `ui/components/qr_scan_dialog.py:24-105` |
| 8 | Tutorial Content (Step 3) | Hướng dẫn Nhập Liệu & Tự Sinh Mã PO (Auto PO) | Bước 3 hướng dẫn nhập trực tiếp trên Form Data Tab (Mã hàng, SL thùng, Box, Rev) và cơ chế tự động cấp phát số PO duy nhất từ SQLite Registry (`PORegistry`), kiểm tra chống trùng lặp mã EDI. | Focus vào khung Form Nhập Liệu trên Tab "Dữ liệu và xem trước" | Tự động chuyển Tab sang Data Tab nếu đang ở tab khác, Spotlight trên Form Frame | Khóa trường Lot ngăn nhập sai định dạng | `ORIGINAL_REQUEST.md:26`, `ui/components/data_tab.py:33-120`, `core/po_registry.py` |
| 9 | Tutorial Content (Step 4) | Hướng dẫn Tạo PDF & In Ấn | Bước 4 hướng dẫn bấm nút "Tạo PDF" (màu xanh lục Emerald), kiểm tra khung Xem trước trang in (Preview Frame 4 tem/trang A4) và nút "Mở PDF vừa tạo". | Focus vào nút "Tạo PDF" tại Sidebar và Khung Preview | Spotlight trên nút Tạo PDF và Preview Image Label, Tooltip hướng dẫn xuất file và in ấn | Báo lỗi thân thiện nếu chưa có dữ liệu hoặc thiếu template | `ORIGINAL_REQUEST.md:27`, `ui/components/sidebar.py:64-83`, `ui/components/data_tab.py:204-220` |
| 10 | Tutorial Navigation & Lifecycle | Next / Back / Skip / Finish & Cleanup | Điều hướng tuần tự giữa các bước (1 ➔ 2 ➔ 3 ➔ 4), hỗ trợ quay lại (Back), bỏ qua (Skip/Esc) và hoàn tất (Finish). Đảm bảo giải phóng toàn bộ overlay, unbind event listeners, trả lại trạng thái tương tác hoàn toàn cho ứng dụng. | Nút [Tiếp tục], [Quay lại], [Bỏ qua (Skip)], phím Escape | Chuyển đổi mượt mà giữa các bước, hủy overlay ngay lập tức khi Skip | Debounce ngăn chặn click liên tục gây giật lag hoặc trùng lặp luồng | `ORIGINAL_REQUEST.md:36-38`, `ui/app_controller.py` |

---

## Edge Cases

| # | Feature | Input / Trigger | Observed / Expected Behavior |
|---|---------|-----------------|-----------------------------|
| 1 | Interactive Overlay | Người dùng phóng to, thu nhỏ (Resize) hoặc tối đa hóa (Maximize) cửa sổ trong lúc Tutorial đang mở | Tọa độ `winfo_rootx()`, `winfo_rooty()` của widget mục tiêu thay đổi. Overlay phải lắng nghe sự kiện `<Configure>` của root window để tự động tính toán lại vị trí spotlight và định vị lại tooltip bubble mượt mà. |
| 2 | Interactive Overlay | Cửa sổ bị thu nhỏ xuống Taskbar (Minimize / Iconify) hoặc phục hồi (Restore) | Không được làm rơi rụng overlay riêng lẻ trên màn hình Desktop. Nếu dùng Canvas/Frame trên root thì tự động ẩn theo root; nếu dùng Toplevel thì phải đặt `transient(root)` và xử lý sự kiện `<Unmap>` / `<Map>` an toàn mà không sinh lỗi `TclError`. |
| 3 | Interactive Overlay | Màn hình có độ phân giải cao (High DPI) hoặc tỉ lệ phóng to màn hình Windows (125%, 150%, 200%) | Tọa độ widget phải được tính toán tương đối theo hệ tọa độ của root window (`x = target.winfo_rootx() - root.winfo_rootx()`, `y = target.winfo_rooty() - root.winfo_rooty()`), đảm bảo spotlight bao khít chính xác widget trên mọi mức DPI scaling của CustomTkinter. |
| 4 | Step Switching | Bước hướng dẫn nằm trên Tab khác với Tab hiện tại (ví dụ: Bước 3 cần highlight Form Data Tab nhưng người dùng đang đứng ở Tab "Chỉnh sửa Layout PDF") | Tutorial Engine phải tự động kích hoạt chuyển Tab (`notebook.select(tab_index)`), gọi `root.update_idletasks()` để widget render đầy đủ, sau đó mới tính toán tọa độ và vẽ spotlight. |
| 5 | Input Debounce | Người dùng nhấn liên tục hoặc spam chuột cực nhanh vào nút "Tiếp tục" / "Quay lại" / "Bỏ qua" | Sử dụng cờ khóa chuyển trạng thái (`is_transitioning = True`) trong suốt chu kỳ chuyển bước, loại bỏ hoàn toàn các event thừa để ngăn chặn crash mainloop, duplicate overlay, hoặc lệch bước. |
| 6 | Modal Grab & Protection | Người dùng cố tình click chuột vào các nút chức năng phía sau lớp mờ (như nút "Xóa dòng", "Tạo PDF", nhập text) | Lớp phủ scrim overlay phải chặn toàn bộ tương tác chuột và phím (mouse interceptor / `grab_set()`) nhằm bảo vệ an toàn tuyệt đối cho dữ liệu nghiệp vụ, chỉ cho phép tương tác với các nút trên hộp thoại Tutorial. |
| 7 | Skip & Emergency Exit | Người dùng nhấn nút "Bỏ qua (Skip)", bấm icon đóng X, hoặc nhấn phím `Escape` | Phải dọn dẹp sạch sẽ (destroy overlay/tooltips), gỡ bỏ (unbind) toàn bộ phím tắt và sự kiện `<Configure>`, phục hồi 100% quyền điều khiển cho giao diện chính ngay lập tức. |
| 8 | Scrollable Container | Widget mục tiêu nằm trong `CTkScrollableFrame` (như nút Tạo PDF hoặc trường nhập liệu dài) bị cuộn khuất khỏi tầm nhìn | Tutorial Engine phải tự động cuộn khung chứa (`scroll_into_view` hoặc `target.focus_set()`) để đưa widget vào vùng nhìn thấy trước khi tính tọa độ spotlight. |
| 9 | Theme Switch | Ứng dụng chạy ở chế độ Sáng (Light Mode), Tối (Dark Mode) hoặc Hệ thống (System) | Giao diện Tooltip card, text màu sắc và viền spotlight phải sử dụng tuple màu thích ứng (`fg_color=("gray95", "gray18")`, `text_color=("gray10", "gray90")`, viền `#2563EB` hoặc `#10B981`) đảm bảo độ tương phản cao và chữ đọc rõ ràng trên mọi giao diện. |
| 10 | Target Missing Fallback | Widget mục tiêu bị ẩn, bị hủy hoặc không tìm thấy tại thời điểm chạy bước | Tutorial Engine không được làm crash ứng dụng; tự động chuyển sang chế độ hiển thị Card chỉ dẫn nổi ở vị trí trung tâm màn hình và tiếp tục cho phép bấm "Tiếp tục" / "Bỏ qua". |

---

## 5-Component Handoff Protocol

### 1. Observation
1. **Khảo sát Cơ chế Lưu trữ Cấu hình**:
   - `core/runtime_paths.py` (dòng 52-68, 127-156): Xác lập thư mục dữ liệu người dùng tại `%LOCALAPPDATA%\InPhieuHienVatData` (hoặc `INPHIEUHIENVAT_DATA_DIR`). Thư mục này nằm ngoài thư mục cài đặt phiên bản (`apps/<version>/`), do đó không bị xóa hay ghi đè khi nâng cấp phần mềm.
   - `core/slip_printer_engine.py` (dòng 317-337): Quản lý file `layout_config.json` với các hàm `ensure_layout_config_file()`, `load_layout_config()`, `save_layout_config()`. File này chỉ chứa cấu hình tọa độ in tem ReportLab (`font`, `qr_positions`, `text_positions`).
   - `ui/main_window.py` (dòng 400-424): Đã có sẵn cơ chế đọc/ghi cấu hình tùy chọn người dùng qua file `user_settings.json` tại `self.app_state.paths.data_dir / "user_settings.json"`, hiện đang lưu `appearance_mode`.
   - `core/po_registry.py`: Quản lý SQLite database `po_registry.db` phục vụ lịch sử cấp phát mã PO và chống trùng lặp mã EDI.
2. **Khảo sát Vị trí Giao diện (UI Layout)**:
   - `ui/main_window.py` (dòng 106-150): Phần Header của ứng dụng gồm 2 phần: bên trái là tiêu đề và trạng thái (`summary_var`, `status_var`), bên phải là cụm điều khiển `preview_controls` chứa `theme_menu` (OptionMenu), `preview_limit_var` (ComboBox), và nút "Kiểm tra bản cập nhật" (Button width=150, height=28).
   - `ui/components/sidebar.py` (dòng 13-84): Chứa các trường chọn file (Excel, Template, Output) và các nút hành động cốt lõi ("Import từ Excel", " Quét QR", "Tạo PDF", "Mở PDF vừa tạo").
   - `ui/components/data_tab.py` (dòng 17-220): Chứa Form nhập liệu 2 cột, các nút thao tác ("Thêm mới", "Cập nhật", "Xóa dòng", "Điền mẫu", "Xóa form"), Bảng Treeview dữ liệu tem, và Khung Preview bản in PDF bên phải.
   - `ui/components/qr_scan_dialog.py` (dòng 80-195): Hộp thoại Modal quét QR với 3 chế độ: "Phân tách (分割)", "Hoàn kho (戻入)", "Bóc tách / Nhập tem".

### 2. Logic Chain
1. **Lựa chọn Nơi Lưu Trữ Trạng Thái Tutorial (`user_settings.json`)**:
   - `layout_config.json` chỉ phục vụ tọa độ in ReportLab của tài liệu PDF. Việc chèn cờ tutorial vào `layout_config.json` sẽ làm ô nhiễm schema in ấn, dễ gây lỗi xác thực dữ liệu khi vẽ canvas.
   - `user_settings.json` đã được thiết kế và triển khai trong `ui/main_window.py` cho các thiết lập của người dùng (`appearance_mode`). Việc bổ sung các trường `has_seen_tutorial` (bool), `auto_suggest_tutorial` (bool), `tutorial_version` (int) vào `user_settings.json` là giải pháp chuẩn mực kiến trúc nhất (Single Responsibility Principle & Clean Code).
2. **Xác định Vị trí Tối Ưu cho Nút "💡 Hướng dẫn (Tutorial)"**:
   - Vị trí thanh Header góc trên bên phải (`preview_controls` trong `ui/main_window.py`) là vị trí tiêu chuẩn của ứng dụng desktop: luôn luôn hiển thị và có thể bấm được ở bất kỳ Tab nào ("Dữ liệu", "Layout", "Lịch sử"), không chiếm không gian thao tác nghiệp vụ ở Sidebar hay làm hẹp bảng dữ liệu.
   - Nút được gán màu vàng hổ phách/amber (#F59E0B) tạo điểm nhấn nhận diện cao (Von Restorff Effect), phân biệt rõ với nút "Kiểm tra bản cập nhật" và các nút nghiệp vụ màu xanh lá/xanh dương.
3. **Kịch bản Hướng dẫn 4 Bước Cốt Lõi**:
   - Bước 1 (Nạp Excel): Gắn spotlight vào Sidebar `File Excel` / `Import từ Excel`.
   - Bước 2 (Quét QR Nghiệp vụ): Gắn spotlight vào nút `⚡ Quét QR` và giải thích 3 nghiệp vụ Phân tách · Hoàn kho · Bóc tách.
   - Bước 3 (Nhập liệu & Auto PO): Tự động chuyển về Data Tab, gắn spotlight vào Form Nhập Liệu, giải thích tính năng tự cấp phát số PO không trùng lặp.
   - Bước 4 (Tạo PDF & In Ấn): Gắn spotlight vào nút `Tạo PDF` màu xanh lục và khung Xem trước trang in bên phải.

### 3. Caveats
- Trên hệ điều hành Windows với Tkinter/CustomTkinter, việc tạo hiệu ứng trong suốt (Alpha transparency) bằng `CTkToplevel` phụ thuộc vào trình quản lý cửa sổ DWM. Phương án tối ưu và an toàn nhất là sử dụng một `CTkFrame` / `tk.Canvas` scrim overlay phủ trực tiếp lên cửa sổ chính (`place(x=0, y=0, relwidth=1, relheight=1)`), kết hợp với một Tooltip Card (`CTkFrame`) nổi với z-order cao nhất.
- Khi người dùng đang ở tab "Chỉnh sửa Layout PDF" hoặc "Lịch sử Đăng ký EDI", trước khi kích hoạt Bước 3 của Tutorial, hệ thống bắt buộc phải gọi lệnh chuyển tab `notebook.select(0)` và `root.update_idletasks()` để đảm bảo form Data Tab hiển thị và có tọa độ hợp lệ.

### 4. Conclusion
1. **Trạng thái Tutorial**: Lưu tại `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` với cấu trúc:
   ```json
   {
     "appearance_mode": "System",
     "has_seen_tutorial": false,
     "auto_suggest_tutorial": true
   }
   ```
2. **Vị trí Nút Trigger**: Đặt tại `header -> preview_controls` ở góc trên bên phải của `ui/main_window.py` với nhãn `💡 Hướng dẫn` (kích thước `120x28`, màu `#F59E0B`).
3. **Động cơ Tutorial Overlay**: Thiết kế module `ui/components/tutorial_overlay.py` với lớp `InteractiveTutorialController` / `TutorialOverlay` quản lý scrim canvas, highlight spotlight, tooltip card điều hướng [Quay lại], [Tiếp tục], [Bỏ qua (Skip)], cùng cơ chế bắt sự kiện resize, DPI scaling, và cleanup an toàn.

### 5. Verification Method
1. **Kiểm tra Lưu trữ & Khởi động**:
   - Xóa hoặc đổi `has_seen_tutorial: false` trong `user_settings.json` ➔ Khởi động ứng dụng ➔ Xác minh hộp thoại gợi ý hướng dẫn xuất hiện tự động.
   - Bấm "Bỏ qua (Không nhắc lại)" hoặc hoàn thành 4 bước ➔ Kiểm tra `user_settings.json` được cập nhật `has_seen_tutorial: true`.
2. **Kiểm tra Giao diện & Spotlight**:
   - Bấm nút `💡 Hướng dẫn` ở góc trên bên phải ➔ Lớp phủ scrim xuất hiện, widget ở từng bước (Import Excel ➔ Quét QR ➔ Form Nhập Liệu & Auto PO ➔ Tạo PDF & Preview) được spotlight chính xác.
3. **Kiểm tra Edge Cases**:
   - Phóng to/thu nhỏ cửa sổ khi đang ở bước bất kỳ ➔ Vị trí spotlight và tooltip bám sát widget mục tiêu.
   - Nhấn phím `Escape` hoặc nút `Bỏ qua (Skip)` ➔ Lớp phủ đóng lập tức, giao diện phục hồi trạng thái tương tác bình thường không có lỗi rò rỉ bộ nhớ hoặc timer treo.
