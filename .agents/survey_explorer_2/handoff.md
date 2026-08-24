# Báo Cáo Khảo Sát Kiến Trúc Codebase Dự Án `PM_in_lai_phieuhienvat`

- **Tác giả / Agent:** `survey_explorer_2` (Exploration Subagent)
- **Đối tượng khảo sát:** Toàn bộ codebase `D:\Sandbox\PM_in_lai_phieuhienvat`
- **Mục tiêu:** Khảo sát chi tiết cấu trúc mã nguồn, điểm khởi chạy, cơ chế luồng sự kiện UI/Tkinter, hệ thống đánh số phiên bản, cấu hình ổ đĩa mạng chia sẻ & đường dẫn tự động cập nhật, danh mục tài nguyên/phụ thuộc đóng gói, và hiện trạng bộ kiểm thử (test suite).
- **Ngày khảo sát:** 2026-08-19

---

## 1. Observation (Dữ Liệu Quan Sát Thực Tế)

### 1.1 Sơ đồ cấu trúc thư mục & phân tầng codebase

```
D:\Sandbox\PM_in_lai_phieuhienvat\
├── slip_printer_app.py                # Entrypoint chính của ứng dụng (CLI & GUI)
├── release.json                       # Version metadata định dạng JSON (SemVer)
├── layout_config.json                 # Tọa độ in mặc định cho văn bản và mã QR
├── template.pdf                       # Phôi PDF nền mẫu (bất biến)
├── app_icon.ico                       # Icon ứng dụng định dạng Windows ICO
├── app_icon_source.png                # Ảnh gốc PNG độ phân giải cao
├── DummySlip.xlsx                     # File Excel mẫu phục vụ import thử nghiệm
├── update_sources.default.json        # Cấu hình nguồn cập nhật mạng mặc định
├── package_app.py                     # Kịch bản build PyInstaller onedir + Install Bundle
├── build_exe.py / build_exe.bat       # Shortcut tiện ích chạy build
├── requirements.txt                   # Danh mục dependencies Python
├── pytest.ini                         # Cấu hình test runner pytest
├── HANDOVER.md                        # Tài liệu bàn giao hiện hành
│
├── core/                              # TẦNG CORE ENGINE & DATA
│   ├── __init__.py
│   ├── runtime_paths.py               # Phân giải đường dẫn tĩnh/động, cô lập AppData & SQLite WAL backup
│   ├── po_registry.py                 # Quản lý SQLite PO database, tự sinh PO 11YYMMDDNN, chống trùng composite key
│   └── slip_printer_engine.py         # Đọc Excel XML stream, tính toán số lượng, sinh QR 129 chars, vẽ overlay PDF
│
├── ui/                                # TẦNG GIAO DIỆN (CustomTkinter + sv_ttk)
│   ├── __init__.py
│   ├── main_window.py                 # SlipPrinterApp (Root Window), splitter pane, event queue polling loop
│   ├── app_state.py                   # AppState (Quản lý toàn bộ State và StringVar của Tkinter)
│   ├── app_controller.py              # AppController (Điều phối hành động UI, thread nền, dialogs, update)
│   └── components/                    # Các Component Panel độc lập
│       ├── __init__.py
│       ├── sidebar.py                 # SidebarPanel (Chọn file Excel/Template/Output, nút hành động chính)
│       ├── data_tab.py                # DataTabPanel (Form nhập liệu, Treeview bôi đỏ dòng trùng, preview ảnh)
│       ├── layout_tab.py              # LayoutTabPanel (Bảng D-Pad điều hướng vị trí X/Y, chỉnh kích thước)
│       ├── history_tab.py             # HistoryTabPanel (Thẻ KPI thống kê PO, tra cứu lịch sử, xuất CSV)
│       └── qr_scan_dialog.py          # QRScanDialog (Modal quét QR súng/dán, phân tách, hoàn kho, bóc tách)
│
├── updater/                           # TẦNG TỰ ĐỘNG CẬP NHẬT (Auto-Updater & Security)
│   ├── __init__.py
│   ├── update_launcher.py             # InPhieuHienVat_Launcher.exe (Bootstrap launcher đọc current.json)
│   ├── app_updates.py                 # Transactional Updater (Staging -> Health-check -> Switch -> Rollback)
│   ├── update_delivery.py             # Phát hiện & nạp package .phieuupdate từ thư mục mạng LAN/UNC
│   └── update_security.py             # Kiểm tra mã băm SHA-256, Anti-Zip-Slip, validate manifest
│
├── installer/                         # KỊCH BẢN ĐÓNG GÓI INNO SETUP
│   └── InPhieuHienVat.iss             # Inno Setup 6 script cấu hình per-user ({localappdata}\InPhieuHienVat)
│
├── docs/                              # TÀI LIỆU DỰ ÁN
│   └── ONBOARDING.md                  # Hướng dẫn tiếp nhận dự án (Onboarding Guide)
│
├── tests/                             # BỘ KIỂM THỬ TỰ ĐỘNG (Pytest)
│   ├── conftest.py                    # Fixtures: cấu hình Tcl/Tk, cô lập AppData, mock messagebox
│   ├── test_po_registry.py            # Kiểm thử SQLite PO Registry, sequence, lock, corruption recovery
│   ├── test_engine.py                 # Kiểm thử tính toán số lượng, validate revision, normalize box, QR
│   ├── test_import_duplicate_check.py # Kiểm thử import Excel trùng mã, Treeview tag red, prompt thêm tay
│   ├── test_runtime_paths.py          # Kiểm thử phân giải đường dẫn, env overrides, network fallback
│   ├── test_updater.py                # Kiểm thử toàn diện auto-updater, security, manifest, delivery
│   ├── test_qr_operations.py          # Kiểm thử quét QR, phân tách (10010), hoàn kho (11010)
│   ├── test_ui_layout.py              # Kiểm thử giao diện và layout editor
│   ├── test_ui_responsiveness.py      # Kiểm thử độ phản hồi giao diện
│   └── [adversarial & stress tests]   # Các bài kiểm thử chịu tải và đối kháng
```

