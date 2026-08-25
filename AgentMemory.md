# 🧠 AgentMemory Checkpoint

> Tự động lưu bởi Antigravity theo **Rule 7: AgentMemory Checkpoint Protocol**
> Ngày lưu: 2026-08-25

## 1. Project Info
- **Project Name:** In Phiếu Hiện Vật (`phieu-hien-vat-printer`)
- **Project Path:** `D:\Sandbox\phieu-hien-vat-printer`
- **GitHub Repository:** `https://github.com/Nakazasen/phieu-hien-vat-printer`

## 2. Completed Work (Đã xong)
- Clone repo từ GitHub về `D:\Sandbox\phieu-hien-vat-printer`, cài dependencies (thiếu `sv-ttk`, đã cài bổ sung).
- Sửa lỗi tutorial overlay bị mờ/chữ đè chữ: tách TooltipCard ra `Toplevel` riêng với opacity 100% (`tooltip_win`), giữ scrim ở 75% alpha; thêm hằng số `SCRIM_ALPHA`/`TOOLTIP_ALPHA`, hàm `_place_tooltip_window`, gắn cờ `-topmost` cho cả hai cửa sổ.
- Refactor layout theo yêu cầu người dùng (2026-08-25):
  - Sidebar: đưa nhóm "File Excel (nếu import)" + "Import từ Excel" (ngay dưới ô Excel) + "Tạo PDF"/"Mở PDF vừa tạo" lên trên cùng; cấu hình đầu ra dời xuống dưới.
  - Gom 2 nút Quét QR (sidebar + header form dữ liệu) thành 1 tab mới "📷 Quét QR" đặt cạnh "📊 Lịch sử Đăng ký EDI".
  - Refactor `qr_scan_dialog.py`: tách `QRScanPanel` tái sử dụng (embedded=True cho tab, False cho dialog); `QRScanDialog` thành wrapper mỏng có `__getattr__` delegation (giữ nguyên API cho test).
  - Tạo `ui/components/qr_scan_tab.py` (`QRScanTabPanel`): "Điền vào Form chính" tự chuyển về tab Dữ liệu, không đóng tab.
  - Tutorial step 2 trỏ vào tab QR mới (`target_tab_index=3`).
- Chạy toàn bộ test suite: 552/552 PASS (thêm 6 test mới `tests/test_qr_scan_tab.py`).
- Chạy `graphify update .` — rebuild 4553 nodes / 6373 edges.
- Tối ưu hiệu năng vẽ giao diện cho máy yếu (2026-08-25):
  - Tạo `ui/preview_renderer.py` (`AsyncPreviewRenderer`): render preview PDF (ReportLab + PyMuPDF) chuyển hoàn toàn sang background thread, debounce 90ms, LRU cache 8 mục theo (template+mtime, trường dữ liệu, layout, zoom), stale-result guard, apply kết quả trên main thread bằng poll timer (an toàn Tcl, không gọi Tk chéo thread).
  - `main_window.refresh_preview_image`: bất đồng bộ hoàn toàn — click chọn dòng/nudge layout không còn block UI.
  - `data_tab`: debounce 80ms cho `<Configure>` resize preview + cache CTkImage theo (nguồn ảnh, kích thước) — không re-thumbnail khi resize liên tục.
  - Lịch sử EDI: dirty-flag — chuyển tab chỉ truy vấn SQLite khi dữ liệu thực sự thay đổi (sau khi tạo PDF thành công).
- Chạy lại test suite: 558/558 PASS (thêm 7 test `tests/test_preview_renderer.py`).

## 3. Decisions Made (Quyết định kiến trúc)
- Overlay tách thành 2 cửa sổ: `overlay_win` (scrim bán trong suốt 75%) và `tooltip_win` (thẻ hướng dẫn đặc 100%) thay vì dùng chung một Toplevel — khắc phục bleed-through do `-alpha` áp cho toàn cửa sổ.
- Dùng `transparentcolor magenta` + `bg_color="magenta"` cho TooltipCard để giữ góc bo tròn trong suốt.
- Gom nút Quét QR thành tab: `QRScanPanel` là nguồn chân lý duy nhất của UI + logic quét; dialog và tab chỉ là 2 "host". `_get_qr_target` trong tutorial ưu tiên legacy (mock) rồi fallback về `qr_tab`.
- Sidebar sắp xếp theo luồng nghiệp vụ: Excel → Import → Tạo PDF ở trên cùng; template/output config bên dưới.
- Preview render bất đồng bộ: UI thread chỉ schedule + apply; worker thread render PDF riêng (mỗi lần mở document PyMuPDF riêng trong thread → an toàn thread); cache key gồm mtime template nên đổi template tự invalidate.

## 4. Modified Files (File sửa đổi chính)
- `ui/components/tutorial_overlay.py`
- `ui/components/qr_scan_dialog.py` (refactor: QRScanPanel + wrapper dialog)
- `ui/components/qr_scan_tab.py` (mới)
- `ui/components/sidebar.py` (reorder + bỏ nút QR + label SL/thùng, Số thùng)
- `ui/components/data_tab.py` (bỏ nút QR header, clear_form xóa hết kể cả Rev, debounce resize + cache preview, viền đậm nút Xóa form, bỏ nút Lot=10 space)
- `ui/main_window.py` (tab 📷 Quét QR, AsyncPreviewRenderer, history dirty-flag)
- `ui/preview_renderer.py` (mới)
- `ui/components/tutorial_script.py` (step 2 → tab QR)
- `ui/app_controller.py` (bỏ fill_lot_spaces, đồng bộ thuật ngữ Số thùng)
- `tests/test_qr_scan_tab.py`, `tests/test_preview_renderer.py` (mới), các test cập nhật: tutorial_script, challenger_m2_2/m3_2, tier5, adversarial_stress, ui_layout, challenger2_empirical
- `AgentMemory.md`

## 5. Remaining Blockers (Lỗi/Khúc mắc còn lại)
- Không có blocker. Chờ người dùng xác nhận UI mới trên máy thật.

## 6. Next Steps (Bước tiếp theo)
- Người dùng kiểm tra: sidebar mới (Excel/Import/Tạo PDF trên cùng), tab "📷 Quét QR" cạnh Lịch sử Đăng ký EDI, tutorial step 2 spotlight đúng tab.

