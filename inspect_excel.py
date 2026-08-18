import sys

import pandas as pd
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

def inspect_excel(file_path):
    print(f"--- Kiểm tra file Excel: {file_path} ---")
    try:
        # Đọc 10 dòng đầu để xem cấu trúc
        df = pd.read_excel(file_path, header=None).head(10)
        print(df.to_string())
    except Exception as e:  # noqa: BLE001
        print(f"Lỗi đọc file Excel: {e}")

def inspect_pdf(file_path):
    print(f"\n--- Kiểm tra file PDF: {file_path} ---")
    try:
        reader = PdfReader(file_path)
        print(f"Số trang: {len(reader.pages)}")
        
        # Kiểm tra trường biểu mẫu (form fields)
        fields = reader.get_fields()
        if fields:
            print("Đã tìm thấy các trường biểu mẫu:")
            for field_name in fields:
                print(f"- {field_name}")
        else:
            print("Không tìm thấy trường biểu mẫu. Khả năng vẽ theo tọa độ.")
            
        # Trích xuất một số văn bản để xem nội dung tĩnh
        first_page_text = reader.pages[0].extract_text()
        print("\nTrích đoạn văn bản trang đầu:")
        print(first_page_text[:500])
        
    except Exception as e:  # noqa: BLE001
        print(f"Lỗi file PDF: {e}")

if __name__ == "__main__":
    inspect_excel("DummySlip.xlsx")
    inspect_pdf("template.pdf")
