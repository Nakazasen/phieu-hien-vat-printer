# Handover — In Phiếu Hiện Vật

Ngày cập nhật: `2026-08-14` (Asia/Bangkok)  
Trạng thái: ứng dụng in phiếu, đóng gói Inno Setup per-user và auto-update qua folder/LAN **đã được triển khai và smoke-test ngày 2026-08-14**. Chưa có nguồn update production được cấu hình/publish.

## 1. Mục đích và phạm vi

`In Phiếu Hiện Vật` là ứng dụng desktop Windows đọc Excel, cho phép chỉnh sửa record, tạo QR và ghép dữ liệu lên `template.pdf` để xuất PDF nhiều trang.

Tài liệu này là nguồn bàn giao hiện hành cho:

- vận hành source/EXE hiện tại;
- các contract dữ liệu Excel, QR, PO và layout;
- kiến trúc, vận hành và bàn giao installer Inno Setup cùng auto-update an toàn, tham chiếu theo mô hình `D:\Sandbox\MP2027`.

Phần 7 giữ lại kế hoạch/acceptance gốc để truy vết; trạng thái thực tế và cách vận hành đã triển khai nằm ở phần 12 trở đi.

## 2. Trạng thái hiện tại đã xác nhận

### 2.1 Chạy và build

- Chạy source: `python slip_printer_app.py`; kiểm tra không mở UI: `python slip_printer_app.py --health-check`.
- Build: `python package_app.py` (hoặc tương thích ngược: `python build_exe.py`, `build_exe.bat`).
- PyInstaller dùng `--onedir`: app ở `dist\InPhieuHienVat`, launcher ở `dist\InPhieuHienVat_Launcher`.
- Bundle cài đặt versioned: `release_artifacts\install_bundle`; installer: `release_artifacts\InPhieuHienVat_Setup_0.1.0.exe`.
- Metadata chính thức: `release.json` (SemVer/channel/schema). Project vẫn **không phải Git repository** và chưa có test framework; smoke tests hiện được thực thi bằng command/script trực tiếp.

### 2.2 Runtime và dữ liệu bền vững hiện tại

Khi chạy source, runtime directory là thư mục chứa `slip_printer_app.py`. Khi chạy EXE, runtime directory là thư mục chứa EXE.

| Dữ liệu/tài nguyên | Vị trí hiện tại | Ý nghĩa |
|---|---|---|
| `template.pdf` | cạnh source/EXE; nếu EXE one-file chưa có thì copy từ bundle | PDF nền mặc định |
| `layout_config.json` | cạnh source/EXE | layout người dùng có thể lưu |
| `po_registry.db` | cạnh source/EXE | SQLite lưu sequence PO và khóa uniqueness |
| `output\` | mặc định dưới runtime directory | PDF được tạo |

Điều này phù hợp cho EXE portable, nhưng không phù hợp với update versioned vì code và dữ liệu người dùng đang lẫn cùng một thư mục.

### 2.3 Quy tắc PO

- Ba field `PO`, `PO chi tiết`, `PO phụ` trên form bị khóa; app tự sinh khi PO trống.
- Nút **Hướng dẫn nhanh** chỉ điền dữ liệu hàng mẫu; không điền PO mẫu cứng.
- PO tự sinh: `11YYMMDDNN`; `NN` từ `01` đến `99` mỗi ngày.
- `PO chi tiết = 00010`; `PO phụ = +001`.
- SQLite có khóa chính `(po, po_detail, po_sub, box)`.
- Luồng GUI hiện kiểm tra/ghi khóa lúc **Tạo PDF**. Cùng PO nhưng `box` khác là hợp lệ theo contract hiện có.
- `po_registry.db` đang bật SQLite WAL; khi di chuyển/backup phải xử lý WAL đúng cách, không được chỉ copy mù file `.db` khi app còn mở.

### 2.4 Quy tắc dữ liệu và PDF không được phá vỡ

- Excel đọc worksheet active, từ dòng `28`, cột `A:J`.
- Field bắt buộc: Mã hàng, Tên hàng, Số lượng thùng, Số box, Rev.
- Tổng SL luôn tính lại từ `Số lượng thùng × segment cuối của Số box`; ví dụ `20 × 001/003 = 60`. Cột C Excel không quyết định giá trị cuối.
- Ngày/Lot chỉ nhận từ Excel; rỗng trở thành 10 dấu cách trong QR.
- Template chỉ dùng trang đầu và clone cho từng record.
- QR là fixed-width payload, không phải JSON.

## 3. Thành phần chính

| File | Trách nhiệm |
|---|---|
| `slip_printer_app.py` | GUI CustomTkinter, paths, form, import, preview, worker xuất PDF |
| `slip_printer_engine.py` | model `SlipRecord`, Excel ZIP/XML reader, validation, QR, overlay/merge PDF, layout |
| `po_registry.py` | SQLite PO generation và uniqueness registry |
| `template.pdf` | PDF nền mặc định |
| `layout_config.json` | font, text position, QR position |
| `build_exe.py` | build PyInstaller one-file hiện tại |
| `build_exe.bat` | wrapper gọi build script |
| `HANDOVER.md` | tài liệu bàn giao hiện hành |

## 4. Mô hình tham chiếu đã phân tích: MP2027

Đã phân tích project `D:\Sandbox\MP2027`, đặc biệt:

- `scripts/package_app.py`
- `installer\MP2027_Manager.iss`
- `scripts\update_launcher.py`
- `src\services\app_updates.py`
- `src\services\update_delivery.py`
- `src\services\update_security.py`
- `docs\handover\release_update_playbook.md`

Mô hình này cần được **chuyển hóa**, không copy nguyên xi.

### 4.1 Packaging/installer của MP2027

1. Build app bằng PyInstaller **onedir** thay vì one-file.
2. Build một launcher nhỏ, ổn định.
3. Tạo install bundle:

```text
install_bundle/
  Launcher.exe
  current.json
  apps/
    <version>/
      App.exe
      _internal/
      manifest.json