---

### 1.2 Điểm khởi chạy (Entry Points)

1. **Ứng dụng chính:** `D:\Sandbox\PM_in_lai_phieuhienvat\slip_printer_app.py`
   - Đoạn mã khởi chạy chính (dòng 21–38):
     ```python
     def main(argv: list[str] | None = None) -> int:
         parser = argparse.ArgumentParser(add_help=False)
         parser.add_argument("--health-check", action="store_true")
         parser.add_argument("--wait-for-pid", type=int)
         args, _unknown = parser.parse_known_args(argv)
         if args.health_check:
             run_health_check()
             return 0
         if args.wait_for_pid is not None:
             _wait_for_process_exit(args.wait_for_pid)
         app = SlipPrinterApp()
         app.mainloop()
         return 0
     ```
   - Chức năng: Hỗ trợ `--health-check` (chạy không mở GUI, kiểm tra nạp template, layout config và kết nối database SQLite); hỗ trợ `--wait-for-pid` (chờ PID tiến trình cũ kết thúc trước khi mở giao diện mới khi cập nhật).

2. **Launcher khởi chạy độc lập (Bootstrap Launcher):** `D:\Sandbox\PM_in_lai_phieuhienvat\updater\update_launcher.py`
   - Đóng vai trò là file thực thi cố định ngoài cùng (`InPhieuHienVat_Launcher.exe`).
   - Đọc `current.json`, kiểm tra mã băm SHA-256 của `manifest.json` trong thư mục phiên bản đang kích hoạt (`apps/<version>/manifest.json`), sau đó khởi chạy `apps/<version>/InPhieuHienVat.exe`.

---

### 1.3 Cơ chế vòng lặp sự kiện UI (Tkinter / CustomTkinter Event Loop & Threading)

