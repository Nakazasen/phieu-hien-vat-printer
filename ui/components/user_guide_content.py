"""Structured content and asset paths for the Real-User Visual Guide (Cẩm nang Hướng dẫn Sử dụng Trực quan).

Replaces the legacy spotlight overlay method with a comprehensive 6-chapter visual manual
built from real screenshots of the live application populated with production data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.runtime_paths import bundle_dir


def get_user_guide_assets_dir() -> Path:
    """Resolve the directory containing generated user guide screenshots, HTML, and PDF manuals."""
    bundled = bundle_dir() / "assets" / "user_guide"
    if bundled.is_dir():
        return bundled
    repo_fallback = Path(__file__).resolve().parents[2] / "assets" / "user_guide"
    return repo_fallback


USER_GUIDE_CHAPTERS: list[dict[str, Any]] = [
    {
        "id": "ch01",
        "short_title": "1. Nhập Excel & Kiểm trùng EDI",
        "title": "Nhập dữ liệu từ Excel & Kiểm tra trùng lặp mã EDI",
        "summary": (
            "Đọc hàng loạt dữ liệu từ file Excel (.xlsx/.xlsm), tự động phát hiện và tô đỏ các dòng đã từng in "
            "(trùng Mã PO + Chi tiết + Phụ + Số thùng) trên cơ sở dữ liệu mạng LAN để ngăn chặn dán nhầm 2 tem trùng mã."
        ),
        "image_filename": "ch01_excel_import.png",
        "target_tab_index": 0,
        "steps": [
            {
                "num": 1,
                "color": "#2563EB",
                "title": "Bấm nút 'Chọn' tại mục 'Tệp Excel' rồi bấm 'Nhập từ Excel' ở cột bên trái",
                "detail": (
                    "Chọn tệp Excel kế hoạch đóng gói (.xlsx hoặc .xlsm) từ máy tính hoặc ổ mạng, sau đó bấm 'Nhập từ Excel'. "
                    "Hệ thống tự động đọc dữ liệu từ dòng 4, tự sinh số PO cho các dòng để trống PO, tự tra cứu CAV từ Server QC "
                    "và nạp toàn bộ các thùng hợp lệ vào bảng."
                ),
            },
            {
                "num": 2,
                "color": "#EF4444",
                "title": "Kiểm tra các dòng tô đỏ cảnh báo trùng lặp mã EDI trên bảng dữ liệu",
                "detail": (
                    "Ngay khi nạp xong, phần mềm đối chiếu với cơ sở dữ liệu chung trên mạng LAN. "
                    "Nếu thùng hàng đã từng được phát hành trước đó hoặc bị lặp ngay trong danh sách, cả dòng sẽ được tô nền đỏ "
                    "để người vận hành nhận biết ngay lập tức."
                ),
            },
            {
                "num": 3,
                "color": "#10B981",
                "title": "Đối chiếu hình ảnh '🔍 Xem trước tem in' thực tế ở khung bên phải",
                "detail": (
                    "Bấm vào bất kỳ dòng nào trong bảng để xem trước 100% bố cục phiếu hiện vật sẽ in ra: "
                    "bao gồm Mã vạch 1D (Code39), Mã QR 2D chuẩn 129 ký tự KDTVN, Số PO, Số lượng, CAV No. và Số thùng."
                ),
            },
            {
                "num": 4,
                "color": "#F59E0B",
                "title": "Sử dụng nút '🗑️ Xóa dòng' hoặc '🗑️ Xóa tất cả' để làm sạch danh sách",
                "detail": (
                    "• Muốn xóa 1 dòng đang chọn trên bảng: bấm nút màu đỏ '🗑️ Xóa dòng' (hoặc phím Delete).\n"
                    "• Muốn làm trống toàn bộ bảng danh sách tem: bấm nút '🗑️ Xóa tất cả' ở góc phải thanh tiêu đề bảng '📋 Danh sách tem sẵn sàng in'.\n"
                    "• Lưu ý phân biệt: Nút '🧹 Xóa biểu mẫu' chỉ xóa trắng các ô đang gõ trên biểu mẫu nhập liệu chứ không xóa bảng bên dưới."
                ),
            },
        ],
        "tips": [
            "Nếu bảng đang có cả dòng cũ đã xuất (tô đỏ) và dòng mới chưa xuất, khi bấm 'Tạo PDF' phần mềm sẽ hiện hộp thoại 'Có dòng trùng với tem đã xuất' — bạn chỉ cần bấm nút màu xanh 'Chỉ xuất X tem mới' để bỏ qua các dòng cũ và chỉ xuất đúng các tem mới.",
            "Sau khi tạo PDF thành công, phần mềm sẽ TỰ ĐỘNG dọn sạch các dòng vừa xuất khỏi bảng chờ in để bạn nhập mã hàng tiếp theo mà không lo lẫn dòng cũ.",
        ],
    },
    {
        "id": "ch02",
        "short_title": "2. Nhập tay, Tra CSV & Tách CAV",
        "title": "Nhập thủ công, Tự động tra cứu CSV (Inspection_data) & Chế độ Tách CAV",
        "summary": (
            "Chỉ cần gõ Mã hàng (*), phần mềm sẽ tự động tìm kiếm trong thư mục Inspection_data trên mạng LAN "
            "để điền Tên hàng, SL/thùng, Rev và danh sách CAV — đồng thời hỗ trợ chọn từng CAV khi bật công tắc Tách CAV."
        ),
        "image_filename": "ch02_manual_cav.png",
        "target_tab_index": 0,
        "steps": [
            {
                "num": 1,
                "color": "#10B981",
                "title": "Gõ 'Mã hàng (*)' (VD: 302YJ03340) — Tự động tra cứu CSV trên LAN",
                "detail": (
                    "Sau khi ngừng gõ khoảng 0.4 giây, phần mềm tự động tra cứu tệp CSV mới nhất trong thư mục "
                    "\\\\10.170.178.1\\...\\Inspection_data để điền chính xác Tên hàng, SL/thùng, Rev và danh sách CAV "
                    "(ví dụ: 1, 2, 3, 4 hoặc 5, 6, 7, 8) mà không cần tra sổ tay."
                ),
            },
            {
                "num": 2,
                "color": "#2563EB",
                "title": "Nhập 'SL/thùng(*)' và 'Số thùng(*)' — Hệ thống tự cấp PO 10 số (11YYMMDDNN)",
                "detail": (
                    "Ở chế độ mặc định, phần mềm tự động sinh số PO 10 chữ số theo quy tắc '11 + YYMMDD + số thứ tự trong ngày' "
                    "(ví dụ: 1126103001, Chi tiết: 00010, Phụ: +001). Nếu nhập 'Số thùng(*) = 6', hệ thống sẽ tự bung thành 6 thùng từ 001/006 đến 006/006."
                ),
            },
            {
                "num": 3,
                "color": "#F59E0B",
                "title": "Gạt công tắc 'Tách CAV' để chọn các lòng khuôn (CAV) thực tế đóng trong thùng",
                "detail": (
                    "Khi gạt công tắc 'Tách CAV', thanh chọn 'Chọn CAV in:' sẽ hiện các ô tích (checkbox) tương ứng với các CAV hợp lệ của mã hàng. "
                    "Bạn chỉ cần tích chọn đúng các số CAV cần in trên phiếu hiện vật (ví dụ: tích chọn CAV 5 và CAV 6)."
                ),
            },
            {
                "num": 4,
                "color": "#EF4444",
                "title": "Bấm '➕ Thêm mới' để đưa xuống bảng (hoặc '🧹 Xóa biểu mẫu' để nhập lại)",
                "detail": (
                    "Bấm '➕ Thêm mới' để tạo các dòng tem xuống bảng '📋 Danh sách tem sẵn sàng in'. "
                    "Nếu muốn xóa trắng các ô nhập liệu để gõ mã khác, bấm '🧹 Xóa biểu mẫu'. Nếu muốn làm trống cả bảng bên dưới, bấm '🗑️ Xóa tất cả'."
                ),
            },
        ],
        "tips": [
            "Nếu xuất PDF xong một lô và tiếp tục gõ mã hàng mới, phần mềm đã tự động dọn bảng và cấp số PO mới tiếp theo trong ngày (ví dụ từ 1126103001 lên 1126103002).",
            "Khi bật/tắt công tắc 'Tách CAV' hoặc tích chọn các ô CAV, ảnh Xem trước bên phải sẽ cập nhật ngay lập tức để bạn kiểm tra ô CAV No. trước khi in.",
        ],
    },
    {
        "id": "ch03",
        "short_title": "3. Quét QR: Phân tách / Hoàn kho",
        "title": "Quét mã QR — Phân tách (分割), Hoàn kho (戻入) & Cấp lại phiếu",
        "summary": (
            "Sử dụng súng bắn mã vạch 2D quét trực tiếp lên tem hiện vật cũ để giải mã 129 ký tự EDI: "
            "tự động tính toán số lượng còn lại và cấp số PO nhánh chuẩn quy định KDTVN cho nghiệp vụ Chia lẻ thùng hoặc Hoàn kho."
        ),
        "image_filename": "ch03_qr_scan.png",
        "target_tab_index": 3,
        "steps": [
            {
                "num": 1,
                "color": "#2563EB",
                "title": "Chuyển sang tab '📷 Quét QR' và bắn mã QR trên tem gốc",
                "detail": (
                    "Đặt con trỏ chuột vào ô nhập mã QR rồi bóp cò súng quét mã vạch (hoặc dán chuỗi QR 129 ký tự và nhấn Enter). "
                    "Hệ thống lập tức bóc tách Mã linh kiện, Tên hàng, Số PO gốc, Số lượng gốc và Số thùng."
                ),
            },
            {
                "num": 2,
                "color": "#F59E0B",
                "title": "Chọn đúng chế độ nghiệp vụ: Phân tách (分割) / Hoàn kho (戻入) / Cấp lại phiếu",
                "detail": (
                    "• Phân tách (分割 - Chia nhỏ): Tách 1 thùng lớn thành các thùng nhỏ hơn (mã đuôi 10010, 20010...).\n"
                    "• Hoàn kho (戻入 - Trả kho): Nhập lại hàng dư về kho với số lượng thực tế (mã đuôi 80010, 90010...).\n"
                    "• Cấp lại phiếu (Reissue): In lại nguyên trạng tem bị rách/mờ."
                ),
            },
            {
                "num": 3,
                "color": "#10B981",
                "title": "Nhập Số lượng tách mới — Hệ thống tự động kiểm tra và trừ lùi",
                "detail": (
                    "Nhập số lượng cần tách ra (nhỏ hơn số lượng gốc trên tem). Khung xem trước bên dưới sẽ hiển thị "
                    "rõ chuỗi QR 129 ký tự mới và số PO chi tiết được hệ thống tự động cấp phát."
                ),
            },
            {
                "num": 4,
                "color": "#EF4444",
                "title": "Bấm '✅ Xác nhận & Đưa vào danh sách in'",
                "detail": (
                    "Dòng dữ liệu sau khi tách/hoàn kho sẽ được chuyển thẳng sang bảng danh sách in ở Tab 1 để bạn "
                    "kết xuất ra file PDF cùng các tem khác."
                ),
            },
        ],
        "tips": [
            "Nếu súng quét mã vạch đang để chế độ gõ tiếng Việt (Unikey), hãy chuyển sang chế độ Tiếng Anh (EN) để tránh bị biến dạng ký tự trong chuỗi QR 129 ký tự.",
            "Hệ thống lưu vết toàn bộ lịch sử các lần Phân tách (分割) của cùng 1 thùng để tự động tăng số thứ tự nhánh mà không bị trùng.",
        ],
    },
    {
        "id": "ch04",
        "short_title": "4. Xem trước Tem & Xuất PDF In ấn",
        "title": "Xem trước Tem hiện vật & Xuất file PDF in ấn (Chuẩn A4 / Letter)",
        "summary": (
            "Hiểu rõ ý nghĩa từng vùng thông tin trên phiếu hiện vật (現品票) và quy trình xuất file PDF "
            "chuẩn kích thước thực 100% (A4: 6 tem/trang hoặc Letter: 4 tem/trang có khe cắt 5.0mm)."
        ),
        "image_filename": "ch04_pdf_export.png",
        "target_tab_index": 0,
        "steps": [
            {
                "num": 1,
                "color": "#F59E0B",
                "title": "Chọn khổ giấy in phù hợp với phôi giấy tại xưởng (A4 hoặc Letter)",
                "detail": (
                    "• A4 (6 phiếu/trang): Dàn 2 cột × 3 hàng cho giấy A4 tiêu chuẩn.\n"
                    "• Letter (4 phiếu/trang): Dàn 2 cột × 2 hàng với lề trên/dưới rộng và khe cắt ngang 5.0mm chính giữa."
                ),
            },
            {
                "num": 2,
                "color": "#10B981",
                "title": "Bấm nút 'Tạo PDF' (Tự động lưu lịch sử EDI & dọn sạch bảng chờ in)",
                "detail": (
                    "Khi bấm 'Tạo PDF' ở cột trái, phần mềm xuất file PDF chuẩn kích thước thực, đồng thời đăng ký mã EDI lên mạng LAN "
                    "và tự động làm sạch các dòng vừa xuất khỏi bảng chờ in để sẵn sàng cho mã hàng tiếp theo."
                ),
            },
            {
                "num": 3,
                "color": "#2563EB",
                "title": "Bấm '📂 Mở PDF vừa tạo' và thiết lập máy in ở chế độ Actual Size (100%)",
                "detail": (
                    "Khi hộp thoại in của trình đọc PDF (Adobe Reader / Edge) hiện ra, BẮT BUỘC chọn 'Actual Size' "
                    "hoặc 'Tỷ lệ 100%' (KHÔNG chọn 'Fit to Printable Area') để kích thước tem và mã vạch không bị co nhỏ."
                ),
            },
            {
                "num": 4,
                "color": "#EF4444",
                "title": "Kiểm tra 4 vùng trọng yếu trên mặt phiếu hiện vật sau khi in",
                "detail": (
                    "1) Mã vạch 1D Code39 (Part No. & Quantity) sắc nét, không đứt nét.\n"
                    "2) Mã QR 2D góc phải hiển thị rõ ràng.\n"
                    "3) Ô 'No. (Số thùng / Khuôn)' và 'CAV No.' đúng thực tế.\n"
                    "4) Ô đóng dấu xác nhận QC (品質保証) không bị chữ đè lên."
                ),
            },
        ],
        "tips": [
            "Khi chọn khổ giấy 'Letter (4 phiếu)', phần mềm sẽ hiển thị hộp thoại nhắc nhở kiểm tra khay giấy máy in để tránh in nhầm khổ Letter lên phôi giấy A4.",
            "Tất cả các file PDF đã tạo đều được lưu tự động trong thư mục output để có thể mở lại bất cứ lúc nào.",
        ],
    },
    {
        "id": "ch05",
        "short_title": "5. Chỉnh Layout 2026 & Lịch sử EDI",
        "title": "Tùy chỉnh Layout tem 2026, Lịch sử đăng ký EDI & Kho Master linh kiện",
        "summary": (
            "Tinh chỉnh tọa độ X/Y, cỡ chữ từng trường trên phiếu theo từng dòng máy in thực tế tại xưởng, "
            "bật/tắt hiển thị Tổng số lượng & Số thứ tự thùng, và tra cứu lịch sử mã PO đã phát hành."
        ),
        "image_filename": "ch05_layout_history.png",
        "target_tab_index": 1,
        "steps": [
            {
                "num": 1,
                "color": "#10B981",
                "title": "Sử dụng 'Tùy chọn hiển thị thông minh (2026)' ở Tab Tinh chỉnh Layout",
                "detail": (
                    "Bạn có thể bật hoặc tắt 2 công tắc:\n"
                    "• Hiển thị tổng số lượng của cả lô (VD: '50 / Tổng: 200').\n"
                    "• Hiển thị số thứ tự thùng trên tổng số thùng (VD: '00001 / 4 thùng')."
                ),
            },
            {
                "num": 2,
                "color": "#2563EB",
                "title": "Tinh chỉnh tọa độ (X, Y, Rộng, Cao, Cỡ chữ) cho từng trường thông tin",
                "detail": (
                    "Chọn một trường trong bảng (ví dụ: Mã linh kiện, Mã QR, CAV No.), điều chỉnh thông số ở khung bên phải "
                    "rồi bấm 'Áp dụng cho mục đang chọn' -> '💾 Lưu làm mặc định' để áp dụng lâu dài cho máy tính đó."
                ),
            },
            {
                "num": 3,
                "color": "#F59E0B",
                "title": "Tra cứu hoặc thu hồi mã PO tại tab '🗄️ Lịch sử Đăng ký EDI' & '📦 Master Linh Kiện'",
                "detail": (
                    "• Tab 'Lịch sử Đăng ký EDI': Tìm kiếm mọi thùng hàng đã từng in theo Mã linh kiện hoặc Số PO; hỗ trợ xóa bản ghi in nhầm để cấp lại số PO.\n"
                    "• Tab 'Master Linh Kiện': Quản lý danh mục linh kiện nội bộ để tự động gợi ý khi không có mạng LAN."
                ),
            },
        ],
        "tips": [
            "Nếu vô tình chỉnh lệch bố cục tem, chỉ cần bấm nút '↺ Khôi phục mặc định gốc' ở cuối khung bên phải để đưa toàn bộ tọa độ về chuẩn nhà máy.",
            "Có thể xuất cấu hình Layout ra file JSON ('📤 Xuất JSON') để chép sang các máy tính khác trong cùng chuyền sản xuất.",
        ],
    },
    {
        "id": "ch06",
        "short_title": "6. Xử lý sự cố & Chế độ Offline",
        "title": "Xử lý sự cố thường gặp (Mất mạng LAN / Offline PO, Nạp lại CSV, Cập nhật)",
        "summary": (
            "Hướng dẫn cách xử lý nhanh tại xưởng khi đường truyền mạng LAN bị gián đoạn, khi cần nhập số PO chỉ định "
            "bằng tay, hoặc khi tệp CSV dữ liệu kiểm tra vừa được cập nhật mới."
        ),
        "image_filename": "ch06_troubleshooting.png",
        "target_tab_index": 0,
        "steps": [
            {
                "num": 1,
                "color": "#10B981",
                "title": "Quan sát đèn báo trạng thái kết nối LAN DB trên thanh tiêu đề",
                "detail": (
                    "• Đèn Xanh ('🟢 LAN DB: Đã kết nối'): Hệ thống tự động đồng bộ lịch sử chống trùng và tự cấp số PO mới.\n"
                    "• Đèn Đỏ ('🔴 LAN DB: Mất kết nối (Offline)'): Máy tính đang mất kết nối tới ổ mạng chung; phần mềm tự động chuyển sang cơ sở dữ liệu dự phòng trên máy."
                ),
            },
            {
                "num": 2,
                "color": "#F59E0B",
                "title": "Bấm nút khóa 🔓/🔒 cạnh ô 'PO (tự sinh)' khi cần tự gõ số PO thủ công",
                "detail": (
                    "Khi mất mạng LAN hoặc khi khách hàng/kế hoạch yêu cầu in đúng một số PO chỉ định (thay vì số PO 10 chữ số tự sinh), "
                    "hãy bấm vào biểu tượng 🔓 cạnh ô PO để mở khóa và gõ trực tiếp số PO vào ô."
                ),
            },
            {
                "num": 3,
                "color": "#2563EB",
                "title": "Bấm nút 🔄 (Đọc lại CSV) hoặc 📁 (Đổi thư mục CSV) khi chưa thấy mã hàng mới",
                "detail": (
                    "Nếu bộ phận QC vừa cập nhật file CSV mới vào thư mục Inspection_data, hãy bấm nút '🔄' để xóa bộ nhớ đệm "
                    "và đọc lại ngay lập tức. Nếu đường dẫn mạng thay đổi, bấm '📁' để chọn lại thư mục chứa CSV."
                ),
            },
            {
                "num": 4,
                "color": "#EF4444",
                "title": "Bấm 'Kiểm tra bản cập nhật' & Nhật ký chẩn đoán theo ngày (error_log)",
                "detail": (
                    "Phần mềm tự động kiểm tra bản cập nhật mới tại \\\\fstvn01\\...\\PMintemEDI. Mọi sự kiện thao tác, cảnh báo trùng tem "
                    "và lỗi phát sinh đều được ghi tự động theo từng ngày (error_log_YYYY-MM-DD.log) và tự động dọn dẹp các ngày cũ nhất khi vượt ngưỡng 500 MB."
                ),
            },
        ],
        "tips": [
            "Bạn có thể mở lại Cẩm nang Hướng dẫn Trực quan này bất cứ lúc nào bằng cách bấm nút '💡 Hướng dẫn' trên góc phải hoặc nhấn phím tắt F1.",
            "Nếu muốn in bộ tài liệu hướng dẫn này ra giấy A4 để dán tại bàn đóng gói, hãy bấm nút '📄 Mở / In file PDF hướng dẫn' ở góc trên của cửa sổ Hướng dẫn.",
        ],
    },
]