```

4. Inno Setup cài bundle vào `%LOCALAPPDATA%`, với `PrivilegesRequired=lowest`.
5. Shortcut luôn gọi launcher, không gọi trực tiếp app nằm trong `apps/<version>`.

### 4.2 Update của MP2027

MP2027 đang dùng policy `HASH_ONLY_LAN`:

- thư mục UNC do công ty kiểm soát là trust boundary;
- không dùng signing key, `manifest.sig`, `key_id` hoặc trusted-key provisioning;
- `latest.json` công bố version, tên package, size, SHA-256 và release notes;
- package `.mpupdate` chứa `manifest.json` với inventory size/SHA-256 của từng file;
- package được publish dưới tên `.part`, hash được kiểm tra rồi mới đổi tên atomically;
- `latest.json` luôn publish **sau cùng** để client không nhìn thấy release dở dang.

Client:

```text
load source config
 -> đọc latest.json
 -> kiểm tra package/version/size/SHA-256
 -> tải/copy vào cache local atomically
 -> kiểm tra manifest + danh sách file
 -> safe extract vào .staging
 -> kiểm tra hash từng file
 -> health-check EXE mới
 -> backup dữ liệu runtime
 -> current.json <- version mới (atomic)
 -> previous.json <- version cũ
 -> launcher khởi động version mới
