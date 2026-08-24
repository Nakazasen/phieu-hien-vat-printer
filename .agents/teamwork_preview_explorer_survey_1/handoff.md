# Báo Cáo Khảo Sát Kiến Trúc Giao Diện UI & Động Cơ Overlay Hướng Dẫn

**Tác giả:** Codebase UI Explorer (`teamwork_preview_explorer_survey_1`)  
**Mã nhiệm vụ:** Survey UI Framework, Window Layout, Coordinates & Interactive Tutorial Overlay  
**Ngày báo cáo:** 2026-08-19  

---

## 1. Observation (Quan sát trực tiếp)

### 1.1. Cấu trúc Tệp & Điểm khởi nhập GUI
Qua khảo sát hệ thống mã nguồn tại `d:\Sandbox\PM_in_lai_phieuhienvat`, các tệp tin cấu thành giao diện chính gồm:

| Tệp tin | Vai trò | Lớp / Thành phần cốt lõi |
|---|---|---|
| `slip_printer_app.py` | Điểm khởi nhập chính (CLI & GUI entrypoint) | `main()`, xử lý `--health-check`, `--wait-for-pid`, khởi tạo `SlipPrinterApp` và gọi `app.mainloop()`. |
| `ui/main_window.py` | Cửa sổ ứng dụng chính (Master Window) | `SlipPrinterApp(ctk.CTk)`, kế thừa từ CustomTkinter root window, điều phối `AppState`, `AppController`, `SidebarPanel`, và `ttk.Notebook` chứa các tab. |
| `ui/app_controller.py` | Bộ điều phối nghiệp vụ & tương tác UI (Controller) | `AppController`, xử lý CRUD dòng tem, nhập Excel, sinh PO, nạp cấu hình layout, điều phối luồng nền tạo PDF và kiểm tra cập nhật. |
| `ui/app_state.py` | Quản lý trạng thái & biến phản ứng (State) | `AppState`, quản lý biến `ctk.StringVar`, danh sách bản ghi `records: list[SlipRecord]`, kết nối `PORegistry`, cấu hình `layout_config`, hàng đợi `event_queue`. |
| `ui/components/sidebar.py` | Thanh bên trái (Sidebar View) | `SidebarPanel(ctk.CTkScrollableFrame)`, chứa logo/tiêu đề, các trường chọn đường dẫn file (Excel, Template PDF, Output Dir), nút "Import từ Excel", nút "⚡ Quét QR", nút "Tạo PDF", nút "Mở PDF". |
| `ui/components/data_tab.py` | Tab 1: Dữ liệu & Xem trước (Data & Preview Tab) | `DataTabPanel(ctk.CTkFrame)`, chia 2 cột: Form nhập liệu 2 cột x 6 hàng + Bảng `ttk.Treeview` hiển thị dữ liệu (trái); Khung xem trước hình ảnh mẫu in + Chuỗi QR (phải). |
| `ui/components/layout_tab.py` | Tab 2: Chỉnh sửa Layout PDF | `LayoutTabPanel(ctk.CTkFrame)`, chia 2 cột: Bảng danh sách phần tử tọa độ (trái); Bộ điều hướng D-pad (Lên/Xuống/Trái/Phải), chọn bước nhảy (1mm/5mm/15mm), chỉnh kích thước và nút Lưu/Hủy/Reset (phải). |
| `ui/components/history_tab.py` | Tab 3: Lịch sử Đăng ký EDI | `HistoryTabPanel(ctk.CTkFrame)`, gồm 3 thẻ KPI tổng quan (Tổng mã, Hôm nay, PO tiếp theo), thanh tìm kiếm tra cứu, bảng `ttk.Treeview` lịch sử, nút xuất CSV. |
| `ui/components/qr_scan_dialog.py` | Cửa sổ Modal Quét & Bóc tách QR | `QRScanDialog(ctk.CTkToplevel)`, popup quét mã QR súng bắn/paste với 3 chế độ ("Phân tách (分割)", "Hoàn kho (戻入)", "Bóc tách / Nhập tem"). |
| `layout_config.json` | Cấu hình tọa độ in tem mẫu | Định nghĩa tọa độ X, Y, font, width, height của 2 vị trí QR và 23 trường text trên phôi tem. |

---

