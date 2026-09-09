# 🧠 AgentMemory Checkpoint

> Tự động lưu bởi Antigravity theo **Rule 7: AgentMemory Checkpoint Protocol**
> Ngày lưu: 2026-09-07 (Asia/Bangkok)

## 1. Project Info
- **Project Name:** In Phiếu Hiện Vật (`phieu-hien-vat-printer`)
- **Project Path:** `D:\Sandbox\PM_in_lai_phieuhienvat`
- **GitHub Repository:** `https://github.com/Nakazasen/phieu-hien-vat-printer`
- **Current Version:** `v0.1.5`

## 2. Completed Work (Đã xong trong phiên 2026-09-07)
1. **Khắc phục lỗi lệch 10 lần số lượng (Fixed-Point 9.3 Standard):**
   - Phân tích và đối soát với 11 tem mẫu thực tế từ nhà cung cấp Kyocera EDI.
   - Nguyên nhân: Code cũ ngộ nhận trường 12 ký tự số lượng gồm 8 số nguyên + 4 số 0 cố định (nhân/chia 10,000), dẫn đến quét tem 2400 pcs bị đọc thành 240 pcs, và in tem 2400 pcs bị phóng đại thành 24,000 pcs.
   - Khắc phục: Chuẩn hóa trường 12 ký tự sang định dạng fixed-point 9.3 (`value * 1000`, 12 số zero-padded). 2400 pcs -> `000002400000`, 4800 pcs -> `000004800000`. Bổ sung kiểm tra tràn số `>= 10**12`.
2. **Tách biệt 2 cụm số lượng trong mã QR 129 ký tự:**
   - Cụm 1 (index 23:35): Format `total_qty` (Tổng số lượng toàn đơn).
   - Cụm 2 (index 60:72): Format `carton_qty` (Số lượng thực tế trong từng thùng), chấm dứt hoàn toàn lỗi lặp lại `total_qty`.
3. **Nâng cấp bộ giải mã QR (`parse_qr_payload`):**
   - Đọc trực tiếp `total_qty` và `carton_qty` từ 2 vị trí độc lập, chia cho 1000.
   - Hỗ trợ fallback tương thích ngược cho tem cũ in lặp số lượng (`multiplier > 1 and raw_carton_qty == raw_total_qty`).
   - Xử lý mượt mà số lượng có dấu phân cách hàng nghìn (dấu phẩy `,`).
4. **Cập nhật UI Quét QR (`ui/components/qr_scan_dialog.py`):**
   - Đổi thứ tự gán biến UI: gán `box_var` trước `total_qty_var` để tránh race condition từ trace callback `sync_total_qty`.
5. **Kiểm thử tự động:**
   - 40/40 test QR/Engine pass 100%.
   - 564/565 test toàn project pass 100% (1 test skipped có chủ đích).
   - Đối soát khớp 100% byte-for-byte với 4 tem mẫu thực tế từ nhà cung cấp.

## 3. Decisions Made (Quyết định kiến trúc)
- Tuân thủ chặt chẽ chuẩn Kyocera EDI fixed-point 9.3 (scaled by 1000).
- Không cho phép số lượng âm hoặc vượt quá 999,999,999.999 (bảo vệ cấu trúc 129 ký tự của QR).
- Hỗ trợ tương thích ngược thông minh khi quét lại các tem cũ in sai để tự động tính lại số lượng thùng.

## 4. Modified Files
- `core/slip_printer_engine.py` (format_string_qty, build_qr_payload, parse_qr_payload, calculate_total_qty)
- `ui/components/qr_scan_dialog.py` (thứ tự gán box_var và total_qty_var)
- `HANDOVER.md` (cập nhật hợp đồng QR 129 ký tự và ví dụ chuẩn từ nhà cung cấp)
- `tests/test_engine.py`, `tests/test_qr_operations.py`, `tests/test_qr_scan_tab.py`, `tests/test_adversarial_stress.py`, `tests/test_ui_layout.py`
- `AgentMemory.md`

---

## 5. Completed Work (Phiên 2026-09-09: Khắc phục lỗi xen dấu '/' và thiết kế lại ô đóng dấu QC)
1. **Khắc phục lỗi xen dấu '/' trong Số lượng giao (Delivery QTY Collision):**
   - Phân tích nguyên nhân: Khi bật hiển thị tổng số lượng (`hide_total_qty = False`), `carton_qty` ("1600") bị vẽ tại `x = 705` trong khi dấu gạch chéo `'/'` căn giữa tại `x = 710`, dẫn đến dấu gạch chéo cắt xuyên qua giữa chữ số `1` và `600`, tạo thành hiển thị sai lệch `1/600  1600`.
   - Khắc phục: Chuẩn hóa logic trong `core/slip_printer_engine.py`: khi hiển thị 2 số lượng, `carton_qty` tự động fallback về `left_x = 670` (kể cả khi file config lưu 705), dấu gạch chéo căn giữa tại `x = 710`, và `total_qty` tại `x = 750` -> Hiển thị chuẩn mực `1600  /  1600`.
   - Khôi phục giá trị mặc định trong `DEFAULT_LAYOUT_CONFIG` và `layout_config.json` về `x: 670`.