```

Rollback không ghi đè binary cũ: launcher chỉ đảo `current.json` và `previous.json` sau khi kiểm tra entrypoint version cũ còn tồn tại.

### 4.3 Biện pháp cần giữ lại khi áp dụng

- SemVer `major.minor.patch` và `release.json` là metadata được bundle cùng app.
- Phân tách code immutable khỏi dữ liệu mutable.
- Manifest bắt buộc; reject package thiếu/thừa file, downgrade, path traversal, size bất thường hoặc hash sai.
- Safe extraction có giới hạn dung lượng tổng, không cho absolute/`..`/hidden path.
- Health-check process mới trong data root cô lập trước activation.
- `current.json`/`previous.json` được ghi temp rồi `os.replace` atomically.
- Backup trước activation và có log/release note/evidence theo phiên bản.

## 5. Khoảng cách giữa app hiện tại và mô hình mục tiêu

| Hạng mục | Hiện tại | Mục tiêu |
|---|---|---|
| Binary | one-file EXE | onedir, versioned app slots |
| Khởi chạy | mở EXE trực tiếp | launcher ổn định đọc `current.json` |
| Cài đặt | copy EXE thủ công | Inno Setup per-user |
| Version | không có metadata | `release.json`, SemVer, release notes |
| Update | chưa có | `.phieuupdate` (hoặc tên được chốt), manifest/hash/catalog |
| Code vs data | chung thư mục EXE | tách `apps/<version>` và user-data |
| PO SQLite | cạnh EXE | data root, backup/checkpoint trước update |
| Layout | cạnh EXE | user-data, seed một lần từ layout bundle |
| Template mặc định | copy cạnh EXE | immutable asset trong app version; chọn template bên ngoài vẫn được phép |
| Kiểm thử release | thủ công | unit + smoke packaged + launcher + installer/update tests |

## 6. Kiến trúc mục tiêu đề xuất cho In Phiếu Hiện Vật

Tên thư mục và tên package cần chốt trước khi code. Phương án mặc định để triển khai:

```text
%LOCALAPPDATA%\InPhieuHienVat\
  InPhieuHienVat_Launcher.exe
  current.json
  previous.json
  apps\
    0.1.0\
      InPhieuHienVat.exe
      _internal\...
      manifest.json
  .staging\
  backups\
    before-0.1.1\...

%LOCALAPPDATA%\InPhieuHienVatData\
  po_registry.db
  layout_config.json
  update_sources.json            # optional user override
  .updates\downloads\
  logs\                          # nếu logging được chấp thuận

%USERPROFILE%\Documents\InPhieuHienVat\output\
  <generated PDFs>
