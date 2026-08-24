# Báo Cáo Khảo Sát & Thiết Kế Đóng Gói và Tự Động Cập Nhật (Packaging & Auto-Update) cho PM_in_lai_phieuhienvat

- **Người thực hiện:** `survey_explorer_3`
- **Thời gian:** 2026-08-19T08:07:00Z
- **Working Directory:** `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\survey_explorer_3`
- **Parent Agent:** `orchestrator_pkg` (Conversation ID: `496a12d8-5a64-4409-b089-6abdc4ab595d`)

---

## 1. Observation (Quan Sát Trực Tiếp)

### 1.1. Khảo sát công cụ trên môi trường Windows

Khảo sát trực tiếp qua các lệnh PowerShell và Python:
- **Python Environment:**
  - Đường dẫn thực thi: `C:\Users\tvn183660\AppData\Local\Programs\Python\Python313\python.exe`
  - Phiên bản: `Python 3.13.5 (tags/v3.13.5:6cb20a2, Jun 11 2025, 16:15:46) [MSC v.1943 64 bit (AMD64)]`
- **PyInstaller:**
  - Đường dẫn thực thi: `C:\Users\tvn183660\AppData\Local\Programs\Python\Python313\Scripts\pyinstaller.EXE`
  - Phiên bản: `6.17.0`
