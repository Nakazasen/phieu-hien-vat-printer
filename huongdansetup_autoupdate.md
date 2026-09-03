# Hướng dẫn Setup Inno Setup và Auto-update chuẩn của In Phiếu Hiện Vật

Tài liệu này mô tả cách hệ thống **In Phiếu Hiện Vật (InPhieuHienVat)** được đóng gói, cài đặt lần đầu và tự cập nhật tự động. Đây là hướng dẫn vận hành chuẩn dựa trên mã nguồn hiện tại cùng các quy chuẩn hệ thống của KDTVN.

> **Chính sách phát hành: `HASH_ONLY_LAN`**  
> Gói cập nhật **không dùng chữ ký số, private/public key, `manifest.sig`, `key_id` hay `trusted_signing_keys`**.  
> Thư mục chia sẻ mạng LAN do công ty kiểm soát là ranh giới tin cậy (Trust Boundary); tính toàn vẹn được bảo vệ bằng mã băm SHA-256, kiểm tra kích thước byte-level, manifest kê khai tuyệt đối, giải nén an toàn chống Zip-Slip, SQLite Online Backup và kiểm tra sức khỏe tự động (`--health-check`).

---

## 1. Hai phương thức phân phối

| Phương thức | Dùng khi | Artifact | Nơi publish trên LAN |
|---|---|---|---|
| **Setup Inno Setup** | Cài mới, chuyển máy hoặc khôi phục thủ công | `InPhieuHienVat_Setup_<version>.exe` | Thư mục phần mềm LAN: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI` |
| **Auto-update** | Nâng cấp tự động bản cài In Phiếu Hiện Vật hiện có | `InPhieuHienVat-<version>.phieuupdate` + `latest.json` | Thư mục cập nhật LAN: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update` |

Yêu cầu “đóng gói theo tiêu chuẩn update”, “làm bản update” hoặc “phát hành update” luôn có nghĩa là làm **cả hai**: Setup trên thư mục phần mềm LAN và package/catalog trong `release_update`. Chỉ yêu cầu “tạo Setup” thì không tự tạo `.phieuupdate`.

---

## 2. Thành phần và cấu trúc chính

| Thành phần | Vai trò |
|---|---|
| `release.json` | Metadata bất biến được đóng vào portable app: `version`, `channel`, schema tương thích. |
| `installer/InPhieuHienVat.iss` | Kịch bản Inno Setup cài bundle ban đầu cho người dùng Windows. |
| `package_app.py` | Build app/launcher, health-check, ghép install bundle, tạo `.phieuupdate`, biên dịch Setup và publish atomically lên LAN. |
| `updater/update_launcher.py` | Launcher đọc `current.json`, kiểm hash `manifest.json` rồi khởi chạy app version đang active. |
| `updater/update_delivery.py` | Nạp nguồn update, đọc catalog LAN, phát hiện bản mới không gây treo UI và tải vào cache local. |
| `updater/app_updates.py` | Kiểm tra package, stage, health-check, backup database SQLite, kích hoạt hoặc rollback. |
| `updater/update_security.py` | Kiểm tra schema/hash/đường dẫn, safe extraction (Anti-Zip-Slip) và giới hạn dung lượng 512MB. |

Bundle cài đặt ban đầu có dạng:

```text
<install-root>/ (Mặc định: %LOCALAPPDATA%\InPhieuHienVat)
├── InPhieuHienVat_Launcher.exe    <-- Điểm vào duy nhất của shortcut
├── current.json                  <-- Pointer tới phiên bản đang kích hoạt
├── previous.json                 <-- Pointer phiên bản trước (phục vụ rollback)
├── .staging/                     <-- Thư mục tạm giải nén bản mới
├── backups/                      <-- Sao lưu DB SQLite trước mỗi lần cập nhật
└── apps/
    └── <version>/                <-- Thư mục Onedir của phiên bản
        ├── InPhieuHienVat.exe
        ├── manifest.json
        └── _internal/...
```

`current.json` chứa version, entrypoint và SHA-256 của `manifest.json`; launcher từ chối chạy app nếu pointer hoặc manifest không khớp.

---

## 3. Nguồn update chuẩn và trust boundary

Ba endpoint LAN được phê duyệt:

```text
1. Thư mục Setup:
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI

2. Thư mục auto-update:
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update

3. Thư mục cơ sở dữ liệu PO dùng chung (Registry DB):
\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\db\po_registry.db
```