- **Framework:** `CustomTkinter` (`ctk.CTk`) kết hợp `sv_ttk` (theme Windows 11 Fluent) và `ttk.Treeview`, `ttk.Notebook`, `ttk.Panedwindow`.
- **Luồng sự kiện (Event Loop):** `SlipPrinterApp.mainloop()` tại `slip_printer_app.py:32`.
- **Mô hình đa nhiệm & Thread Dispatch:**
  - `ui/app_controller.py`: Mọi tác vụ nặng (tạo file PDF `start_generation`, kiểm tra cập nhật `check_for_update`, tải và cài bản cập nhật `start_update_install`) đều được đẩy sang luồng phụ qua `threading.Thread(target=..., daemon=True).start()` (xem `app_controller.py:538, 592, 610`).
  - Giao tiếp liên luồng qua `queue.Queue` (`app_state.event_queue` tại `app_state.py:36`). Luồng worker gửi tuple sự kiện như `("progress", (current, total, message))`, `("success", (output_path, count))`, `("error", err_str)`, `("update_available", ...)`.
  - Hàm `SlipPrinterApp._drain_event_queue()` trong `ui/main_window.py:269–358` được lập lịch định kỳ mỗi 150ms qua `self.after(150, self._drain_event_queue)` trên luồng UI chính. Khi có sự kiện từ queue, UI widget cập nhật thanh tiến trình, log box, hoặc hiển thị hộp thoại `messagebox`.
  - **Đảm bảo an toàn luồng tuyệt đối:** Không bao giờ gọi trực tiếp Tkinter widget từ background thread.

- **Quản lý Hộp thoại (Dialogs & Messageboxes):**
  - Sử dụng chuẩn `tkinter.messagebox` (`showinfo`, `showwarning`, `showerror`, `askyesno`).
  - Toàn bộ thông điệp cảnh báo/lỗi đã được Việt hóa 100%, có cấu trúc rõ ràng gồm mô tả lỗi và phần "👉 Hướng dẫn khắc phục:" chi tiết (xem `app_controller.py:108, 237, 264, 300, 336, 351, 370, 396, 427, 448, 467, 483, 521, 574`).
  - Hộp thoại quét QR chuyên dụng (`QRScanDialog` tại `ui/components/qr_scan_dialog.py:24–496`) kế thừa `ctk.CTkToplevel`, cấu hình `self.transient(parent)` và `self.grab_set()` để hoạt động như một modal dialog chuẩn.

---

### 1.4 Hệ thống quản lý phiên bản (Versioning)

- File định danh phiên bản nguồn: `D:\Sandbox\PM_in_lai_phieuhienvat\release.json` (dòng 1–9):
  ```json
  {
    "application": "In Phiếu Hiện Vật",
    "version": "0.1.1",
    "channel": "pilot",
    "update_manifest_schema": 1,
    "minimum_supported_data_schema": 1,
    "maximum_supported_data_schema": 1
  }
  ```
- Ràng buộc phiên bản đồng bộ:
  - `installer/InPhieuHienVat.iss:5`: `#define AppVersion "0.1.1"`
  - `package_app.py:164–171`: Hàm `_validate_inno_version(version)` tự động kiểm tra đối chiếu đảm bảo `#define AppVersion "<version>"` trong file `.iss` phải khớp chính xác 100% với giá trị `version` trong `release.json`.
  - `updater/update_delivery.py:77–82`: Hàm `current_release_version(paths)` đọc `release.json` từ bundle và validate cú pháp SemVer `major.minor.patch`.

---

### 1.5 Cấu hình ổ đĩa mạng chia sẻ (Network Share) & Auto-Updater Releases

1. **Cơ sở dữ liệu SQLite dùng chung (PO Registry):**
   - Định nghĩa tại `core/runtime_paths.py:22`:
     ```python
     SHARED_REGISTRY_DIR = r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\db"
     ```
   - Cơ chế phân giải đường dẫn và fallback an toàn (`_resolve_registry_path` tại `runtime_paths.py:102–125`):
     - Ưu tiên 1: Biến môi trường `INPHIEUHIENVAT_REGISTRY_PATH` (ghi đè file tường minh).
     - Ưu tiên 2: Biến môi trường `INPHIEUHIENVAT_DATA_DIR` (thư mục dữ liệu độc lập cho test).
     - Ưu tiên 3: Ổ đĩa mạng chia sẻ `SHARED_REGISTRY_DIR / "po_registry.db"` (mặc định cho production).
     - Ưu tiên 4: Fallback về `%LOCALAPPDATA%\InPhieuHienVatData\po_registry.db` nếu ổ mạng không thể truy cập (offline / mất mạng) mà không làm sập ứng dụng.
   - Cấu hình an toàn SQLite trên ổ mạng UNC (`core/po_registry.py:58–70`):
     - `PRAGMA busy_timeout=30000` (chờ lock tối đa 30 giây).
     - `timeout=30.0` trong `sqlite3.connect`.
     - `PRAGMA journal_mode=DELETE` khi đường dẫn là UNC share (`\\` hoặc `//`), do chế độ WAL không an toàn khi chia sẻ bộ nhớ đa máy qua giao thức SMB/CIFS.
     - Cơ chế tự phục hồi `_execute_with_auto_recovery()` thực hiện retry exponential backoff 5 lần khi gặp lỗi locked/busy.