```

Nguyên tắc:

- `apps/<version>` là immutable sau khi phát hành.
- Không được lưu `po_registry.db`, output hoặc layout người dùng trong `apps/<version>`.
- Default `template.pdf` và default `layout_config.json` là asset của app version.
- Lần chạy đầu, app seed `layout_config.json` vào data root nếu người dùng chưa có file; không được ghi đè layout đã chỉnh khi update.
- `template.pdf` mặc định có thể đọc trong bundle; ô chọn PDF Mẫu vẫn cho phép người dùng chọn template ngoài bundle.
- Output mặc định nên ở Documents để người dùng dễ thấy. Đây là đề xuất cần chủ sở hữu xác nhận.

### 6.1 Lưu ý bắt buộc cho SQLite WAL

`po_registry.py` dùng `PRAGMA journal_mode=WAL`. Trước khi updater backup hoặc app chuyển version:

1. dừng toàn bộ thao tác tạo PDF/ghi PO;
2. checkpoint WAL (`PRAGMA wal_checkpoint(TRUNCATE)`) rồi đóng connection, **hoặc** dùng SQLite backup API để tạo snapshot nhất quán;
3. backup database kèm manifest hash;
4. chỉ sau đó mới đổi `current.json`.

Không được sao chép một mình `po_registry.db` trong khi WAL còn có dữ liệu chưa checkpoint; điều đó có thể làm mất sequence hoặc uniqueness record mới nhất.

## 7. Kế hoạch triển khai

Các phase dưới đây là kế hoạch gốc dùng để truy vết. Phần kỹ thuật của Phase 1–6 đã được triển khai theo phần 12; các quyết định production/pilot còn lại vẫn là điều kiện release. Trong phiên này, bootstrap Spec Kit đã timeout quá 60 giây và người dùng đã phê duyệt ngoại lệ hẹp được ghi trong `antigravityrules`; Graphify và kiểm thử vẫn bắt buộc.

### Phase 0 — Chốt chính sách phát hành (blocker nghiệp vụ)

Quyết định cần chủ sở hữu xác nhận:

1. Thư mục UNC/ổ mạng tin cậy để chứa update; ai có quyền publish.
2. Có dùng policy `HASH_ONLY_LAN` như MP2027 hay cần ký Authenticode/package signing riêng.
3. Tên app, `AppId` Inno cố định, version khởi đầu và channel (`pilot`/`stable`).
4. Vị trí data root và output mặc định đề xuất ở phần 6.
5. Update tự kiểm tra lúc startup, chỉ kiểm tra thủ công, hay cả hai.
6. Có hỗ trợ HTTPS sau này hay chỉ LAN/UNC.

Không triển khai hoặc publish update khi các quyết định trên chưa rõ.

### Phase 1 — Nền tảng release có kiểm thử

- Thêm `release.json` và một nơi duy nhất đọc version.
- Thêm `requirements.txt` có version đã kiểm chứng.
- Thiết lập `tests/` bằng `unittest` hoặc `pytest`; tối thiểu có test engine/PO registry hiện hữu.
- Thêm entrypoint `--health-check` không khởi động GUI đầy đủ, kiểm tra imports, asset bắt buộc, data root có thể tạo/đọc và SQLite mở được.
- Tạo spec cho migration packaging/update và cập nhật `HANDOVER.md` khi contract thay đổi.

Acceptance:

- app source chạy được;
- health-check source/bundle exit `0`;
- test QR, total quantity, PO sequence và duplicate combo pass;
- metadata version nhất quán.

### Phase 2 — Tách runtime data khỏi code

- Tạo module path/runtime ownership.
- Tách app bundle dir, versioned app dir, install root, user-data root và output root.
- Migrate one-time, idempotent từ vị trí portable cũ sang data root với thông báo rõ ràng.
- Seed layout mặc định không ghi đè user layout.
- Chuyển `po_registry.db` sang data root; checkpoint/backup an toàn cho migration.
- Không tự copy template/layout cạnh EXE nữa.

Acceptance:

- cập nhật/reinstall không làm mất PO registry hoặc layout;
- template bundle vẫn mở được;
- output không được ghi vào thư mục app version;
- migration chạy hai lần không duplicate/corrupt data.

### Phase 3 — PyInstaller onedir và launcher

- Thay `build_exe.py` one-file bằng entrypoint packaging `onedir`.
- Tạo portable app spec và launcher spec riêng.
- Bundle include: app executable, dependencies, `template.pdf`, default layout, `release.json`, default update-source config.
- Build install bundle theo `apps/<version>`, `current.json`, launcher.
- Launcher chỉ resolve entrypoint trong version dir đã hash manifest; hỗ trợ `--health-check`.

Acceptance:

- app and launcher health-check pass từ bundle cô lập;
- launcher mở đúng version trong `current.json`;
- dữ liệu user không nằm trong bundle;
- build không phụ thuộc Python trên máy người dùng.

### Phase 4 — Inno Setup installer

- Tạo `installer\InPhieuHienVat.iss` với Inno Setup 6.
- Cài bundle vào `%LOCALAPPDATA%\InPhieuHienVat`, `PrivilegesRequired=lowest`.
- Shortcut gọi launcher.
- Uninstall chỉ xóa staging/code theo chính sách đã chốt; không tự xóa `InPhieuHienVatData`, output hoặc backups.
- Thêm Vietnamese `.isl` đã pin/version-controlled nếu cần giao diện tiếng Việt nhất quán.

Acceptance:

- cài trên Windows sạch không cần Python;
- startup, import Excel, preview và tạo PDF pass;
- uninstall không xóa `po_registry.db`, layout, output;
- installer artifact có version/hash/release note record.

### Phase 5 — Core updater an toàn

- Tạo module manifest, SHA-256, safe ZIP extraction, version compare và catalog validation.
- Tạo package update (ví dụ `.phieuupdate`) chứa full onedir app và `manifest.json` inventory.
- Tạo config update source có precedence: bundled default → user override → company policy.
- Tạo `latest.json` và publish atomically (`.part` → hash/size → package final → `latest.json` last).
- Stage → verify → health-check → SQLite-safe backup → activate pointer → previous pointer.
- Cung cấp rollback từ launcher/app khi version cũ còn nguyên vẹn.

Acceptance:

- reject downgrade, hash sai, size sai, package có file thừa/thiếu, path traversal và manifest sai;
- health-check fail không đổi current pointer;
- update thành công giữ nguyên PO/layout/output;
- rollback quay về binary cũ mà không làm mất data;
- mọi activation/publish đều atomic.

### Phase 6 — UI cập nhật và vận hành phát hành

- Thêm kiểm tra update background, thông báo version/release note, nút cập nhật và trạng thái lỗi thân thiện.
- Cache update local trước khi cài; app mới chờ process cũ thoát rồi khởi động.
- Viết release playbook và release note theo version.
- Thêm test integration cho folder source; pilot trên máy có bản cũ.

Acceptance:

- user có thể kiểm tra/cài update từ GUI mà không khóa UI;
- pilot update từ version cũ sang version mới pass;
- xác minh sau publish: local hash = LAN hash = `latest.json` hash; không còn `.part`;
- có log/evidence release và hướng dẫn rollback.

## 8. Luồng phát hành mục tiêu

### 8.1 Cài mới hoặc cài lại

```text
source + tests
 -> package onedir
 -> portable health-check
 -> assemble install bundle
 -> launcher health-check
 -> compile Inno Setup
 -> clean-machine smoke
 -> publish Setup (nếu được ủy quyền)