### 1.2. Khởi tạo CustomTkinter, Cửa sổ Master & Phân cấp Frame (Widget Hierarchy)

1. **Khởi tạo Master Window (`ui/main_window.py:31-68`):**
   ```python
   class SlipPrinterApp(ctk.CTk):
       def __init__(self):
           super().__init__()
           self.title(APP_TITLE)
           screen_w = self.winfo_screenwidth()
           screen_h = self.winfo_screenheight()
           target_w = min(1400, max(1000, screen_w - 60))
           target_h = min(900, max(700, screen_h - 80))
           pos_x = max(0, (screen_w - target_w) // 2)
           pos_y = max(0, (screen_h - target_h) // 2)
           self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
           self.minsize(1000, 700)
   ```
2. **Cấu trúc Bộ chia (PanedWindow Layout) (`ui/main_window.py:81-101`):**
   ```python
   self.splitter = ttk.Panedwindow(self, orient="horizontal")
   self.splitter.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

   sidebar_host = ctk.CTkFrame(self.splitter, corner_radius=14, fg_color=("gray94", "gray14"))
   self.sidebar = SidebarPanel(sidebar_host, self.controller, corner_radius=14, fg_color=("gray94", "gray14"))
   content = ctk.CTkFrame(self.splitter, corner_radius=14)

   self.splitter.add(sidebar_host, weight=0)
   self.splitter.add(content, weight=1)
   ```
3. **Phân cấp bên trong `content` (`ui/main_window.py:102-186`):**
   - **Hàng 0 (Header):** Tiêu đề tóm tắt (`summary_var`), trạng thái (`status_var`), cụm `preview_controls` (Menu đổi giao diện Sáng/Tối/Hệ thống, ComboBox số dòng xem trước, Nút kiểm tra cập nhật).
   - **Hàng 1 (Notebook):** `ttk.Notebook` chứa 3 Tab:
     * Tab 0: `self.data_tab = DataTabPanel(notebook, ...)` ("Dữ liệu và xem trước")
     * Tab 1: `self.layout_tab = LayoutTabPanel(notebook, ...)` ("Chỉnh sửa Layout PDF")
     * Tab 2: `self.history_tab = HistoryTabPanel(notebook, ...)` ("📊 Lịch sử Đăng ký EDI")
   - **Hàng 2 (Footer):** Thanh tiến trình `self.progress = ctk.CTkProgressBar` và Hộp nhật ký `self.log_box = ctk.CTkTextbox`.

---

### 1.3. Cơ chế Định vị Widget & Tính toán Tọa độ (Coordinates Calculation)

1. **Trình quản lý bố cục (Layout Managers):**
   - **`grid()`**: Sử dụng chủ đạo trong toàn bộ ứng dụng với cấu hình `weight` co giãn động (`grid_rowconfigure`, `grid_columnconfigure`, `uniform="tab_cols"`).
   - **`pack()`**: Sử dụng cục bộ cho các cụm nút nối tiếp (ví dụ các nút Radio bước nhảy, các thẻ KPI, các nút header).
   - **`place()`**: Hiện chưa sử dụng nhiều trên màn hình chính, nhưng là công cụ lý tưởng cho lớp phủ Overlay và hộp thoại Tooltip nổi.

2. **Cách trích xuất tọa độ tuyệt đối và tương đối của bất kỳ Widget nào:**
   Để xác định vị trí chính xác của widget mục tiêu `target_widget` (ví dụ nút "Import từ Excel", ô Quét QR, nút "Tạo PDF") so với cửa sổ gốc `root` (`SlipPrinterApp`):
   ```python
   # Đảm bảo Tkinter hoàn tất tính toán hình học
   root.update_idletasks()

   # Tọa độ màn hình tuyệt đối (Root screen coords)
   target_root_x = target_widget.winfo_rootx()
   target_root_y = target_widget.winfo_rooty()
   app_root_x = root.winfo_rootx()
   app_root_y = root.winfo_rooty()

   # Tọa độ tương đối so với cửa sổ ứng dụng chính (App-relative coords)
   rel_x = target_root_x - app_root_x
   rel_y = target_root_y - app_root_y
   width = target_widget.winfo_width()
   height = target_widget.winfo_height()

   # Bounding Box bao quanh widget (với padding an toàn, ví dụ pad=6)
   pad = 6
   x1 = max(0, rel_x - pad)
   y1 = max(0, rel_y - pad)
   x2 = min(root.winfo_width(), rel_x + width + pad)
   y2 = min(root.winfo_height(), rel_y + height + pad)
   ```

