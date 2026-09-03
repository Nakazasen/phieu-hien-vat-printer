# 🧠 AgentMemory Checkpoint

> Tự động lưu bởi Antigravity theo **Rule 7: AgentMemory Checkpoint Protocol**
> Ngày lưu: 2026-09-03 (Asia/Bangkok)

## 1. Project Info
- **Project Name:** In Phiếu Hiện Vật (`phieu-hien-vat-printer`)
- **Project Path:** `D:\Sandbox\PM_in_lai_phieuhienvat`
- **GitHub Repository:** `https://github.com/Nakazasen/phieu-hien-vat-printer`
- **Current Version:** `v0.1.3`

## 2. Completed Work (Đã xong trong phiên 2026-09-03)
1. **Đồng bộ mã nguồn từ GitHub:**
   - Kéo (pull) thành công commit `7bc1e0a` (phôi phiếu EDI 3 ô chữ ký, căn chỉnh chính xác, script khởi chạy mới).
2. **Khắc phục triệt để lỗi không khởi động được của `run.bat` & `build_exe.bat`:**
   - Nguyên nhân: `run.bat` ưu tiên chọn `D:\Sandbox\.venv` là môi trường ảo chung/trống thiếu `customtkinter` và `fitz`.
   - Khắc phục: Bổ sung Validation Gate kiểm tra lệnh import thư viện trước khi gán `PYTHON_EXE`, đồng thời tự động fallback sang binary exe đã đóng gói nếu không có Python hợp lệ.
3. **Tiêu chuẩn hóa hệ thống Auto-Update theo chuẩn MP2027:**
   - Chuyển giao và biên soạn tài liệu vận hành: `huongdansetup_autoupdate.md` và `docs/handover/release_update_playbook.md`.
   - Nâng cấp `updater/update_delivery.py`: bổ sung tầng ưu tiên Company Policy (`%PROGRAMDATA%\InPhieuHienVat\update_sources.json`).
   - Nâng cấp `package_app.py`: bổ sung cờ `--publish-lan`, Pre-publish write probe, Collision Guard chống ghi đè artifact lịch sử, và quy trình copy nguyên tử `.part`.
4. **Đóng gói và phát hành chính thức phiên bản `v0.1.3` lên 2 thư mục LAN:**
   - **Thư mục Setup:** `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\InPhieuHienVat_Setup_0.1.3.exe` (114,437,757 bytes, SHA-256 khớp 100%).
   - **Thư mục Auto-update:** `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI\release_update\InPhieuHienVat-0.1.3.phieuupdate` (154,541,225 bytes) + `latest.json`.
5. **Xử lý dứt điểm lỗi không gỡ cài đặt (Uninstall) được trên Windows:**
   - Nguyên nhân: Vết tích registry từ bài smoke test ngày 14/08/2026 trỏ vào thư mục tạm đã bị xóa `build\installer-smoke-...`.
   - Khắc phục: Xóa sạch registry key mồ côi `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{CEBD9EDE-12C7-4E8A-BD6D-67FC0F3D3F43}_is1` và dọn dẹp các lối tắt liên quan.
6. **Kiểm thử tự động:**
   - Toàn bộ 93/93 bài test (60 test updater/adversarial + 33 test po_registry/qr) pass 100%.

## 3. Decisions Made (Quyết định kiến trúc)
- Tuân thủ chính sách `HASH_ONLY_LAN`: không dùng chữ ký số, bảo vệ bằng SHA-256 + kích thước byte-level + manifest + safe extraction (Anti-Zip-Slip) + SQLite online backup.
- Áp dụng cơ chế Validation Gate cho batch scripts (`run.bat`, `build_exe.bat`) để chống xung đột giữa các virtualenv trong thư mục `D:\Sandbox`.
- Quản lý phiên bản chặt chẽ theo SemVer, nguồn sự thật duy nhất là `latest.json` trên LAN `release_update`.

## 4. Modified Files (File sửa đổi chính)
- `release.json` (bump to 0.1.3)
- `installer/InPhieuHienVat.iss` (bump AppVersion to 0.1.3)
- `run.bat` (Validation Gate cho Python environment)
- `build_exe.bat` (Validation Gate cho PyInstaller)
- `package_app.py` (publish_setup, verify_writable_share, collision guard, --publish-lan)
- `updater/update_delivery.py` (Company Policy ProgramData support)
- `huongdansetup_autoupdate.md` (mới, tài liệu chuẩn đóng gói & update)
- `docs/handover/release_update_playbook.md` (mới, playbook vận hành release)
- `HANDOVER.md` (cập nhật trạng thái ngày 2026-09-03)
- `AgentMemory.md` (checkpoint cập nhật)

## 5. Remaining Blockers
- Không có blocker nào. Tất cả tính năng, bộ cài và gói update đều đã được phát hành và kiểm chứng toàn diện.

## 6. Next Steps
- Thông báo người dùng khởi động ứng dụng trên máy trạm để xác nhận quá trình tự động cập nhật lên phiên bản 0.1.3.
