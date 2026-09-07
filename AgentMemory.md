# 🧠 AgentMemory Checkpoint

> Tự động lưu bởi Antigravity theo **Rule 7: AgentMemory Checkpoint Protocol**
> Ngày lưu: 2026-09-07 (Asia/Bangkok)

## 1. Project Info
- **Project Name:** In Phiếu Hiện Vật (`phieu-hien-vat-printer`)
- **Project Path:** `D:\Sandbox\PM_in_lai_phieuhienvat`
- **GitHub Repository:** `https://github.com/Nakazasen/phieu-hien-vat-printer`
- **Current Version:** `v0.1.3`

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