3. **Xử lý Widget nằm trong Tab hoặc Khung cuộn (ScrollableFrame):**
   - Nếu widget mục tiêu nằm trong một Tab cụ thể (ví dụ form nhập liệu ở `data_tab` hoặc bảng D-pad ở `layout_tab`), động cơ hướng dẫn cần kích hoạt chuyển tab trước: `self.notebook.select(target_tab_index)`.
   - Nếu widget nằm trong `CTkScrollableFrame` (như `SidebarPanel`), đảm bảo widget hiển thị trong tầm nhìn trước khi đo tọa độ.

---

### 1.4. Hệ thống Kiểu dáng, Màu sắc & Thiết kế (Design Tokens & Typography)

1. **Hệ màu chủ đạo (Color Palette):**
   - **Von Restorff / Primary Action (Xanh lục Ngọc bích):**
     * Mã màu: `#10B981`, Hover: `#059669`, Text: `white`
     * Áp dụng: Nút "Tạo PDF", nút "➕ Thêm mới", nút "💾 Lưu vị trí này", nút "📥 Xuất Excel / CSV".
   - **Secondary / Operations Action (Xanh dương Electric Blue):**
     * Mã màu: `#2563EB`, Hover: `#1D4ED8`, Text: `white`
     * Áp dụng: Nút "⚡ Quét QR", nút "💾 Cập nhật dòng", nút "📷 Quét QR", Segmented button.
   - **Warning / Highlight / Tips (Hổ phách Amber):**
     * Mã màu: `#F59E0B`, Text: `white` hoặc `#B45309`
     * Áp dụng: Thẻ KPI "Số PO tiếp theo", biểu tượng hướng dẫn `💡`.
   - **Destructive / Danger (Đỏ tươi / Đỏ đậm):**
     * Mã màu: Light: `#EF4444`, Dark: `#991B1B`, Hover: `#DC2626` / `#7F1D1D`
     * Áp dụng: Nút "🗑️ Xóa dòng", cảnh báo trùng mã EDI (`#FEE2E2`).
   - **Màu nền trung tính (Neutral Backgrounds & Cards):**
     * Light/Dark tuples: `("gray94", "gray14")`, `("gray90", "gray20")`, `("gray92", "gray17")`, `("gray85", "gray25")`.
     * Văn bản chú thích: `("gray40", "gray60")` hoặc `("gray30", "gray70")`.

2. **Typography & Font Sizes:**
   - **Giao diện chuẩn:** `ctk.CTkFont` kế thừa hệ thống Windows Segoe UI qua `sv_ttk`.
   - **Dữ liệu mã / Payload:** `ctk.CTkFont(family="Consolas", size=11)` (áp dụng cho QR Payload, mã QR thô).
   - **Cỡ chữ phân cấp:**
     * Tiêu đề ứng dụng lớn: `size=28, weight="bold"`
     * Tiêu đề cửa sổ/mục: `size=20, weight="bold"`
     * Tiêu đề nhóm chức năng / Thẻ: `size=15` hoặc `16, weight="bold"`
     * Nhãn trường / Nút bấm chính: `size=13` hoặc `14, weight="bold"`
     * Nhãn mô tả / Hướng dẫn phụ: `size=11` hoặc `12`

3. **Lưu trữ Cấu hình Người dùng (Config Persistence):**
   - Vị trí: `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` (thông qua `self.app_state.paths.data_dir / "user_settings.json"`).
   - Dễ dàng mở rộng để lưu cờ: `{"appearance_mode": "Dark", "has_seen_tutorial": true}`.

---

## 2. Logic Chain (Chuỗi lập luận & So sánh Kỹ thuật)

### 2.1. Đánh giá 3 Phương án Kiến trúc cho Động cơ UI Overlay