`update_sources.default.json` được đóng gói bên trong app và mặc định trỏ đúng folder `release_update` với `startup_check: true`. Ứng dụng nạp cấu hình theo thứ tự tăng dần ưu tiên:

1. **Default được đóng trong app:** `update_sources.default.json`.
2. **Override của người dùng:** `%LOCALAPPDATA%\InPhieuHienVatData\update_sources.json`.
3. **Company policy:** `%PROGRAMDATA%\InPhieuHienVat\update_sources.json`.

Cấu trúc file cấu hình chuẩn:

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

---

## 4. Quy tắc version và điều kiện trước phát hành

Nguồn sự thật duy nhất để chọn version là:

```text
<release_update>\latest.json
```

Không suy đoán version từ commit, nhánh, hoặc file cũ. Trước khi thay đổi version/build/publish phải:

1. Đọc `latest.json` trên LAN; kiểm schema, version, package, SHA-256 và size.
2. Xác nhận hash/size thực tế của package mà catalog trỏ tới trên LAN.
3. Chọn patch kế tiếp. Ví dụ catalog đang là `0.1.2` thì phát hành `0.1.3`.
4. Cập nhật đồng bộ version trong `release.json` và `installer/InPhieuHienVat.iss`.
5. Kiểm tra `update_sources.default.json` vẫn trỏ đúng `release_update` đã duyệt.
6. Chạy toàn bộ test suite để đảm bảo 100% pass:
   ```powershell
   pytest tests/test_updater.py tests/test_adversarial_updater.py tests/test_po_registry.py tests/test_qr_operations.py -q
   ```
7. Không ghi đè hoặc đổi tên tùy ý nếu file cùng version đã tồn tại trên LAN nhưng khác hash.

---

## 5. Đóng gói và phát hành tự động

### 5.1. Lệnh phát hành chuẩn lên mạng LAN (Khuyên dùng)

Lệnh sau sẽ build onedir, smoke health-check, biên dịch Inno Setup installer, tạo gói `.phieuupdate`, và tự động xuất bản nguyên tử lên cả 2 thư mục LAN:

```powershell
python package_app.py --build-update `
  --min-app-version "0.1.0" `
  --publish-lan `
  --release-notes "0.1.3: Cập nhật phôi phiếu EDI 3 ô chữ ký, căn chỉnh chính xác, nâng cấp launcher và hệ thống tự động cập nhật LAN."