```

### 8.2 Auto-update

```text
verify current catalog/version
 -> tests + package + health-check
 -> build update package + manifest
 -> publish package .part
 -> verify size/SHA-256
 -> rename package atomically
 -> publish latest.json last
 -> pilot update
 -> record release evidence
```

Điều kiện phải dừng trước publish:

- version metadata không khớp;
- test/health-check fail;
- endpoint update không đọc/ghi được;
- version không tăng;
- cùng tên/version nhưng hash artifact khác;
- không có quyền publish rõ ràng;
- không xác nhận được bảo toàn dữ liệu SQLite WAL.

## 9. Kiểm thử bắt buộc trước release

| Nhóm | Tối thiểu |
|---|---|
| Engine | mapping A:J, total quantity, lot spaces, QR fixed-width |
| PO | sequence date, limit 99, duplicate composite key, persistence |
| Runtime migration | copy idempotent, user layout retained, SQLite WAL snapshot retained |
| Package | assets + metadata present, health-check pass |
| Launcher | current pointer valid, manifest hash mismatch rejected, previous pointer rollback |
| Installer | cài máy sạch, shortcut, uninstall data preservation |
| Updater | catalog/package/file hashes, downgrade rejection, safe extraction, health failure, backup, activation, rollback |
| Pilot | update bản cũ thật, tạo PDF sau update, PO duplicate vẫn bị chặn |

## 10. Hướng dẫn vận hành source (và lịch sử trước migration)

- Chạy `release_clean\InPhieuHienVat.exe` hoặc source theo phần 2.
- Không di chuyển/xóa `po_registry.db`; làm vậy sẽ mất lịch sử uniqueness và counter PO.
- Không thay `template.pdf` hoặc `layout_config.json` cạnh EXE nếu chưa sao lưu; app ưu tiên file bên ngoài bundle.
- Không sửa trực tiếp `build\`, `dist\`, `release_clean\` để thay logic source.
- Không coi artifact hiện có là installer/update package.

## 11. Những việc đã làm trong phiên phân tích này

- Phân tích đầy đủ luồng Inno Setup/update của `D:\Sandbox\MP2027` bằng graph và source/playbook liên quan.
- Xác định mô hình `HASH_ONLY_LAN`, launcher versioned, atomic catalog publish, health-check, backup và rollback.
- Đối chiếu app hiện tại: one-file, chưa versioned, chưa có installer/updater, data nằm cạnh EXE.
- Xác định rủi ro đặc thù: `po_registry.db` dùng SQLite WAL, vì vậy backup/migration không thể chỉ copy `.db` khi app đang mở.
- Chưa sửa source packaging/update. Chỉ cập nhật tài liệu handover này.

## 12. Điểm bắt đầu cho người tiếp theo

1. Đọc tài liệu này và kiểm tra file thực tế.
2. Chốt sáu quyết định ở Phase 0 với chủ sở hữu.
3. Tạo Spec Kit artifacts cho feature packaging/update.
4. Bắt đầu từ Phase 1, không nhảy thẳng vào Inno/updater.
5. Sau mỗi milestone, cập nhật handover và lưu checkpoint AgentMemory gồm project path, quyết định, file đổi, kết quả kiểm thử và bước kế tiếp.

Các file cần mở trước khi sửa:

- `slip_printer_app.py` — path ownership và GUI;
- `po_registry.py` — persistence/WAL;
- `build_exe.py` — entrypoint build cần thay thế;
- `slip_printer_engine.py` — contract PDF/Excel không được phá;
- `.antigravityrules` — bắt buộc Graphify trước code và Spec Kit trước source/test changes.

## 12. Triển khai thực tế ngày 2026-08-14

### 12.1 File mới/thay đổi

| File | Vai trò |
|---|---|
| `runtime_paths.py` | Tách dữ liệu ghi được khỏi app bundle; migrate an toàn layout/SQLite cũ vào `%LOCALAPPDATA%\InPhieuHienVatData` và output vào Documents. |
| `release.json` | Version/channel/schema phát hành; bản hiện tại `0.1.0`, channel `pilot`. |
| `update_sources.default.json` | Cấu hình update mặc định an toàn: không tự kiểm tra và không có nguồn production hard-code. |
| `update_security.py` | Manifest canonical JSON, SHA-256, path allow-list, verify zip và safe extract. |
| `app_updates.py` | Stage → health-check → backup SQLite/layout → atomic pointer activation; rollback `previous.json`. |
| `update_delivery.py` | Đọc catalog `latest.json`, folder/LAN source, tải cache, kiểm tra hash/kích thước. |
| `update_launcher.py` | Launcher ổn định, chỉ mở entrypoint được trỏ bởi `current.json` có hash manifest hợp lệ. |
| `package_app.py` | Build app/launcher onedir, lắp bundle, tạo `.phieuupdate`, publish catalog nguyên tử. |
| `installer\InPhieuHienVat.iss` | Cài đặt per-user bằng Inno Setup, shortcut gọi launcher, không xóa user data lúc uninstall. |
| `slip_printer_app.py` | Dùng runtime paths, `--health-check`, nút kiểm tra update và flow cài/restart update. |

`template.pdf`, `layout_config.json`, `release.json` và cấu hình nguồn update nằm tại `apps/<version>/_internal` trong PyInstaller onedir. Đây là cấu trúc đúng của PyInstaller; không đổi validator thành kiểm tra asset ở root.

### 12.2 Layout sau cài đặt

```text
%LOCALAPPDATA%\InPhieuHienVat\
  InPhieuHienVat_Launcher.exe
  _internal\...
  current.json
  previous.json                 (chỉ có sau update thành công)
  apps\0.1.0\
    InPhieuHienVat.exe
    _internal\template.pdf, layout_config.json, release.json, ...
    manifest.json
  backups\<timestamp>-before-<version>\   (chỉ có sau update)