Dựa trên các quan sát về CustomTkinter và hành vi cửa sổ trên Windows, chúng tôi phân tích 3 phương án:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │ ĐÁNH GIÁ CÁC PHƯƠNG ÁN KIẾN TRÚC UI OVERLAY TRÊN WINDOWS│
                  └─────────────────────────────────────────────────────────┘
                                               │
             ┌─────────────────────────────────┼─────────────────────────────────┐
             ▼                                 ▼                                 ▼
   [Phương án 1: IN-WINDOW CANVAS]   [Phương án 2: TOPLEVEL ALPHA]     [Phương án 3: GLASSMORPHISM PIL]
   • 1 tk.Canvas trên Root Window     • 1 Cửa sổ Toplevel không viền   • Tạo ảnh bán trong suốt RGBA
   • 4 Hình chữ nhật tối tạo rãnh     • attributes("-alpha", 0.65)     • Vẽ ảnh lên Canvas nền
   • Widget nổi bật lộ diện 100%      • attributes("-transparentcolor")• Đòi hỏi vẽ lại liên tục khi resize
   • Ưu: Siêu mượt, không lệch tọa độ • Nhược: Lệch 1-frame khi kéo    • Nhược: Chi phí CPU cao hơn
   • ĐÁNH GIÁ: TỐI ƯU NHẤT (Khuyên dùng)• ĐÁNH GIÁ: Rủi ro DWM/DPI       • ĐÁNH GIÁ: Phức tạp không cần thiết
```

#### Phương án 1: In-Window Canvas với 4 Khung chữ nhật bao quanh (4-Rectangle Spotlight Cutout) — **ĐỀ XUẤT TỐI ƯU**
- **Cơ chế hoạt động:**
  1. Tạo một `tk.Canvas(root, highlightthickness=0, bd=0)` phủ toàn bộ cửa sổ chính thông qua `canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)`. Gọi `canvas.lift()`.
  2. Đo tọa độ tương đối của widget cần hướng dẫn `(x1, y1, x2, y2)`.
  3. Vẽ 4 hình chữ nhật màu tối xám than chì (`#0f172a` hoặc `#111827` với stipple hoặc solid đậm) lấp đầy 4 phía xung quanh bounding box:
     - Đỉnh: `(0, 0, root_w, y1)`
     - Đáy: `(0, y2, root_w, root_h)`
     - Trái: `(0, y1, x1, y2)`
     - Phải: `(x2, y1, root_w, y2)`
  4. Vùng `(x1, y1, x2, y2)` ở giữa hoàn toàn trong suốt tự nhiên, để lộ 100% widget thực tế bên dưới đang hoạt động.
  5. Vẽ viền sáng phát quang (Glow Border) 3px màu `#10B981` (Emerald) hoặc `#3B82F6` (Electric Blue) bao quanh vùng `(x1, y1, x2, y2)`.
  6. Tạo một thẻ `ctk.CTkFrame` làm hộp thoại Callout Tooltip, đặt tự động ở vị trí thuận tiện nhất (phía dưới, phía trên, bên phải hoặc bên trái widget) tùy theo khoảng cách mép màn hình.
- **Ưu điểm vượt trội:**
  - ✅ **Hoàn toàn nằm trong tiến trình Mainloop:** Không tạo thêm HWND ngoài Windows OS, không gây giật lag, không xung đột Taskbar.
  - ✅ **Tự động co giãn theo cửa sổ:** Khi người dùng thay đổi kích thước hoặc di chuyển cửa sổ, `place(relwidth=1, relheight=1)` giữ nguyên vị trí, không có hiện tượng "trễ 1-frame" (window lag) như các cửa sổ `Toplevel` rời rạc.
  - ✅ **Chặn tương tác ngoài luồng:** Lớp Canvas tự động hấp thụ các cú click chuột ngoài vùng spotlight, bảo vệ người dùng không bấm nhầm nút khác trong lúc xem hướng dẫn.
  - ✅ **Dễ dàng kiểm thử tự động (Unit Testable):** Hoạt động hoàn hảo trong môi trường test `pytest` có hoặc không có giả lập màn hình thật.