- **Inno Setup 6 Command-Line Compiler (`ISCC.exe`):**
  - Không nằm trong `PATH`, không nằm trong `C:\Program Files (x86)\Inno Setup 6\` hoặc `C:\Program Files\Inno Setup 6\`.
  - **Được cài đặt và hoạt động tại:** `C:\Users\tvn183660\AppData\Local\Programs\Inno Setup 6\ISCC.exe` (Phiên bản compiler engine: `Inno Setup 6.7.3`).

### 1.2. Nghiên cứu kiến trúc tham chiếu từ `D:\Sandbox\MP2027`
Dự án `MP2027` sử dụng kiến trúc đóng gói và cập nhật **`HASH_ONLY_LAN`**:
- **Tài liệu quy chuẩn:** `D:\Sandbox\MP2027\docs\handover\release_update_playbook.md`.
- **Cơ chế không khóa (Keyless):** Không sử dụng cặp khóa ký private/public key. Dựa hoàn toàn vào phân quyền thư mục mạng nội bộ (`\\fstvn01\Data\...`) được công ty quản lý và kiểm tra mã băm SHA-256 đối chiếu giữa catalog (`latest.json`), tệp kê khai (`manifest.json`), và từng tệp nhị phân.
- **Mô hình Onedir + Stable Launcher:**
  - Bộ cài đặt chứa: thư mục ứng dụng theo phiên bản `apps/<version>/` (onedir PyInstaller) + tệp kê khai `apps/<version>/manifest.json` + trình khởi chạy ổn định `MP2027_Launcher.exe` + tệp trạng thái `current.json`.
  - Tệp `.iss` cài đặt vào `{localappdata}\MP2027 Manager` với `PrivilegesRequired=lowest`. Cài đặt theo cấp người dùng (per-user) giúp việc cập nhật không bị chặn bởi quyền quản trị Windows (UAC).
- **Quy trình đóng gói (`scripts/package_app.py`):**
  1. Build ứng dụng `MP2027_Portable` qua PyInstaller.
  2. Kiểm tra tài nguyên và chạy thử nghiệm `--health-check`.
  3. Build launcher `MP2027_Manager`.
  4. Lắp ráp gói `install_bundle` (`apps/<version>/` + `current.json` + `MP2027_Launcher.exe`).
  5. Tùy chọn `--build-update` tạo tệp `.mpupdate` nén `manifest.json` và tệp ứng dụng.
  6. Tùy chọn `--publish-dir` phát hành gói nguyên tử: sao chép `.part`, xác thực SHA-256, đổi tên chính thức, rồi ghi `latest.json` sau cùng.

### 1.3. Khảo sát hiện trạng dự án mục tiêu `PM_in_lai_phieuhienvat`
Dự án hiện tại `PM_in_lai_phieuhienvat` đã được thiết kế sẵn sàng các module tương ứng theo chuẩn `MP2027`:
- **File cấu hình phiên bản:** `release.json` (hiện tại `version: "0.1.1"`).
- **File cấu hình nguồn cập nhật:** `update_sources.default.json`:
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
- **Kịch bản Inno Setup:** `installer/InPhieuHienVat.iss` với AppId `{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}`.
- **Bộ công cụ đóng gói:** `package_app.py` và `build_exe.bat`.
- **Hệ thống Auto-Update (`updater/`):**
  - `updater/update_security.py`: Kiểm tra an toàn đường dẫn (`safe_relative_path`), kiểm tra manifest, hash SHA-256, dung lượng tối đa (`MAX_ARTIFACT_BYTES = 512MB`), giải nén an toàn (`safe_extract_package`).
  - `updater/update_delivery.py`: Đọc cấu hình `load_update_config`, phân tích `latest.json`, phát hiện bản mới `discover_update`, tải gói về bộ đệm `fetch_update`.
  - `updater/app_updates.py`: Trích xuất gói vào `.staging/`, kiểm tra manifest, chạy kiểm tra sức khỏe `--health-check`, sao lưu database `po_registry.db` bằng SQLite Online Backup API và file cấu hình layout vào `backups/before-<version>`, kích hoạt nguyên tử qua `current.json`/`previous.json`, và khởi động bản mới `launch_activated_update`.
  - `updater/update_launcher.py`: Trình khởi chạy đọc `current.json`, kiểm tra tính toàn vẹn của `manifest.json` theo hash SHA-256, tìm file thực thi của phiên bản đang kích hoạt và khởi chạy.
- **Tích hợp giao diện UI:**
  - `ui/main_window.py` (dòng 67, 313-357): Khởi tạo kiểm tra tự động sau 1.2 giây (`after(1200)`), lắng nghe các sự kiện cập nhật qua hàng đợi `event_queue` (`update_available`, `update_success`, `update_error`).
  - `ui/app_controller.py` (dòng 564-611): Triển khai worker thread nền `threading.Thread(target=worker, daemon=True).start()` cho `check_for_update` và `start_update_install`, không gây nghẽn UI main loop.
- **Kiểm thử tự động:** `tests/test_updater.py` chứa 26 test case bao quát toàn bộ logic bảo mật, delivery, cấu hình, và phát hiện phiên bản (chạy đạt 100% qua pytest).

---

## 2. Logic Chain (Chuỗi Lập Luận Kỹ Thuật)

### Bước 1: Xác lập tính khả thi của chuỗi công cụ (Toolchain Feasibility)
- *Quan sát 1.1:* `python.exe` (3.13.5) và `pyinstaller.exe` (6.17.0) có sẵn trong môi trường người dùng; `ISCC.exe` (6.7.3) có sẵn tại `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`.
- *Lập luận:* Toàn bộ quy trình từ biên dịch Python sang mã máy (PyInstaller onedir) cho đến đóng gói tệp cài đặt Windows (`Setup.exe` qua Inno Setup) có thể tự động hóa 100% bằng script mà không yêu cầu cài thêm phần mềm ngoài.

### Bước 2: Chuẩn hóa đặc tả đóng gói (Packaging Specification)
- *Quan sát 1.2 & 1.3:* `InPhieuHienVat.iss` định nghĩa:
  - Định danh duy nhất: `AppId={{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}` (không trùng với MP2027).
  - Vị trí cài đặt mặc định: `{localappdata}\InPhieuHienVat` kết hợp `PrivilegesRequired=lowest`.
  - Cấu trúc thư mục cài đặt: Thư mục gốc chứa `InPhieuHienVat_Launcher.exe`, `current.json`, và thư mục con `apps/<version>/` chứa toàn bộ binary của app.
  - Quản lý shortcut & gỡ cài đặt: Tạo shortcut Desktop và Start Menu trỏ vào `InPhieuHienVat_Launcher.exe`. Khi gỡ cài đặt, `[UninstallDelete]` chỉ dọn dẹp `.staging`, bảo toàn dữ liệu lịch sử in ấn và cấu hình của người dùng nằm tại `%LOCALAPPDATA%\InPhieuHienVatData`.
- *Lập luận:* Kiến trúc này phân tách hoàn toàn giữa **Phần mềm (disposable release assets)** và **Dữ liệu người dùng (persistent user state)**, tạo tiền đề để Auto-Update hoạt động trơn tru bằng cách chỉ ghi đè/bổ sung thư mục `apps/<new_version>/` mà không đụng chạm đến dữ liệu nghiệp vụ.

### Bước 3: Hoàn thiện quy trình build tự động (`build_installer.bat` & `package_app.py`)
- *Quan sát 1.1 & 1.3:* Lệnh biên dịch Inno Setup cần trỏ chính xác vào file `ISCC.exe`.
- *Lập luận:* Cần cung cấp script `build_installer.bat` thông minh có khả năng tự động dò tìm `ISCC.exe` qua 4 vị trí:
  1. `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`
  2. `%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe`
  3. `%ProgramFiles%\Inno Setup 6\ISCC.exe`
  4. Lệnh `ISCC` trên biến môi trường `PATH`.
  Quy trình thực thi gồm 2 pha:
  `python package_app.py` -> kiểm tra bundle -> gọi `ISCC.exe installer\InPhieuHienVat.iss` -> sinh `release_artifacts\InPhieuHienVat_Setup_<version>.exe`.

### Bước 4: Kiến trúc Auto-Update và luồng tương tác Non-blocking UI
- *Quan sát 1.3:*
  - `discover_update` đọc `latest.json` trên ổ mạng `\\fstvn01\...`.
  - Nếu `version > current_version` và SHA-256 khớp, trả về `UpdateCandidate`.
  - `check_for_update` và `start_update_install` được bọc trong daemon thread (`threading.Thread`).
  - Giao tiếp giữa thread nền và UI Tkinter thông qua `queue.Queue` (`app_state.event_queue`).
  - Tkinter event loop gọi `_drain_event_queue` định kỳ 150ms để cập nhật giao diện (Status bar, Dialog xác nhận Yes/No, Progress bar).
  - Quá trình kích hoạt: Staging -> Verify SHA-256 -> Health-check (`--health-check`) -> Backup SQLite `po_registry.db` -> Atomic update `current.json` -> Gọi `launch_activated_update` với tham số `--wait-for-pid <current_pid>` -> Đóng app cũ -> Tiến trình mới chờ app cũ thoát hẳn rồi mở UI.
- *Lập luận:* Luồng cập nhật đảm bảo an toàn tuyệt đối (Fail-Safe), chống treo đơ giao diện, tự động phục hồi nếu có lỗi trong quá trình tải hoặc kiểm tra tính toàn vẹn.

---

## 3. Caveats (Lưu Ý & Ranh Giới Kỹ Thuật)

1. **Khả năng kết nối ổ đĩa mạng LAN:**
   - Trong trường hợp máy trạm mất kết nối mạng nội bộ hoặc ổ chia sẻ `\\fstvn01\...` tạm thời không truy cập được, hàm `discover_update` bắt các ngoại lệ `OSError` / `UpdateDeliveryError` và bỏ qua (fail-safe) một cách êm ái, không làm gián đoạn trải nghiệm mở phần mềm của người dùng.
2. **Quyền hạn cài đặt Windows (UAC):**
   - Bộ cài Inno Setup được cấu hình `PrivilegesRequired=lowest` cài vào `{localappdata}`. Người dùng văn phòng thông thường không cần quyền Administrator vẫn có thể cài đặt và nhận bản cập nhật tự động.
3. **An toàn dữ liệu SQLite trong chế độ WAL:**
   - Việc sao lưu runtime state trước khi update sử dụng `sqlite3.backup()` trực tiếp trên connection thay vì hàm `shutil.copy2` đơn thuần, tránh được lỗi mất mát dữ liệu chưa được checkpoint từ file `-wal`.
4. **Vị trí ISCC.exe:**
   - Máy phát triển hiện tại cài Inno Setup ở thư mục per-user (`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`). Tất cả build script cần hỗ trợ đường dẫn này cùng với các đường dẫn hệ thống tiêu chuẩn.

---

## 4. Conclusion (Kết Luận & Đề Xuất Kỹ Thuật)

Hệ thống đóng gói (Inno Setup 6) và tự động cập nhật (Auto-Update) của dự án `PM_in_lai_phieuhienvat` đã kế thừa trọn vẹn và chuẩn hóa từ dự án mẫu `MP2027`.

### Bảng tổng hợp thông số kỹ thuật:

| Hạng mục | Thông số / Quy cách của PM_in_lai_phieuhienvat |
|---|---|
| **App Name** | `In Phiếu Hiện Vật` |
| **AppId GUID** | `{{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}}` |
| **Compiler Engine** | Inno Setup 6.7.3 (`ISCC.exe`) |
| **Cơ chế tin cậy** | `HASH_ONLY_LAN` (Không dùng key mã hóa; kiểm tra SHA-256 qua LAN nội bộ) |
| **Đường dẫn phát hành LAN** | `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update` |
| **Đường dẫn Database dùng chung** | `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\db\po_registry.db` |
| **Vị trí cài đặt ứng dụng** | `{localappdata}\InPhieuHienVat` (`apps/<version>/` + `current.json` + `InPhieuHienVat_Launcher.exe`) |
| **Vị trí dữ liệu người dùng** | `%LOCALAPPDATA%\InPhieuHienVatData` (`po_registry.db` fallback, `layout_config.json`, `update_sources.json`) |
| **Luồng thực thi UI** | Background Daemon Thread + Tkinter Event Queue (150ms drain), không treo UI |
| **Quy trình khởi động lại** | `launch_activated_update` -> spawn tiến trình mới với cờ `--wait-for-pid` -> thoát tiến trình cũ |

### Đề xuất kịch bản build hoàn chỉnh `build_installer.bat`:
```bat
@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo =======================================================
echo    DONG GOI VA TAO BO CAI DAT IN PHIEU HIEN VAT
echo =======================================================
echo.

echo [1/3] Chay package_app.py dung ung dung onedir va launcher...
python package_app.py
if errorlevel 1 (
    echo.
    echo [LOI] package_app.py that bai.
    pause
    exit /b 1
)

echo.
echo [2/3] Tim kiem trinh bien dich Inno Setup 6 (ISCC.exe)...
set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
) else if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%ProgramFiles%\Inno Setup 6\ISCC.exe"
) else (
    where ISCC.exe >nul 2>nul
    if not errorlevel 1 (
        set "ISCC_PATH=ISCC.exe"
    )
)