%LOCALAPPDATA%\InPhieuHienVatData\
  po_registry.db
  layout_config.json
  update_sources.json            (override tùy chọn)
  .updates\downloads\

Documents\InPhieuHienVat\output\
```

Không xóa `%LOCALAPPDATA%\InPhieuHienVatData` hoặc output khi uninstall. `po_registry.db` được copy bằng SQLite backup API (WAL-safe), không copy thô file `.db`.

### 12.3 Build release và installer

1. Sửa `release.json`; version phải là SemVer mới và đồng bộ `#define AppVersion` trong `installer\InPhieuHienVat.iss`.
2. Chạy `python package_app.py`. Kết quả là `release_artifacts\install_bundle`.
3. Compile: `& 'C:\Users\<user>\AppData\Local\Programs\Inno Setup 6\ISCC.exe' '.\installer\InPhieuHienVat.iss'`.
4. Artifact cần bàn giao: `release_artifacts\InPhieuHienVat_Setup_<version>.exe`.

Installer dùng `compiler:Default.isl`, không phụ thuộc `Vietnamese.isl` vì gói ngôn ngữ này không có trong mọi máy compiler. Ứng dụng đã cài vẫn là giao diện tiếng Việt.

### 12.4 Tạo và publish update LAN

Chỉ người được ủy quyền mới được ghi vào folder publish. Ví dụ một share đã được kiểm soát quyền:

```powershell
python package_app.py --build-update --min-app-version 0.1.0 --publish-dir '\\server\share\InPhieuHienVat\pilot' --release-notes 'Nội dung thay đổi'
```

Lệnh tạo `InPhieuHienVat-<version>.phieuupdate`, copy/verify artifact rồi publish `latest.json` sau cùng bằng file tạm + replace. Không copy đè package hoặc `latest.json` thủ công.

Để opt-in ở client, tạo `%LOCALAPPDATA%\InPhieuHienVatData\update_sources.json`:

```json
{
  "schema": 1,
  "startup_check": false,
  "sources": [
    {"type": "folder", "location": "\\\\server\\share\\InPhieuHienVat\\pilot", "enabled": true}
  ]
}
```

Người dùng bấm **Kiểm tra cập nhật** để discover. App chỉ nhận catalog/package đúng schema, hash/kích thước, version tăng và `min_app_version` hợp lệ. Khi cài: package được stage trong `apps/<version>`, health-check trước activation, backup runtime state, ghi `previous.json`/`current.json` nguyên tử, rồi launcher khởi động bản active.

### 12.5 Rollback và sự cố

- Nếu health-check/stage thất bại: không đổi `current.json`; staging bị xóa.
- Nếu bản mới lỗi sau activation: chạy `rollback_update(app_root, paths)` từ môi trường support hoặc phục hồi `current.json` bằng nội dung `previous.json` sau khi xác nhận hash manifest.
- Khôi phục nghiệp vụ: copy lại `po_registry.db` và `layout_config.json` từ `backups\<timestamp>-before-<version>`; không ghi đè khi chưa đóng app.
- Không có HTTPS, Authenticode hay chữ ký bất đối xứng trong scope hiện tại. Mô hình là `HASH_ONLY_LAN`: ACL của share publish là ranh giới tin cậy; hash phát hiện hỏng/tamper sau khi catalog đã tin cậy.

### 12.6 Bằng chứng kiểm thử đã chạy

| Kiểm tra | Kết quả |
|---|---|
| AST parse các module runtime/package/update/launcher và app | Pass |
| Source `--health-check` với data/output tạm | Pass |
| Migration SQLite backup + tách runtime paths | Pass |
| Verify/safe extract `.phieuupdate` | Pass |
| Simulated stage → backup → activation → rollback | Pass |
| Launcher fake pointer/manifest và bundle launcher health-check | Pass |
| PyInstaller onedir app + launcher | Pass |
| Inno Setup 6.7.3 compile | Pass; setup `0.1.0` tạo được |
| Silent install vào thư mục smoke-test + launcher health-check | Pass |
| Publish catalog folder + discover/fetch/hash + bỏ qua cùng version | Pass |

### 12.7 Hạn chế và việc cần làm trước production

1. Chốt đường dẫn UNC production, ACL publisher/read-only client và quy trình tăng version; hiện default source rỗng có chủ đích.
2. Chạy pilot từ một bản cũ thật đến bản mới thật, sau đó in PDF và thử duplicate PO để xác nhận nghiệp vụ không đổi.
3. Thêm automated tests vào repository khi team chốt test runner; hiện smoke tests chưa được lưu thành test suite.
4. Cân nhắc Authenticode và/hoặc chữ ký catalog/package nếu update rời LAN trusted.
5. Không publish bản `0.1.0` trở lại như update cho bản `0.1.0`; update phải có version cao hơn.

## 13. EDI label-only: 4 tem trên một A4

Từ `2026-08-14`, output PDF không còn in nguyên trang `template.pdf`. Mỗi `SlipRecord` (một dòng dữ liệu/EDI) chỉ in vùng tem EDI ở góc trên-phải của template, rồi ghép các tem lên trang A4 dọc.

| Số dòng dữ liệu | Kết quả |
|---:|---|
| 1 | 1 trang A4, chỉ có 1 tem ở góc trên-trái; phần còn lại trắng. |
| 2–4 | 1 trang A4, xếp theo thứ tự trên-trái, trên-phải, dưới-trái, dưới-phải. |
| 5–8 | 2 trang A4; trang đầu 4 tem, trang sau phần tem còn lại. |

Chi tiết kỹ thuật trong `slip_printer_engine.py`:

- Crop cố định của `template.pdf`: `Rect(558.6, 0.0, 841.92, 287.76)` (PDF point), đúng vùng người dùng đã chỉ.
- Kích thước crop được giữ nguyên, không kéo méo. A4 dọc dùng lưới 2×2, khe ngang/dọc 4 mm để cắt; tem đầu tiên luôn ở trên-trái.
- Dữ liệu/QR vẫn được overlay trên template trước khi crop, vì vậy mỗi dòng có nội dung và QR riêng; các phần Delivery Instruction/Receipt khác hoàn toàn không xuất hiện.