#### Phương án 2: Borderless `CTkToplevel` / `tk.Toplevel` với `-alpha`
- **Cơ chế:** Tạo một cửa sổ phụ không viền `overrideredirect(True)`, gán `attributes("-alpha", 0.65)` và đồng bộ tọa độ qua sự kiện `<Configure>`.
- **Hạn chế:**
  - Trên Windows, việc gán `-transparentcolor` để khoét lỗ có thể khiến vùng khoét trở thành "click-through" (xuyên thấu click chuột vào phần mềm phía sau nếu người dùng click trượt).
  - Khi người dùng kéo di chuyển cửa sổ chính nhanh, cửa sổ `Toplevel` phụ thường bị trễ vài miligiây tạo cảm giác rung lắc (jitter).
  - Khó kiểm soát trên các hệ thống đa màn hình có DPI Scaling khác nhau (100% vs 125% vs 150%).

---

### 2.2. Kịch Bản 4 Bước Hướng Dẫn Cốt Lõi (Theo Yêu Cầu R2)

Động cơ hướng dẫn sẽ dẫn dắt người dùng qua 4 nghiệp vụ trọng tâm nhất:

| Bước | Tên Bước | Widget Mục tiêu (Target Widget) | Nội dung Diễn giải (Tooltip Content) | Thao tác Chuyển tiếp |
|:---:|---|---|---|---|
| **1** | **Nạp Dữ liệu từ Excel** | Khung chọn file Excel & Nút `Import từ Excel` trên `SidebarPanel` | "Nhấn nút **'Chọn'** để nạp file Excel danh sách tem hoặc nhấn **'Import từ Excel'** để nạp dữ liệu mẫu có sẵn. Phần mềm sẽ tự động kiểm tra định dạng Rev, số lượng và cảnh báo nếu phát hiện trùng mã EDI." | Bấm **"Tiếp tục ▶"** chuyển sang Bước 2 |
| **2** | **Quét QR Nghiệp vụ** | Nút `⚡ Quét QR (Phân tách · Hoàn kho)` trên Sidebar | "Công cụ hỗ trợ súng bắn mã QR với 3 nghiệp vụ tự động:<br>• **Phân tách (分割):** Tách lô hàng lớn thành các thùng nhỏ (+10 PO chi tiết).<br>• **Hoàn kho (戻入):** Nhập trả hàng về kho với mã PO hoàn trả đặc thù.<br>• **Bóc tách tem:** Giải mã chuỗi QR 129 ký tự để lấy mã hàng, số lượng, Rev và PO." | Bấm **"Tiếp tục ▶"** chuyển sang Bước 3 |
| **3** | **Tự động Sinh mã PO (Auto PO)** | Form nhập liệu dòng & Nút `➕ Thêm mới` trên `DataTabPanel` | "Khi tạo tem mới mà không nhập số PO, hệ thống sẽ **tự động sinh số PO chuẩn** tuần tự theo ngày (PO chi tiết `00010`, PO phụ `+001`) từ cơ sở dữ liệu chia sẻ `po_registry.db`, đảm bảo tính duy nhất và không bị trùng lặp." | Bấm **"Tiếp tục ▶"** chuyển sang Bước 4 |
| **4** | **Xem trước & Tạo file PDF** | Khung `🔍 Xem trước trang in` và Nút `Tạo PDF` | "Kiểm tra hình ảnh mẫu in trực quan (4 tem trên 1 trang A4) và chuỗi QR 129 ký tự. Nhấn **'Tạo PDF'** để xuất file in chất lượng cao. Quá trình tạo chạy ngầm không gây đơ ứng dụng. Sau khi xong, nhấn **'Mở PDF vừa tạo'** để in trực tiếp." | Bấm **"🎉 Hoàn tất"** đóng Overlay |

---

### 2.3. Thiết kế Nút Kích Hoạt & Cơ Chế Tự Động Gợi Ý Lần Đầu Mở App (Theo Yêu Cầu R3)

1. **Vị trí Nút Kích hoạt:**
   - Đặt một nút `ctk.CTkButton` với biểu tượng `💡 Hướng dẫn` tại thanh Header (cùng hàng với `theme_menu` và nút "Kiểm tra bản cập nhật") hoặc tại đỉnh `SidebarPanel`.
   - Màu sắc: `fg_color="#F59E0B"` (Amber/Vàng hổ phách), `hover_color="#D97706"`, `text_color="white"`, `font=ctk.CTkFont(size=12, weight="bold")`.