if not defined ISCC_PATH (
    echo.
    echo [CANH BAO] Khong tim thay ISCC.exe. Goi cai dat bundle nam trong release_artifacts\install_bundle.
    echo Vui long cai dat Inno Setup 6 de bien dich thanh Setup.exe.
    pause
    exit /b 0
)

echo Da tim thay ISCC tai: "!ISCC_PATH!"
echo.
echo [3/3] Bien dich bo cai dat bang Inno Setup...
"!ISCC_PATH!" "installer\InPhieuHienVat.iss"
if errorlevel 1 (
    echo.
    echo [LOI] Bien dich Inno Setup that bai.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo    THANH CONG! TEP CAI DAT DA DUOC TAO TAI:
echo    release_artifacts\
echo =======================================================
echo.
pause
```

---

## 5. Verification Method (Phương Pháp Xác Minh)

### 5.1. Chạy toàn bộ Unit Test cho hệ thống Auto-Update
Chạy lệnh kiểm thử Pytest:
```powershell
python -m pytest tests/test_updater.py -v
```
**Điều kiện thành công:** Toàn bộ 26 test case đều báo `PASSED` (bao gồm kiểm tra mã băm, phân tích manifest, phòng chống path traversal, phát hiện và tải bản cập nhật).

### 5.2. Xác minh biên dịch gói cài đặt Inno Setup (`ISCC.exe`)
Chạy lệnh biên dịch thủ công qua PowerShell:
```powershell
& "C:\Users\tvn183660\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "installer\InPhieuHienVat.iss"
```
**Điều kiện thành công:** Compiler trả về mã thoát `0`, tạo thành công tệp `release_artifacts\InPhieuHienVat_Setup_0.1.1.exe`.

### 5.3. Xác minh tự động đóng gói qua Python script
Chạy lệnh:
```powershell
python package_app.py
```
**Điều kiện thành công:** Tạo đầy đủ `release_artifacts/install_bundle/`, vượt qua smoke test `--health-check` của cả `InPhieuHienVat.exe` và `InPhieuHienVat_Launcher.exe`.

### 5.4. Xác minh điều kiện không hợp lệ (Invalidation Conditions)
- Nếu `release.json` và `InPhieuHienVat.iss` không khớp phiên bản, `package_app.py` sẽ chặn ngay từ bước đầu.
- Nếu tệp `.phieuupdate` bị chỉnh sửa hoặc thiếu tệp so với `manifest.json`, `safe_extract_package` và `verify_manifest_files` sẽ từ chối giải nén và dọn sạch thư mục `.staging`.
