import sys

import openpyxl
from PyPDF2 import PdfReader

if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001, S110
            pass

def inspect_excel_fast(file_path):
    print(f"--- Kiểm tra nhanh file Excel: {file_path} ---")
    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb.active
        print(f"Trang tính đang chọn: {sheet.title}")
        for row in sheet.iter_rows(max_row=5, values_only=True):
            print(row)
    except Exception as e:  # noqa: BLE001
        print(f"Lỗi đọc nhanh Excel: {e}")

def inspect_pdf(file_path):
    print(f"\n--- Kiểm tra file PDF: {file_path} ---")
    try:
        reader = PdfReader(file_path)
        print(f"Số trang: {len(reader.pages)}")
        fields = reader.get_fields()
        if fields:
            print("Đã tìm thấy các trường biểu mẫu:")
            for field_name in fields:
                print(f"- {field_name}")
        else:
            print("Không tìm thấy trường biểu mẫu.")
        
        text = reader.pages[0].extract_text()
        print("\nTrích đoạn văn bản:")
        print(text[:300])
    except Exception as e:  # noqa: BLE001
        print(f"Lỗi file PDF: {e}")

if __name__ == "__main__":
    inspect_excel_fast("DummySlip.xlsx")
    inspect_pdf("template.pdf")