Các PDF kiểm tra trực quan đã tạo trong `output\\pdf`:

- `edi-1-label-a4.pdf` — 1 tem/A4.
- `edi-4-labels-a4.pdf` — 4 tem/A4.
- `edi-5-labels-a4.pdf` — kiểm tra phân trang 4 + 1.

## 14. Giao diện vận hành tối giản

Sidebar của màn hình in chỉ phục vụ luồng nghiệp vụ: **chọn Excel (nếu cần) → Import từ Excel → tạo PDF → mở PDF vừa tạo**. Template, output directory, tên file, reset path, reload preview, build script, project folder và kiểm tra update không hiển thị ở sidebar vì không cần cho thao tác in hằng ngày.

- `template.pdf` được dùng cố định bởi runtime để đảm bảo crop EDI chính xác.
- Thư mục output mặc định do runtime quản lý; tên PDF tự sinh theo thời gian.
- Xóa dữ liệu hàng loạt không có nút riêng: import Excel mới thay thế danh sách hiện có, còn từng dòng được xóa trong bảng dữ liệu.
- Kết quả xuất thông báo đúng số **tem** và số **trang A4** (`ceil(số tem / 4)`), không còn gọi nhầm mỗi dòng là một trang.

## 15. Hoàn thiện release 0.1.1 (2026-08-14)

### 15.1 Contract QR EDI đã đối chiếu PDF tham chiếu

Nguồn đối chiếu là `260211_105322(mẫu tham khảo khi xuất tem bằng phần mềm).pdf`. Đã render đủ 3 trang và giải mã QR bằng OpenCV; ba QR có cùng prefix 122 ký tự, chỉ khác trường Box cuối:

```text
112602110100010+001    0000000100003W2ND25350 01            000000010000                                                  001/003
112602110100010+001    0000000100003W2ND25350 01            000000010000                                                  002/003
112602110100010+001    0000000100003W2ND25350 01            000000010000                                                  003/003
```

Contract hiện hành của `build_qr_payload`:

| Trường | Độ dài | Quy tắc |
|---|---:|---|
| PO + PO chi tiết + PO phụ | 19 | Ví dụ `1126021101` + `00010` + `+001`. |
| Khoảng cách sau PO | 4 | Cố định. |
| Tổng số lượng | 12 | 8 chữ số + 4 số `0`: `1` → `000000010000`, `180` → `000001800000`. |
| Mã hàng + khoảng trắng + Rev | 25 | Pad bên phải bằng khoảng trắng. |
| Tổng số lượng lặp lại | 12 | Cùng quy tắc trường số lượng đầu. |
| Lot | 26 | Pad bên phải bằng khoảng trắng. |
| Khoảng cách trước Box | 24 | Cố định. |
| Box | biến đổi | Giữ nguyên, ví dụ `001/003` hoặc `1`. |

Vì vậy payload có độ dài `122 + len(Box)`: `001/003` là 129 ký tự; `1` là 123 ký tự. Đã có test so sánh byte-for-byte với PDF tham chiếu và test QR tạo mới → giải mã ngược đúng payload.

### 15.2 Quy tắc Rev

`Rev` bắt buộc đúng hai chữ số từ **01–99**. Các giá trị `1`, `00`, `001`, `A1`, rỗng hoặc lớn hơn `99` bị từ chối khi nhập tay, import Excel và ngay trước khi tạo PDF. Form hiển thị `Rev (*) (01–99)` và giá trị sau khi xóa form là `01`.

### 15.3 Nhận diện và cập nhật production

- Dòng nhận diện: `Phát triển: Bùi Đức Vinh · Phòng PTHT Chế tạo` nằm dưới tiêu đề ở sidebar.
- `app_icon.ico` là icon máy in tem/QR cho cửa sổ, app, launcher và installer; `app_icon_source.png` là nguồn của icon.
- App tự kiểm tra catalog khi mở từ thư mục update LAN và yêu cầu người dùng xác nhận trước khi cài. Nút **Kiểm tra bản cập nhật** ở góc trên-phải dùng cho kiểm tra thủ công.
- Thư mục phát hành installer: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI`.
- Thư mục cập nhật: `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update`.