2. **Tái thiết kế ô đóng dấu QC trên `template.pdf` (Line QC & Part QC):**
   - Vấn đề: Kích thước ô vuông cũ quá nhỏ ($16.6\text{ mm} \times 11.6\text{ mm}$), không thể đóng vừa con dấu QC tiêu chuẩn nhà máy tại Việt Nam ($20\text{ mm} \times 20\text{ mm}$ hoặc tròn $\varnothing 20\text{ mm}$ như Shiny S-520, Trodat 4922, Shiny R-520).
   - Giải pháp kiến trúc:
     * Tận dụng $15.5\text{ mm}$ khoảng trống trắng thừa tự nhiên bên trái (từ $x = 558$ đến $732$).
     * Mở rộng ô QC sang trái (bắt đầu từ $x = 625$ đến $1110$), tăng chiều rộng mỗi ô từ $16.6\text{ mm}$ lên **$21.4\text{ mm}$** ($> 20\text{ mm}$).
     * Gộp ô chữ nhật nhãn phía dưới vào thành một ô liền mạch cao **$18.0\text{ mm}$** ($y = 16$ đến $220$).
     * Chuyển nhãn chữ "Line QC" và "Part QC" lên mép trên làm tiêu đề gọn gàng, để lại toàn bộ diện tích bên dưới hoàn toàn thông thoáng cho thao tác đóng dấu.
   - Cập nhật trực tiếp `template.pdf` (`xref 79` & `81`).
3. **Kiểm thử tự động & Xác thực trực quan:**
   - Thêm `test_delivery_qty_no_collision_when_total_shown` và `test_template_qc_boxes_expanded` vào `tests/test_template_new_design.py`.
   - Toàn bộ test suite cốt lõi (39/39 tests) pass 100%.
   - Xuất ảnh kiểm chứng thực tế: `scratch/verified_slip_dual_qty.png` và `scratch/verified_slip_single_qty.png`.

---

## 6. Release & LAN Deployment (v0.1.5 - 2026-09-09)
1. **Biên dịch & Đóng gói:**
   - Cập nhật phiên bản lên `0.1.5` trong `release.json` và `installer/InPhieuHienVat.iss`.
   - Build PyInstaller onedir: `dist/InPhieuHienVat` và `dist/InPhieuHienVat_Launcher`.
   - Biên dịch bộ cài đặt Inno Setup: `release_artifacts/InPhieuHienVat_Setup_0.1.5.exe` (114,471,992 bytes).
   - Tạo gói tự động cập nhật: `release_artifacts/InPhieuHienVat-0.1.5.phieuupdate` (154,717,789 bytes, sha256: `b8718a3684f5...`).
   - Tạo danh mục cập nhật cục bộ: `release_artifacts/latest.json`.
2. **Phát hành lên mạng nội bộ KDTVN (Atomic Publishing):**
   - Thư mục Cài đặt (Setup): `\\fstvn01\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\Hang muc can luu\Vinh\PMintemEDI`
     * Phát hành file mới: `InPhieuHienVat_Setup_0.1.5.exe`.
     * Di chuyển bản cũ: `InPhieuHienVat_Setup_0.1.4.exe` được chuyển an toàn vào thư mục con `old/`.
   - Thư mục Tự cập nhật (Auto-Update): `...\PMintemEDI\release_update`
     * Phát hành gói mới: `InPhieuHienVat-0.1.5.phieuupdate` và `latest.json`.
     * Di chuyển các bản cũ: `InPhieuHienVat-0.1.2.phieuupdate`, `0.1.3`, `0.1.4` được chuyển an toàn vào thư mục con `old/`.
3. **Kiểm thử & Nghiệm thu:**
   - 96/96 unit/integration/adversarial tests pass 100%.
   - Toàn vẹn checksum SHA-256 đối soát giữa Local và LAN trùng khớp 100%.
   - Cả 2 thư mục gốc trên LAN chỉ giữ duy nhất phiên bản mới nhất `v0.1.5`, toàn bộ bản cũ đã nằm gọn trong `old/`.

---

## 7. Hotfix v0.1.6 & Khóa an toàn chống trùng PO khi Mất mạng (2026-09-09)
1. **Khôi phục gạch chéo `/` trong Số lượng giao (Dual Delivery QTY):**
   - Khôi phục lệnh vẽ `pdf_canvas.drawCentredString(710, height - item['y'], '/')` và `qty_right_2` trong `DEFAULT_LAYOUT_CONFIG`.
   - Căn lề chuẩn mực: `20` tại $x=670$, `/` tại $x=710$, `40` tại $x=750$.
2. **Cơ chế Khóa an toàn chống trùng số PO khi Offline (Fail-Closed Gate):**
   - Bổ sung ngoại lệ `OfflinePOGenerationBlockedError` trong `core/po_registry.py`.
   - Khi mất kết nối mạng LAN tới `\\fstvn01\...\po_registry.db`: hệ thống CHẶN tự động sinh PO mới để loại trừ triệt để nguy cơ 2 máy sinh trùng số PO.
   - Bổ sung nút mở khóa `🔓` tại trường PO trên giao diện `DataTabPanel` cho phép nhập tay PO do QLSX cấp.
   - Bổ sung huy hiệu trực quan `[🟢 LAN DB Đã kết nối]` / `[🔴 Mất kết nối LAN (Khóa tự sinh PO)]` trên thanh tiêu đề.
   - Nghiệp vụ in lại (quét mã QR có sẵn PO hoặc nạp Excel có sẵn PO) vẫn hoạt động bình thường khi offline.
3. **Kiểm thử & Phát hành v0.1.6:**
   - Toàn bộ bài test pass 100%.
   - Phát hành gói cập nhật tự động `InPhieuHienVat-0.1.6.phieuupdate` và bộ cài `InPhieuHienVat_Setup_0.1.6.exe` lên LAN.
