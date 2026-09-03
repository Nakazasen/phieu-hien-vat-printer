# Hướng Dẫn Vận Hành & Phát Hành Cập Nhật (Release & Update Playbook)
## Hệ Thống In Phiếu Hiện Vật (InPhieuHienVat)

Tài liệu này mô tả chi tiết quy trình chuẩn để kiểm thử, đóng gói, tạo bộ cài đặt (Setup.exe) và phát hành gói cập nhật tự động (Auto-update) qua mạng LAN công ty theo tiêu chuẩn tương đương MP2027.

---

## 1. Nguyên Tắc & Ranh Giới Tin Cậy (Trust Boundary)

> **Chính sách phát hành: `HASH_ONLY_LAN`**  
> Gói cập nhật **không dùng chữ ký số, private/public key, hay chứng chỉ ngoài**. Thư mục chia sẻ nội bộ LAN do KDTVN kiểm soát được xác định là ranh giới tin cậy. Tính toàn vẹn của ứng dụng được bảo vệ đa tầng bằng:
> - Thuật toán băm SHA-256 (64 ký tự hex) cho toàn bộ file và package.
> - Kê khai kích thước chính xác (byte-level).
> - Manifest bắt buộc có danh sách file khớp 100% (không thừa, không thiếu).
> - Trích xuất an toàn (Anti-Zip-Slip, cấm path traversal, cấm ghi đè ngoài staging).
> - Kiểm tra sức khỏe tự động (`--health-check`) trong sandbox trước khi kích hoạt.
> - Sao lưu SQLite database (Online Backup API) trước khi đổi phiên bản active.

---

## 2. Hai Phương Thức Phân Phối & Đường Dẫn LAN Chuẩn

| Phương thức | Dùng khi | Định dạng Artifact | Đường dẫn xuất bản trên LAN |
|---|---|---|---|
| **Bộ cài đặt (Setup)** | Cài mới máy tính, chuyển máy hoặc khôi phục thủ công | `InPhieuHienVat_Setup_<version>.exe` | `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI` |
| **Tự cập nhật (Auto-update)** | Tự động nâng cấp các máy đang chạy bản cũ | `InPhieuHienVat-<version>.phieuupdate` + `latest.json` | `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update` |

> **Lưu ý:** Thư mục cơ sở dữ liệu PO dùng chung (Registry DB) nằm tại:  
> `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\db\po_registry.db`

---

## 3. Cấu Trúc Gói Cài Đặt (Install Bundle)

```text
<install-root>/ (Mặc định: %LOCALAPPDATA%\InPhieuHienVat)
├── InPhieuHienVat_Launcher.exe    <-- Shortcut desktop/start menu luôn trỏ vào đây
├── current.json                  <-- Trỏ version đang active & SHA-256 manifest
├── previous.json                 <-- Trỏ version trước đó (để rollback khi cần)
├── .staging/                     <-- Thư mục tạm giải nén gói mới
├── backups/                      <-- Thư mục backup database & layout trước cập nhật
└── apps/
    └── <version>/                <-- Thư mục chứa onedir của từng phiên bản
        ├── InPhieuHienVat.exe
        ├── manifest.json
        └── _internal/...
```

---

## 4. Quy Tắc Phiên Bản (Version Rules)

1. **Nguồn sự thật duy nhất cho phiên bản kế tiếp:**  
   Đọc file catalog hiện có trên LAN: `release_update\latest.json`.  
   *Ví dụ: Nếu `latest.json` đang là `0.1.2`, phiên bản tiếp theo phải là `0.1.3`.*
2. **Đồng bộ 3 vị trí trước khi đóng gói:**
   - `release.json` (Trường `version`)
   - `installer\InPhieuHienVat.iss` (Dòng `#define AppVersion "..."`)
   - Release note mô tả ngắn gọn thay đổi cho người dùng (tối đa 2.000 ký tự).

---

## 5. Các Lệnh Đóng Gói & Phát Hành Chuẩn

### 5.1. Chạy Kiểm Thử Bắt Buộc Trước Khi Đóng Gói
```powershell
python -m pytest tests/test_updater.py tests/test_adversarial_updater.py -q
python -m pytest tests/test_po_registry.py tests/test_qr_operations.py -q
```
*Tất cả bài test phải PASS 100% trước khi tiến hành đóng gói.*

### 5.2. Đóng Gói & Phát Hành Toàn Diện Lên LAN (Khuyên Dùng)
Lệnh sau sẽ build onedir, chạy health-check, biên dịch Inno Setup (.iss), tạo gói update `.phieuupdate`, và phát hành nguyên tử (.part -> chính thức) lên cả 2 thư mục LAN:

```powershell
python package_app.py --build-update `
  --min-app-version "0.1.0" `
  --publish-lan `
  --release-notes "- Mô tả ngắn các tính năng mới hoặc bản sửa lỗi"
```

### 5.3. Hoặc Phát Hành Thủ Công Từng Thư Mục Riêng
- **Chỉ phát hành gói Auto-update:**
  ```powershell
  python package_app.py --build-update `
    --min-app-version "0.1.0" `
    --publish-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update" `
    --release-notes "- Mô tả thay đổi"
  ```
- **Chỉ phát hành bộ cài Setup.exe:**
  ```powershell
  python package_app.py `
    --publish-setup-dir "\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI"
  ```

---

## 6. Cơ Chế Phát Hành An Toàn (Atomic Publishing & Safety Guard)

Khi gọi lệnh publish, script `package_app.py` thực thi tuần tự các chốt an toàn:
1. **Pre-publish Probe:** Tạo file probe `.tmp` trên thư mục LAN, xác minh đọc/ghi thành công rồi xóa đi. Nếu LAN bị mất kết nối hoặc không có quyền ghi, script dừng ngay lập tức.
2. **Collision Guard:** Kiểm tra nếu file Setup hoặc Package cùng tên đã tồn tại trên LAN:
   - Nếu hash trùng khớp: Bỏ qua copy (tránh ghi đè trùng lặp).
   - Nếu hash khác biệt: Dừng khẩn cấp, từ chối ghi đè để bảo vệ lịch sử artifact.
3. **Copy qua tệp tạm `.part`:** Sao chép file lên LAN dưới dạng `<tên_file>.part`, kiểm tra lại SHA-256 và kích thước của file trên LAN so với local.
4. **Đổi tên nguyên tử (Atomic Rename):** Chỉ khi hash khớp tuyệt đối mới đổi tên `.part` thành `.phieuupdate` hoặc `.exe`.
5. **Catalog `latest.json` ghi sau cùng:** File catalog trên LAN luôn được cập nhật sau khi gói `.phieuupdate` đã nằm an toàn trên LAN. Client không bao giờ gặp tình trạng thấy catalog trỏ vào gói đang copy dở.

---

## 7. Khôi Phục & Rollback Khi Gặp Sự Cố

- **Nếu client cập nhật phiên bản mới bị lỗi khởi động:**
  Chỉ cần chạy lệnh rollback của Launcher:
  ```powershell
  python -c "from updater.app_updates import rollback_update; rollback_update(r'%LOCALAPPDATA%\InPhieuHienVat')"
  ```
  Launcher sẽ hoán đổi con trỏ `current.json` về lại `previous.json` ngay lập tức.
- **Nếu cần phục hồi dữ liệu SQLite:**
  Mọi bản database trước khi cập nhật đều được lưu trữ an toàn tại:
  `%LOCALAPPDATA%\InPhieuHienVat\backups\before-<version>\`