2. **Cơ chế Tự động Kích hoạt lần đầu:**
   - Trong `SlipPrinterApp.__init__()`, sau khi nạp cấu hình giao diện:
     ```python
     self.after(600, self._check_first_run_tutorial)
     ```
   - Hàm `_check_first_run_tutorial()` đọc `user_settings.json`. Nếu `has_seen_tutorial` chưa tồn tại hoặc bằng `False`, phần mềm sẽ hiển thị hộp thoại gợi ý nhẹ nhàng:
     *"Chào mừng bạn đến với phần mềm In Phiếu Hiện Vật! Bạn có muốn xem hướng dẫn nhanh 4 bước sử dụng không?"*
     Nếu người dùng chọn "Đồng ý" hoặc bấm xem, lớp phủ Overlay sẽ được kích hoạt; sau đó ghi nhận `has_seen_tutorial: True` vào `user_settings.json`.

---

## 3. Caveats (Lưu ý & Giới hạn)

1. **Thuộc tính Widget ẩn danh (Anonymous Widgets):**
   Trong `SidebarPanel` (`ui/components/sidebar.py`), một số nút bấm hiện được tạo trực tiếp mà không lưu thành thuộc tính thể hiện (ví dụ `self.import_button = ...`). Khi triển khai, nên gán tên thuộc tính rõ ràng để động cơ Tutorial truy cập trực tiếp thay vì duyệt mảng `winfo_children()`.
2. **Cập nhật hình học trước khi lấy tọa độ:**
   Cần luôn gọi `root.update_idletasks()` trước khi trích xuất `winfo_rootx()` / `winfo_rooty()` nhằm tránh tọa độ trả về bằng 0 khi widget mới vừa khởi tạo.
3. **Môi trường Headless / CI:**
   Trong các môi trường không có màn hình hiển thị (như Linux headless server), các hàm Tkinter đồ họa cần được bọc trong khối `try...except` hoặc sử dụng fixture `tk_root` đã được cách ly trong `conftest.py`.

---

## 4. Conclusion (Kết luận & Đề xuất Hành động)

1. **Tính khả thi 100%:** Kiến trúc giao diện hiện tại của `PM_in_lai_phieuhienvat` rất mạch lạc, áp dụng phân tách MVC chuẩn giữa `AppState`, `AppController`, `SlipPrinterApp` và các Component.
2. **Phương án đề xuất:** Xây dựng một module độc lập `ui/components/tutorial_overlay.py` định nghĩa lớp `InteractiveTutorialOverlay` sử dụng **In-Window Canvas 4-Rectangle Spotlight** kết hợp thẻ Tooltip nổi `ctk.CTkFrame`.
3. **Lưu trữ trạng thái:** Tái sử dụng tệp `user_settings.json` hiện có trong `%LOCALAPPDATA%\InPhieuHienVatData` để lưu cờ `has_seen_tutorial`.
4. **Trải nghiệm mượt mà:** Không chặn luồng chính (Mainloop), cho phép người dùng bấm "Bỏ qua (Skip)" bất kỳ lúc nào để quay lại trạng thái bình thường ngay lập tức.

---

## 5. Verification Method (Phương pháp Xác minh Độc lập)

### 5.1. Lệnh Kiểm thử Hệ thống
Chạy toàn bộ bộ kiểm thử tự động của dự án:
```powershell
pytest tests/ -v
```

### 5.2. Kịch bản Xác minh Kiểm thử Mới (Khi Triển Khai)
1. **Kiểm thử tọa độ Spotlight:** Tạo test `test_tutorial_overlay_spotlight_coordinates(tk_root)` xác nhận 4 góc của vùng rỗng khớp chính xác với bounding box của nút mục tiêu trong phạm vi sai số $\le 2$ pixel.
2. **Kiểm thử điều hướng Bước:** Tạo test `test_tutorial_navigation_next_back_skip(tk_root)` chứng minh chuyển từ Bước 1 $\rightarrow$ 4 và bấm "Bỏ qua" giải phóng hoàn toàn lớp Canvas khỏi màn hình.
3. **Kiểm thử Ghi nhớ Cấu hình:** Xác nhận cờ `has_seen_tutorial` được ghi và đọc chính xác từ `user_settings.json`.

---
*Báo cáo khảo sát hoàn tất và sẵn sàng cho giai đoạn lập kế hoạch & triển khai.*