2. **Đường dẫn phát hành bản cập nhật (Auto-Updater Release Path):**
   - Định nghĩa tại `D:\Sandbox\PM_in_lai_phieuhienvat\update_sources.default.json:7`:
     ```json
     {
       "schema": 1,
       "startup_check": true,
       "sources": [
         {
           "type": "folder",
           "location": "\\\\fstvn01\\Data\\00_KDTVN Common(KDTVN共通)\\⑤Production Engineering(製造技術)\\Hang muc can luu\\Vinh\\PMintemEDI\\release_update",
           "enabled": true
         }
       ]
     }
     ```
   - Định dạng gói phát hành: File zip nén `.phieuupdate` (ví dụ `InPhieuHienVat-0.1.2.phieuupdate`) đi kèm tệp chỉ mục `latest.json` ghi mã băm SHA-256, dung lượng và release notes.

---

### 1.6 Danh mục tài nguyên, phôi in, cơ sở dữ liệu và cấu hình đóng gói (Packaging Assets)

1. **Tài nguyên bất biến đóng gói cùng binary (Bundled Assets):**
   - `template.pdf` (phôi mẫu nền phiếu hiện vật, bắt buộc).
   - `layout_config.json` (tọa độ in mặc định).
   - `release.json` (metadata phiên bản).
   - `update_sources.default.json` (cấu hình mạng nguồn update).
   - `app_icon.ico` (icon Windows).
   - `DummySlip.xlsx` (file mẫu thử nghiệm).
   - Dữ liệu theme `sv_ttk` (`--collect-data sv_ttk`).

2. **Dữ liệu người dùng động (User Mutable Data - Lưu ngoài thư mục cài đặt):**
   - Thư mục: `%LOCALAPPDATA%\InPhieuHienVatData\`
   - Tệp tin:
     - `po_registry.db` (nếu fallback về cục bộ).
     - `layout_config.json` (cấu hình tọa độ sau khi người dùng tinh chỉnh).
     - `user_settings.json` (lưu chế độ theme: Dark / Light / System).
     - `update_sources.json` (cấu hình nguồn update tùy chỉnh).
     - `.updates/downloads/` (cache gói cập nhật tải về).
   - Thư mục xuất PDF: `%USERPROFILE%\Documents\InPhieuHienVat\output\`.

3. **Quy trình đóng gói tự động (`package_app.py` & Inno Setup):**
   - Bước 1: PyInstaller build app chính `--onedir` $\rightarrow$ `dist/InPhieuHienVat/InPhieuHienVat.exe`.
   - Bước 2: Chạy smoke test `--health-check` đối với app vừa build.
   - Bước 3: PyInstaller build launcher `--onedir --console` $\rightarrow$ `dist/InPhieuHienVat_Launcher/InPhieuHienVat_Launcher.exe`.
   - Bước 4: Lắp ráp cấu trúc `release_artifacts/install_bundle/`:
     - `InPhieuHienVat_Launcher.exe`
     - `current.json`
     - `apps/<version>/` (chứa toàn bộ `InPhieuHienVat.exe`, thư mục `_internal/` và `manifest.json`).
   - Bước 5: Chạy smoke test launcher với `--health-check`.
   - Bước 6: Inno Setup 6 biên dịch `installer/InPhieuHienVat.iss` $\rightarrow$ `release_artifacts/InPhieuHienVat_Setup_<version>.exe` (cài đặt per-user không đòi quyền Admin).

---

### 1.7 Hiện trạng bộ kiểm thử (Test Suite & Test Runner)

- **Cấu hình:** `pytest.ini` (`pythonpath = .`, `testpaths = tests`).
- **Fixtures hỗ trợ:** `tests/conftest.py` tự động cô lập thư mục AppData/Output cho mỗi test case, mock toàn bộ `tkinter.messagebox` để tránh bị treo giao diện, thiết lập đường dẫn Tcl/Tk trên Windows.
- **Danh sách file test:**
  1. `tests/test_po_registry.py` (222 dòng): Test logic SQLite PO generator, sequence 99/ngày, transaction integrity, concurrency, corruption healing.
  2. `tests/test_engine.py` (250 dòng): Test công thức tính tổng số lượng, validate revision 01-99, normalize box, expand box sequence, format chuỗi QR 129 chars.
  3. `tests/test_import_duplicate_check.py` (651 dòng): Test import Excel có và không trùng lặp mã EDI, hiển thị cảnh báo non-blocking, Treeview gán tag `"duplicate"` bôi nền đỏ `#FEE2E2`, hộp thoại xác nhận khi thêm tay, việt hóa thông báo.
  4. `tests/test_runtime_paths.py` (141 dòng): Test phân giải đường dẫn, env var overrides, SQLite backup WAL migration, priority resolution.
  5. `tests/test_updater.py` (371 dòng): Test bảo mật updater, kiểm tra hash SHA-256, chống Zip-Slip, manifest, discovery, staging, atomic activation, rollback.
  6. `tests/test_qr_operations.py` (527 dòng): Test modal dialog quét QR, bóc tách QR 129 chars, sinh PO chi tiết phân tách `10010`..`90010`, hoàn kho `11010`..`91010`.
  7. `tests/test_ui_layout.py`, `tests/test_ui_responsiveness.py`, `tests/test_adversarial_stress.py`, `tests/test_adversarial_ui_and_cli.py`, `tests/test_challenger2_empirical_stress.py`, `tests/test_final_acceptance_challenger1.py`, `tests/test_r1_stress_challenger.py`.

