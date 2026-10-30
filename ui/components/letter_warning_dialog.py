from __future__ import annotations

from pathlib import Path
from typing import Optional

import customtkinter as ctk
from PIL import Image


class LetterWarningDialog(ctk.CTkToplevel):
    """Modal dialog displaying visual explanation when user chooses Letter paper size."""

    def __init__(self, parent: ctk.CTk, on_confirm: Optional[callable] = None, on_cancel: Optional[callable] = None):
        super().__init__(parent)
        self.parent = parent
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.result = False

        self.title("Lưu ý kỹ thuật: Chuyển sang khổ giấy Letter")
        self.resizable(False, False)

        # Dialog size & position (centered over parent)
        dlg_w, dlg_h = 760, 680
        pos_x = max(0, parent.winfo_rootx() + (parent.winfo_width() - dlg_w) // 2)
        pos_y = max(0, parent.winfo_rooty() + (parent.winfo_height() - dlg_h) // 2)
        self.geometry(f"{dlg_w}x{dlg_h}+{pos_x}+{pos_y}")

        self.transient(parent)
        self.grab_set()

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel_clicked)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Header Banner
        header_frame = ctk.CTkFrame(self, fg_color=("#FEF3C7", "#78350F"), corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="⚠️  CẢNH BÁO QUY CÁCH IN: KHỔ GIẤY LETTER (IN 4 TEM/TRANG)",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#92400E", "#FEF3C7"),
        ).grid(row=0, column=0, padx=20, pady=(12, 4), sticky="w")

        ctk.CTkLabel(
            header_frame,
            text="Khổ Letter ngắn hơn A4 17.6 mm. Để bảo toàn 100% kích thước gốc tem, hệ thống sẽ in 4 tem/trang.",
            font=ctk.CTkFont(size=13),
            text_color=("#B45309", "#FDE68A"),
        ).grid(row=1, column=0, padx=20, pady=(0, 12), sticky="w")

        # 2. Scrollable / Central Content Frame with Illustration
        content_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=12)
        content_frame.grid_columnconfigure(0, weight=1)

        # Image diagram
        img_path = Path(__file__).resolve().parent.parent.parent / "letter_explanation.png"
        if img_path.is_file():
            try:
                pil_img = Image.open(img_path)
                display_w = 700
                display_h = int(pil_img.height * (display_w / pil_img.width))
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(display_w, display_h))
                img_label = ctk.CTkLabel(content_frame, text="", image=ctk_img)
                img_label.grid(row=0, column=0, padx=0, pady=(0, 14), sticky="ew")
            except Exception:  # noqa: BLE001
                pass

        # Text explanation card
        card = ctk.CTkFrame(content_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        card.grid(row=1, column=0, sticky="ew", padx=4, pady=4)
        card.grid_columnconfigure(0, weight=1)

        explanation_text = (
            "📌 NGUYÊN NHÂN KỸ THUẬT VÀ GIẢI PHÁP:\n\n"
            "1. Khổ A4 chuẩn (210 × 297 mm):\n"
            "   • Chiều dài 297 mm vừa vặn cho 3 hàng tem (3 × 97.45 mm = 292.4 mm).\n"
            "   • In đủ 6 tem / 1 tờ A4 (2 cột × 3 hàng) ở tỷ lệ 100% gốc, có khe hở dao dập 5.0 mm giữa 2 cột.\n\n"
            "2. Khổ Letter (215.9 × 279.4 mm):\n"
            "   • Chiều dài chỉ có 279.4 mm (ngắn hơn A4 tới 17.6 mm).\n"
            "   • Nếu in 3 hàng ở tỷ lệ 100% gốc (292.4 mm) thì hàng thứ 3 sẽ bị tràn ra ngoài đáy giấy 13.0 mm (máy in cắt mất chân tem).\n\n"
            "3. Giải pháp tự động khi chọn Letter:\n"
            "   • Phần mềm TUYỆT ĐỐI KHÔNG CO HÌNH (bảo toàn 100% kích thước tem gốc cho Oricon và máy quét XNHH).\n"
            "   • Tự động xếp 4 tem / 1 trang (2 cột × 2 hàng), duy trì khoảng hở dao dập 5.0 mm cả chiều dọc và chiều ngang.\n"
            "   • Số trang in trên Letter sẽ được tính theo công thức: ⌈Số tem / 4⌉."
        )

        ctk.CTkLabel(
            card,
            text=explanation_text,
            justify="left",
            font=ctk.CTkFont(size=13),
            text_color=("gray20", "gray85"),
        ).grid(row=0, column=0, padx=16, pady=14, sticky="w")

        # 3. Footer Action Buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 16))
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)

        self.btn_cancel = ctk.CTkButton(
            footer,
            text="↩  Giữ khổ A4 chuẩn (6 tem/trang)",
            height=44,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10B981",  # Emerald Green
            hover_color="#059669",
            command=self._on_cancel_clicked,
        )
        self.btn_cancel.grid(row=0, column=0, padx=(0, 10), sticky="ew")

        self.btn_confirm = ctk.CTkButton(
            footer,
            text="✓  Tôi hiểu, in khổ Letter (4 tem/trang)",
            height=44,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            hover_color=("#CBD5E1", "#475569"),
            border_width=1,
            border_color=("#94A3B8", "#64748B"),
            text_color=("#0F172A", "#F8FAFC"),
            command=self._on_confirm_clicked,
        )
        self.btn_confirm.grid(row=0, column=1, padx=(10, 0), sticky="ew")

        # UI/UX Pro Max: Keyboard ergonomics & focus management
        self.bind("<Escape>", lambda _e: self._on_cancel_clicked())
        self.btn_cancel.bind("<Return>", lambda _e: self._on_cancel_clicked())
        self.btn_confirm.bind("<Return>", lambda _e: self._on_confirm_clicked())
        self.after(60, lambda: self.btn_cancel.focus_set())

    def _on_confirm_clicked(self) -> None:
        self.result = True
        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _on_cancel_clicked(self) -> None:
        self.result = False
        if self.on_cancel:
            self.on_cancel()
        self.destroy()