```

### 5.2. Các bước script thực hiện tuần tự:

1. **Pre-publish Probe:** Kiểm tra đọc/ghi thử nghiệm trên cả hai thư mục LAN bằng probe tạm.
2. **Collision Check:** Xác minh artifact cũ trên LAN không bị va chạm hash.
3. **Build Application onedir:** Đóng gói bằng PyInstaller với tài nguyên `template.pdf`, `layout_config.json`, `release.json`, `update_sources.default.json`.
4. **Smoke Health-Check:** Chạy `InPhieuHienVat.exe --health-check` trong môi trường sandbox cô lập.
5. **Build Launcher:** Tạo `InPhieuHienVat_Launcher.exe`.
6. **Ghép Bundle:** Tạo `install_bundle` với `apps/<version>/`, `manifest.json` và `current.json`.
7. **Biên dịch Inno Setup:** Tự động tìm `ISCC.exe` và biên dịch `InPhieuHienVat_Setup_<version>.exe`.
8. **Tạo `.phieuupdate`:** Đóng gói zip an toàn kèm `manifest.json` kê khai chi tiết SHA-256 từng file.
9. **Xuất bản nguyên tử (Atomic Publish):**
   - Copy Setup lên LAN dưới dạng `.part` $ightarrow$ kiểm tra hash/size $ightarrow$ đổi tên thành `.exe`.
   - Copy `.phieuupdate` lên LAN dưới dạng `.part` $ightarrow$ kiểm tra hash/size $ightarrow$ đổi tên thành `.phieuupdate`.
   - Ghi `latest.json.part` $ightarrow$ đổi tên thành `latest.json` **sau cùng**.

---

## 6. Đóng gói Setup bằng Inno Setup

`installer/InPhieuHienVat.iss` được cấu hình:
- `AppVersion` bắt buộc khớp với `release.json`.
- Cài đặt per-user tại `{localappdata}\InPhieuHienVat`, không yêu cầu quyền Admin (`PrivilegesRequired=lowest`).
- Tạo shortcut desktop và start menu trỏ tới `InPhieuHienVat_Launcher.exe`.
- Đa ngôn ngữ: Hỗ trợ tiếng Việt (`installer/languages/Vietnamese.isl`).
- Sử dụng thuật toán nén `lzma2/solid`.
- Khi gỡ cài đặt: Chỉ xóa thư mục `.staging`, tuyệt đối không xóa dữ liệu người dùng hay cơ sở dữ liệu.

---

## 7. Runtime auto-update hoạt động như thế nào

### 7.1. Discovery và download (Không gây đơ máy)
1. Khi ứng dụng khởi động, luồng nền (`threading.Thread`) thăm dò `latest.json` trên LAN với **timeout 2.0 giây**. Nếu mất mạng hoặc LAN chậm, ứng dụng vẫn mở ngay lập tức.
2. Chỉ so sánh phiên bản trong `latest.json` với phiên bản hiện tại từ `release.json`. Không băm file zip lớn qua mạng LAN khi khởi động.
3. Khi người dùng xác nhận cập nhật, gói `.phieuupdate` mới được tải vào `%LOCALAPPDATA%\InPhieuHienVatData\.updates\downloads\` qua file tạm, kiểm tra toàn bộ SHA-256 và kích thước rồi mới lưu vào cache.

### 7.2. Kiểm tra, Stage và Kích hoạt
1. Mở `.phieuupdate`, kiểm tra `manifest.json`: version phải mới hơn, `min_app_version` phải thỏa mãn.
2. Giải nén vào thư mục `.staging/`, áp dụng Anti-Zip-Slip (chặn path traversal `..`, đường dẫn tuyệt đối, file ẩn, giới hạn 512MB).
3. So khớp hash SHA-256 và size của từng file giải nén với manifest.
4. Đổi tên staging thành `apps/<target-version>`.
5. Chạy `InPhieuHienVat.exe --health-check` trong môi trường sandbox để xác nhận chạy tốt.
6. **Sao lưu database SQLite:** Dùng SQLite Online Backup API sao lưu `po_registry.db` và `layout_config.json` vào `backups/before-<target-version>/` kèm `backup.json`.
7. **Hoán đổi nguyên tử:** Sao chép `current.json` vào `previous.json`, sau đó ghi đè `current.json` mới atomically.

### 7.3. Rollback an toàn
Nếu phiên bản mới gặp sự cố, hệ thống có thể rollback tức thì bằng cách hoán đổi ngược `current.json` và `previous.json` mà không làm mất dữ liệu của người dùng:
```powershell
python -c "from updater.app_updates import rollback_update; rollback_update(r'%LOCALAPPDATA%\InPhieuHienVat')"
```

---

## 8. Checklist phát hành một phiên bản

- [ ] Đọc `latest.json` trên LAN, xác định phiên bản mới là patch kế tiếp.
- [ ] Đồng bộ `release.json` và `installer/InPhieuHienVat.iss`.
- [ ] Chạy kiểm thử tự động đạt 100% PASS.
- [ ] Chạy lệnh `package_app.py --build-update --publish-lan --release-notes "..."`.
- [ ] Kiểm tra trên LAN: `InPhieuHienVat_Setup_<version>.exe`, `InPhieuHienVat-<version>.phieuupdate` và `latest.json` đã xuất hiện đầy đủ, không còn file `.part`.
- [ ] Mở ứng dụng từ bản cũ để kiểm tra thông báo cập nhật và nâng cấp thử nghiệm.

---

## 9. Lệnh kiểm tra nhanh sau đóng gói

```powershell
# Kiểm tra health-check của app onedir
& ".\dist\InPhieuHienVat\InPhieuHienVat.exe" --health-check

# Kiểm tra health-check của launcher trên bundle
& ".\release_artifacts\install_bundle\InPhieuHienVat_Launcher.exe" --health-check

# Kiểm tra hash và kích thước của các artifact local
Get-FileHash ".\release_artifacts\InPhieuHienVat_Setup_*.exe" -Algorithm SHA256
Get-FileHash ".\release_artifacts\InPhieuHienVat-*.phieuupdate" -Algorithm SHA256
```