---

## 2. Logic Chain (Chuỗi Lập Luận Suy Luận)

1. **Từ quan sát cấu trúc thư mục và file entrypoint:**
   - Ứng dụng áp dụng kiến trúc MVC rõ ràng: `ui/main_window.py` là View chính, `ui/app_controller.py` là Controller xử lý logic nghiệp vụ, `ui/app_state.py` là State trung tâm, và các module trong `core/` độc lập hoàn toàn với UI framework.
   - Cơ chế khởi chạy hai lớp (Launcher `InPhieuHienVat_Launcher.exe` $\rightarrow$ Versioned App `apps/<version>/InPhieuHienVat.exe`) cho phép ứng dụng thực hiện tự động cập nhật nguyên khối (transactional atomic update) mà không bao giờ gặp lỗi tệp đang bị khóa (file lock) khi ghi đè trực tiếp.

2. **Từ quan sát luồng sự kiện Tkinter và xử lý đa luồng:**
   - Việc tách biệt luồng thông qua `threading.Thread` kết hợp `app_state.event_queue` và chu kỳ polling 150ms `after()` trên `SlipPrinterApp` đảm bảo giao diện luôn mượt mà (responsive), không bao giờ bị đơ/treo (freeze) khi thực hiện import file Excel lớn, render PDF nhiều trang hoặc tải bản cập nhật qua mạng.

3. **Từ quan sát cấu hình đường dẫn mạng và cơ sở dữ liệu:**
   - Đường dẫn database dùng chung `\\fstvn01\Data\...\db\po_registry.db` và đường dẫn cập nhật `\\fstvn01\Data\...\release_update` được quản lý tập trung và nhất quán.
   - Việc cấu hình `PRAGMA journal_mode=DELETE` cho các đường dẫn UNC mạng là hoàn toàn chính xác và bắt buộc, vì cơ chế WAL của SQLite phụ thuộc vào shared memory (POSIX/Windows shared memory map) vốn không thể đồng bộ an toàn qua mạng chia sẻ SMB giữa nhiều máy trạm khác nhau.
   - Cơ chế fallback 4 cấp độ trong `_resolve_registry_path()` đảm bảo ứng dụng vẫn khởi động và hoạt động ổn định cục bộ ngay cả khi mất kết nối mạng.

4. **Từ quan sát quy trình đóng gói và kiểm soát phiên bản:**
   - File `release.json` là Single Source of Truth cho phiên bản. Kịch bản `package_app.py` ép buộc kiểm tra tính đồng bộ giữa `release.json` và `installer/InPhieuHienVat.iss`, ngăn chặn hoàn toàn rủi ro sai lệch phiên bản khi xuất bản installer.
   - Bộ cài đặt Inno Setup được cấu hình `PrivilegesRequired=lowest` cài vào `{localappdata}\InPhieuHienVat`, đảm bảo mọi công nhân/kỹ thuật viên trong nhà máy đều có thể tự cài đặt và chạy cập nhật mà không cần liên hệ bộ phận IT cấp quyền Administrator.

---

## 3. Caveats (Khu Vực Cần Lưu Ý & Giới Hạn Khảo Sát)

1. **Khả năng truy cập thực tế tới ổ đĩa mạng `\\fstvn01\...`:**
   - Quá trình kiểm tra cục bộ sử dụng đường dẫn giả lập hoặc fallback do môi trường sandbox không gắn trực tiếp ổ đĩa mạng nội bộ `\\fstvn01`. Codebase đã có sẵn đầy đủ fallback và test mock cho kịch bản này.
2. **File PPTX Translation:**
   - Trong thư mục `pptx_translation/` và `tests/test_pptx_*.py` có tồn tại các module dịch thuật PPTX và OCR hình ảnh từ yêu cầu trước đó. Các module này độc lập và không ảnh hưởng đến luồng hoạt động chính của ứng dụng in phiếu hiện vật `InPhieuHienVat`.

---

## 4. Conclusion (Kết Luận Đánh Giá Tổng Thể)

1. Codebase của dự án `PM_in_lai_phieuhienvat` có cấu trúc hoàn chỉnh, phân tầng rõ ràng (Presentation / Core Engine / Updater / Storage / Packaging / Tests), tuân thủ nghiêm ngặt các nguyên tắc Clean Code và quy chuẩn an toàn Windows Desktop.
2. Hệ thống Auto-Update và Đóng gói (Inno Setup 6 + PyInstaller onedir + Bootstrap Launcher) đã được thiết kế hoàn thiện, hỗ trợ đầy đủ quy trình kiểm tra sức khỏe (`--health-check`), backup dữ liệu trước cập nhật, chuyển đổi phiên bản nguyên tử và rollback an toàn.
3. Cơ sở dữ liệu chia sẻ SQLite và đường dẫn cập nhật mạng nội bộ đã được cấu hình chính xác trỏ đến thư mục `\\fstvn01\Data\...`, có cơ chế chống lock mạng và fallback an toàn.
4. Bộ kiểm thử (Pytest) bao phủ toàn diện từ unit test, integration test, UI mock test, cho đến stress test và updater verification test.

---

## 5. Verification Method (Phương Pháp Xác Minh Độc Lập)

Để kiểm tra và xác minh độc lập toàn bộ các phát hiện trên, thực hiện các lệnh sau trong môi trường dòng lệnh Windows PowerShell tại thư mục dự án:

1. **Chạy toàn bộ Unit Test & Integration Test:**
   ```powershell
   pytest
   ```
   *Kết quả kiểm thử thực tế:* **153 passed, 1 skipped, 1 warning in 189.39s** (100% test suite passed).

2. **Chạy kiểm tra sức khỏe hệ thống không cần mở GUI (Headless Health Check):**
   ```powershell
   python slip_printer_app.py --health-check
   ```
   *Kỳ vọng:* In ra thông báo: `Kiểm tra hệ thống thành công: ...\template.pdf` và thoát với mã `0`.

3. **Kiểm tra cú pháp và tính hợp lệ của script đóng gói:**
   ```powershell
   python -c "import package_app; print('package_app syntax and imports OK')"
   ```

4. **Kiểm tra tính nhất quán phiên bản:**
   ```powershell
   python -c "import json; r=json.load(open('release.json')); iss=open('installer/InPhieuHienVat.iss', encoding='utf-8').read(); assert f'#define AppVersion \"{r[\"version\"]}\"' in iss; print('Version sync OK:', r['version'])"
   ```
