"""In-App Visual User Guide Window (Cẩm nang Hướng dẫn Sử dụng Trực quan).

Replaces the legacy spotlight-overlay method with a non-blocking, multi-chapter
visual manual featuring real annotated application screenshots, full-screen image
zoom, instant keyword search, one-click tab jumping, and standalone HTML/PDF launchers.
"""
from __future__ import annotations

import os
from pathlib import Path
import tkinter as tk
from typing import TYPE_CHECKING, Any
import webbrowser

import customtkinter as ctk
from PIL import Image, ImageTk

from core.error_logger import log_error_event
from ui.components.user_guide_content import USER_GUIDE_CHAPTERS, get_user_guide_assets_dir

COLORS: dict[str, Any] = {
    "bg_main": ("#F1F5F9", "#0F172A"),
    "bg_card": ("#FFFFFF", "#1E293B"),
    "border": ("#CBD5E1", "#334155"),
    "text_main": ("#0F172A", "#F8FAFC"),
    "text_sub": ("#475569", "#CBD5E1"),
    "primary": "#2563EB",
    "primary_hover": "#1D4ED8",
    "secondary": ("#E2E8F0", "#334155"),
    "secondary_hover": ("#CBD5E1", "#475569"),
    "accent": "#10B981",
    "accent_hover": "#059669",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "selected_bg": ("#EFF6FF", "#1E3A8A"),
}

FONTS: dict[str, tuple[Any, ...]] = {
    "header": ("Segoe UI", 16, "bold"),
    "sub_header": ("Segoe UI", 13, "bold"),
    "body": ("Segoe UI", 12),
    "body_bold": ("Segoe UI", 12, "bold"),
    "button": ("Segoe UI", 12, "bold"),
    "small": ("Segoe UI", 11),
    "small_bold": ("Segoe UI", 11, "bold"),
}

if TYPE_CHECKING:
    from ui.main_window import SlipPrinterApp


class ImageZoomDialog(ctk.CTkToplevel):
    """High-resolution scrollable zoom viewer for inspecting annotated screenshots."""

    def __init__(self, parent: tk.Misc, image_path: Path, title: str) -> None:
        super().__init__(parent)
        self.title(f"🔍 Phóng to hình ảnh hướng dẫn — {title}")
        self.geometry("1280x820")
        self.minsize(900, 600)
        self.configure(fg_color="#090D16")

        self._image_path = image_path
        self._zoom_level = 1.0
        self._pil_original = Image.open(image_path).convert("RGB")
        self._tk_image_ref: ImageTk.PhotoImage | None = None

        # Top toolbar
        toolbar = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0, height=52)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        ctk.CTkLabel(
            toolbar,
            text=f"🔍 {title}",
            font=FONTS["sub_header"],
            text_color="#F8FAFC",
        ).pack(side=tk.LEFT, padx=16, pady=10)

        ctk.CTkButton(
            toolbar,
            text="✕ Đóng (Esc)",
            width=110,
            height=32,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            font=FONTS["button"],
            command=self.destroy,
        ).pack(side=tk.RIGHT, padx=14, pady=10)

        ctk.CTkButton(
            toolbar,
            text="➕ Phóng to (125%)",
            width=130,
            height=32,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["body_bold"],
            command=lambda: self._set_zoom(1.25),
        ).pack(side=tk.RIGHT, padx=6, pady=10)

        ctk.CTkButton(
            toolbar,
            text="🔍 Vừa khít (100%)",
            width=130,
            height=32,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            font=FONTS["body_bold"],
            command=lambda: self._set_zoom(1.0),
        ).pack(side=tk.RIGHT, padx=6, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="#090D16")
        self.scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.image_label = tk.Label(self.scroll_frame, text="", bg="#090D16", bd=0, highlightthickness=0)
        self.image_label.pack(padx=8, pady=8)

        self._render_image()
        self.bind("<Escape>", lambda _e: self.destroy())
        self.after(50, self._bring_to_front)

    def _bring_to_front(self) -> None:
        if self.winfo_exists():
            self.lift()
            self.focus_force()

    def _set_zoom(self, zoom: float) -> None:
        self._zoom_level = zoom
        self._render_image()

    def _render_image(self) -> None:
        orig_w, orig_h = self._pil_original.size
        base_w = 1200
        target_w = int(base_w * self._zoom_level)
        target_h = int(orig_h * (target_w / max(orig_w, 1)))
        resized = self._pil_original.resize((target_w, target_h), Image.Resampling.LANCZOS)
        self._tk_image_ref = ImageTk.PhotoImage(resized, master=self)
        self.image_label.configure(image=self._tk_image_ref)


class VisualUserGuideWindow(ctk.CTkToplevel):
    """Comprehensive, non-blocking Visual User Guide window with real annotated screenshots."""

    def __init__(
        self,
        master: "SlipPrinterApp",
        chapters: list[dict[str, Any]] | None = None,
        initial_chapter: int = 0,
    ) -> None:
        super().__init__(master)
        self.master_app = master
        self.chapters: list[dict[str, Any]] = list(chapters or USER_GUIDE_CHAPTERS)
        self.filtered_indices: list[int] = list(range(len(self.chapters)))
        self.current_chapter_index: int = max(0, min(initial_chapter, len(self.chapters) - 1))
        self.is_active: bool = True

        self._assets_dir = get_user_guide_assets_dir()
        self._current_ctk_image: ctk.CTkImage | None = None
        self._zoom_dialog: ImageZoomDialog | None = None
        self._chapter_buttons: dict[int, ctk.CTkButton] = {}

        self.title("📖 Cẩm Nang Hướng Dẫn Sử Dụng Trực Quan — In Phiếu Hiện Vật (KDTVN)")
        self.geometry("1260x830")
        self.minsize(980, 660)
        self.configure(fg_color=COLORS["bg_main"])

        self._build_ui()
        self._bind_shortcuts()
        self.select_chapter(self.current_chapter_index)

        self.protocol("WM_DELETE_WINDOW", self.close_guide)
        self.after(60, self._bring_to_front)

    # ------------------------------------------------------------------
    # Compatibility properties/methods for callers expecting tutorial API
    # ------------------------------------------------------------------
    @property
    def current_step_index(self) -> int:
        return self.current_chapter_index

    @property
    def steps(self) -> list[dict[str, Any]]:
        return self.chapters

    def next_step(self) -> None:
        self.next_chapter()

    def prev_step(self) -> None:
        self.prev_chapter()

    def skip(self) -> None:
        self.close_guide()

    def finish(self) -> None:
        self.close_guide()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # 1. Top Header Banner
        header = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=0, height=68)
        header.pack(fill=tk.X, side=tk.TOP)

        title_col = ctk.CTkFrame(header, fg_color="transparent")
        title_col.pack(side=tk.LEFT, padx=20, pady=10)

        ctk.CTkLabel(
            title_col,
            text="📖 CẨM NANG HƯỚNG DẪN SỬ DỤNG TRỰC QUAN (TRẢI NGHIỆM NGƯỜI DÙNG THẬT)",
            font=FONTS["header"],
            text_color="#F8FAFC",
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_col,
            text="Hình ảnh chụp trực tiếp từ giao diện vận hành thực tế — Đánh số thứ tự thao tác ① ② ③ ④ rõ ràng, không làm khóa màn hình chính",
            font=FONTS["small"],
            text_color="#94A3B8",
            anchor="w",
        ).pack(anchor="w")

        actions_col = ctk.CTkFrame(header, fg_color="transparent")
        actions_col.pack(side=tk.RIGHT, padx=16, pady=12)

        self.btn_open_pdf_manual = ctk.CTkButton(
            actions_col,
            text="📄 Mở / In bản PDF (A4)",
            width=175,
            height=36,
            fg_color="#10B981",
            hover_color="#059669",
            text_color="#FFFFFF",
            font=FONTS["button"],
            command=self.open_pdf_manual,
        )
        self.btn_open_pdf_manual.pack(side=tk.RIGHT, padx=(8, 0))

        self.btn_open_html_manual = ctk.CTkButton(
            actions_col,
            text="🌐 Mở bản Web (HTML) phóng to",
            width=215,
            height=36,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=FONTS["button"],
            command=self.open_html_manual,
        )
        self.btn_open_html_manual.pack(side=tk.RIGHT, padx=4)

        # 2. Bottom Navigation Footer
        footer = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=0, height=56)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        self.btn_prev = ctk.CTkButton(
            footer,
            text="◀ Chuyên đề trước (Phím ⬅)",
            width=190,
            height=36,
            fg_color=COLORS["secondary"],
            hover_color=COLORS["secondary_hover"],
            text_color=COLORS["text_main"],
            font=FONTS["body_bold"],
            command=self.prev_chapter,
        )
        self.btn_prev.pack(side=tk.LEFT, padx=18, pady=10)

        self.progress_label = ctk.CTkLabel(
            footer,
            text="Đang xem: Chuyên đề 1 / 6",
            font=FONTS["sub_header"],
            text_color=COLORS["primary"],
        )
        self.progress_label.pack(side=tk.LEFT, expand=True)

        self.btn_close = ctk.CTkButton(
            footer,
            text="✕ Đóng hướng dẫn (Esc)",
            width=165,
            height=36,
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            text_color="#FFFFFF",
            font=FONTS["button"],
            command=self.close_guide,
        )
        self.btn_close.pack(side=tk.RIGHT, padx=(8, 18), pady=10)

        self.btn_next = ctk.CTkButton(
            footer,
            text="Chuyên đề tiếp theo (Phím ➡) ▶",
            width=220,
            height=36,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            text_color="#FFFFFF",
            font=FONTS["button"],
            command=self.next_chapter,
        )
        self.btn_next.pack(side=tk.RIGHT, padx=8, pady=10)

        # 3. Main Body Split (Left Chapter Sidebar + Right Scrollable Visual Content)
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        # Left Sidebar
        self.sidebar_frame = ctk.CTkFrame(
            body,
            width=285,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        self.sidebar_frame.pack_propagate(False)

        ctk.CTkLabel(
            self.sidebar_frame,
            text="DANH MỤC 6 CHUYÊN ĐỀ",
            font=FONTS["sub_header"],
            text_color=COLORS["text_main"],
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(14, 6))

        self.search_var = tk.StringVar()
        self.search_entry = ctk.CTkEntry(
            self.sidebar_frame,
            textvariable=self.search_var,
            placeholder_text="🔍 Tìm nhanh (VD: Tách CAV, QR)...",
            height=34,
            font=FONTS["body"],
        )
        self.search_entry.pack(fill=tk.X, padx=12, pady=(0, 10))
        self.search_entry.bind("<KeyRelease>", lambda _e: self._on_search_changed())

        self.nav_list_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._rebuild_sidebar_buttons()

        # Helpful note at bottom of sidebar
        tip_card = ctk.CTkFrame(
            self.sidebar_frame,
            fg_color=COLORS["selected_bg"],
            corner_radius=8,
            border_width=1,
            border_color=COLORS["primary"],
        )
        tip_card.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)
        ctk.CTkLabel(
            tip_card,
            text=(
                "💡 Cửa sổ hướng dẫn này hoàn toàn độc lập.\n"
                "Bạn có thể vừa mở hướng dẫn ở một bên, vừa bấm thao tác trực tiếp trên phần mềm chính!"
            ),
            font=FONTS["small"],
            text_color=COLORS["text_main"],
            justify=tk.LEFT,
            wraplength=245,
        ).pack(padx=10, pady=8)

        # Right Scrollable Area
        self.content_scroll = ctk.CTkScrollableFrame(
            body,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=COLORS["border"],
        )
        self.content_scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Dynamic content containers inside content_scroll
        self.chapter_banner = ctk.CTkFrame(
            self.content_scroll,
            fg_color="#0F172A",
            corner_radius=10,
        )
        self.chapter_banner.pack(fill=tk.X, padx=16, pady=(14, 10))

        banner_top = ctk.CTkFrame(self.chapter_banner, fg_color="transparent")
        banner_top.pack(fill=tk.X, padx=16, pady=(12, 4))

        self.chapter_badge_lbl = ctk.CTkLabel(
            banner_top,
            text="CHUYÊN ĐỀ 1 / 6",
            font=FONTS["small_bold"],
            text_color="#34D399",
            fg_color="#064E3B",
            corner_radius=6,
            padx=10,
            pady=2,
        )
        self.chapter_badge_lbl.pack(side=tk.LEFT)

        self.btn_jump_tab = ctk.CTkButton(
            banner_top,
            text="🚀 Mở màn hình này trên phần mềm để thực hành ngay",
            height=30,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#FFFFFF",
            font=FONTS["small_bold"],
            command=self.jump_to_target_tab,
        )
        self.btn_jump_tab.pack(side=tk.RIGHT)

        self.chapter_title_lbl = ctk.CTkLabel(
            self.chapter_banner,
            text="",
            font=("Segoe UI", 18, "bold"),
            text_color="#FFFFFF",
            anchor="w",
            justify=tk.LEFT,
            wraplength=840,
        )
        self.chapter_title_lbl.pack(fill=tk.X, padx=16, pady=(2, 4))

        self.chapter_summary_lbl = ctk.CTkLabel(
            self.chapter_banner,
            text="",
            font=FONTS["body"],
            text_color="#CBD5E1",
            anchor="w",
            justify=tk.LEFT,
            wraplength=840,
        )
        self.chapter_summary_lbl.pack(fill=tk.X, padx=16, pady=(0, 12))

        # Screenshot Card
        self.screenshot_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color="#090D16",
            corner_radius=10,
            border_width=2,
            border_color="#334155",
        )
        self.screenshot_card.pack(fill=tk.X, padx=16, pady=(4, 12))

        screenshot_header = ctk.CTkFrame(self.screenshot_card, fg_color="#0F172A", corner_radius=0, height=36)
        screenshot_header.pack(fill=tk.X, padx=2, pady=(2, 0))

        ctk.CTkLabel(
            screenshot_header,
            text="📸 HÌNH ẢNH GIAO DIỆN THỰC TẾ (ĐÃ ĐÁNH SỐ THỨ TỰ THAO TÁC ① ② ③ ④)",
            font=FONTS["small_bold"],
            text_color="#38BDF8",
        ).pack(side=tk.LEFT, padx=12, pady=6)

        self.btn_zoom_image = ctk.CTkButton(
            screenshot_header,
            text="🔍 Phóng to ảnh chụp màn hình (Xem rõ từng chi tiết)",
            height=26,
            fg_color=COLORS["primary"],
            hover_color=COLORS["primary_hover"],
            font=FONTS["small_bold"],
            command=self.open_zoom_dialog,
        )
        self.btn_zoom_image.pack(side=tk.RIGHT, padx=10, pady=5)

        self.screenshot_label = tk.Label(
            self.screenshot_card,
            text="",
            bg="#090D16",
            fg="#F87171",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
        )
        self.screenshot_label.pack(padx=10, pady=10)
        self.screenshot_label.bind("<Button-1>", lambda _e: self.open_zoom_dialog())

        # Steps Container
        self.steps_section_title = ctk.CTkLabel(
            self.content_scroll,
            text="📋 CHI TIẾT CÁC BƯỚC THỰC HIỆN (ĐỐI CHIẾU THEO SỐ TRÊN ẢNH):",
            font=FONTS["sub_header"],
            text_color=COLORS["text_main"],
            anchor="w",
        )
        self.steps_section_title.pack(fill=tk.X, padx=16, pady=(4, 6))

        self.steps_container = ctk.CTkFrame(self.content_scroll, fg_color="transparent")
        self.steps_container.pack(fill=tk.X, padx=16, pady=(0, 10))

        # Tips Container
        self.tips_card = ctk.CTkFrame(
            self.content_scroll,
            fg_color="#FFFBEB",
            corner_radius=10,
            border_width=1,
            border_color="#F59E0B",
        )
        self.tips_card.pack(fill=tk.X, padx=16, pady=(4, 18))

        self.tips_title_lbl = ctk.CTkLabel(
            self.tips_card,
            text="💡 LƯU Ý QUAN TRỌNG TẠI XƯỞNG:",
            font=FONTS["body_bold"],
            text_color="#92400E",
            anchor="w",
        )
        self.tips_title_lbl.pack(fill=tk.X, padx=14, pady=(10, 4))

        self.tips_body_lbl = ctk.CTkLabel(
            self.tips_card,
            text="",
            font=FONTS["body"],
            text_color="#78350F",
            anchor="w",
            justify=tk.LEFT,
            wraplength=820,
        )
        self.tips_body_lbl.pack(fill=tk.X, padx=14, pady=(0, 12))

    def _rebuild_sidebar_buttons(self) -> None:
        for child in self.nav_list_frame.winfo_children():
            child.destroy()
        self._chapter_buttons.clear()

        for idx in self.filtered_indices:
            ch = self.chapters[idx]
            is_selected = idx == self.current_chapter_index
            btn = ctk.CTkButton(
                self.nav_list_frame,
                text=ch["short_title"],
                anchor="w",
                height=40,
                corner_radius=8,
                fg_color=COLORS["primary"] if is_selected else "transparent",
                hover_color=COLORS["primary_hover"] if is_selected else COLORS["secondary"],
                text_color="#FFFFFF" if is_selected else COLORS["text_main"],
                font=FONTS["body_bold"] if is_selected else FONTS["body"],
                command=lambda target_idx=idx: self.select_chapter(target_idx),
            )
            btn.pack(fill=tk.X, padx=4, pady=3)
            self._chapter_buttons[idx] = btn

    def _on_search_changed(self) -> None:
        query = self.search_var.get().strip().lower()
        if not query:
            self.filtered_indices = list(range(len(self.chapters)))
        else:
            matched: list[int] = []
            for idx, ch in enumerate(self.chapters):
                searchable = " ".join(
                    [
                        ch.get("short_title", ""),
                        ch.get("title", ""),
                        ch.get("summary", ""),
                        " ".join(s.get("title", "") + " " + s.get("detail", "") for s in ch.get("steps", [])),
                        " ".join(ch.get("tips", [])),
                    ]
                ).lower()
                if query in searchable:
                    matched.append(idx)
            self.filtered_indices = matched or list(range(len(self.chapters)))

        self._rebuild_sidebar_buttons()
        if self.current_chapter_index not in self.filtered_indices and self.filtered_indices:
            self.select_chapter(self.filtered_indices[0])

    # ------------------------------------------------------------------
    # Chapter Selection & Rendering
    # ------------------------------------------------------------------
    def select_chapter(self, index: int) -> None:
        if not self.chapters:
            return
        index = max(0, min(index, len(self.chapters) - 1))
        self.current_chapter_index = index
        ch = self.chapters[index]

        # Highlight sidebar button
        for idx, btn in self._chapter_buttons.items():
            is_sel = idx == index
            btn.configure(
                fg_color=COLORS["primary"] if is_sel else "transparent",
                hover_color=COLORS["primary_hover"] if is_sel else COLORS["secondary"],
                text_color="#FFFFFF" if is_sel else COLORS["text_main"],
                font=FONTS["body_bold"] if is_sel else FONTS["body"],
            )

        total = len(self.chapters)
        self.chapter_badge_lbl.configure(text=f"CHUYÊN ĐỀ {index + 1} / {total}")
        self.chapter_title_lbl.configure(text=ch["title"])
        self.chapter_summary_lbl.configure(text=ch["summary"])
        self.progress_label.configure(
            text=f"Đang xem: Chuyên đề {index + 1} / {total} — {ch['short_title']}"
        )

        # Update prev/next buttons
        self.btn_prev.configure(state="normal" if index > 0 else "disabled")
        if index < total - 1:
            self.btn_next.configure(text="Chuyên đề tiếp theo (Phím ➡) ▶", state="normal")
        else:
            self.btn_next.configure(text="🎉 Đã xem hết chuyên đề", state="disabled")

        # Load annotated real screenshot using master-bound PhotoImage
        img_path = self._assets_dir / ch["image_filename"]
        if img_path.is_file():
            pil_img = Image.open(img_path).convert("RGB")
            orig_w, orig_h = pil_img.size
            disp_w = 880
            disp_h = int(orig_h * (disp_w / max(orig_w, 1)))
            resized = pil_img.resize((disp_w, disp_h), Image.Resampling.LANCZOS)
            self._current_ctk_image = ImageTk.PhotoImage(resized, master=self)
            self.screenshot_label.configure(image=self._current_ctk_image, text="")
        else:
            self.screenshot_label.configure(
                image="",
                text=f"(Không tìm thấy ảnh minh họa: {img_path.name})",
            )

        # Populate step cards
        for child in self.steps_container.winfo_children():
            child.destroy()

        for step in ch.get("steps", []):
            card = ctk.CTkFrame(
                self.steps_container,
                fg_color=COLORS["bg_main"],
                corner_radius=8,
                border_width=1,
                border_color=COLORS["border"],
            )
            card.pack(fill=tk.X, pady=4)

            badge_color = step.get("color", COLORS["primary"])
            num_badge = ctk.CTkLabel(
                card,
                text=str(step["num"]),
                width=34,
                height=34,
                fg_color=badge_color,
                text_color="#FFFFFF",
                corner_radius=17,
                font=FONTS["sub_header"],
            )
            num_badge.pack(side=tk.LEFT, padx=(12, 10), pady=12, anchor="n")

            text_col = ctk.CTkFrame(card, fg_color="transparent")
            text_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12), pady=10)

            ctk.CTkLabel(
                text_col,
                text=f"Bước ({step['num']}): {step['title']}",
                font=FONTS["body_bold"],
                text_color=COLORS["text_main"],
                anchor="w",
                justify=tk.LEFT,
                wraplength=780,
            ).pack(fill=tk.X, anchor="w")

            ctk.CTkLabel(
                text_col,
                text=step["detail"],
                font=FONTS["body"],
                text_color=COLORS["text_sub"],
                anchor="w",
                justify=tk.LEFT,
                wraplength=780,
            ).pack(fill=tk.X, anchor="w", pady=(2, 0))

        # Populate tips
        tips_lines = "\n".join(f"• {tip}" for tip in ch.get("tips", []))
        self.tips_body_lbl.configure(text=tips_lines)

        # Scroll back to top of chapter
        try:
            self.content_scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def next_chapter(self) -> None:
        if self.current_chapter_index < len(self.chapters) - 1:
            self.select_chapter(self.current_chapter_index + 1)

    def prev_chapter(self) -> None:
        if self.current_chapter_index > 0:
            self.select_chapter(self.current_chapter_index - 1)

    def jump_to_target_tab(self) -> None:
        """Switch the main application window to the current chapter's operational tab."""
        ch = self.chapters[self.current_chapter_index]
        tab_idx = int(ch.get("target_tab_index", 0))
        try:
            if hasattr(self.master_app, "notebook") and self.master_app.notebook.winfo_exists():
                self.master_app.notebook.select(tab_idx)
                self.master_app.lift()
                self.master_app.focus_force()
        except Exception as exc:
            log_error_event(
                "user_guide",
                "jump_to_target_tab_failed",
                f"Failed to switch notebook tab {tab_idx}: {exc}",
                exc=exc,
                dedup_window_seconds=2.0,
            )

    def open_zoom_dialog(self) -> None:
        """Open the high-resolution zoomable screenshot modal for the active chapter."""
        ch = self.chapters[self.current_chapter_index]
        img_path = self._assets_dir / ch["image_filename"]
        if not img_path.is_file():
            return
        if self._zoom_dialog is not None and self._zoom_dialog.winfo_exists():
            self._zoom_dialog.destroy()
        self._zoom_dialog = ImageZoomDialog(self, img_path, ch["title"])

    def open_html_manual(self) -> bool:
        """Open the standalone full-screen HTML manual in the user's web browser."""
        html_path = self._assets_dir / "huong_dan_su_dung.html"
        if not html_path.is_file():
            return False
        try:
            webbrowser.open(html_path.resolve().as_uri())
            return True
        except Exception as exc:
            log_error_event(
                "user_guide",
                "open_html_manual_failed",
                f"Failed to open HTML manual: {exc}",
                exc=exc,
            )
            return False

    def open_pdf_manual(self) -> bool:
        """Open the printable A4 PDF manual using the OS default PDF viewer."""
        pdf_path = self._assets_dir / "Huong_Dan_Su_Dung_InPhieuHienVat.pdf"
        if not pdf_path.is_file():
            return False
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(pdf_path.resolve()))
            else:
                webbrowser.open(pdf_path.resolve().as_uri())
            return True
        except Exception as exc:
            log_error_event(
                "user_guide",
                "open_pdf_manual_failed",
                f"Failed to open PDF manual: {exc}",
                exc=exc,
            )
            return False

    def _bind_shortcuts(self) -> None:
        self.bind("<Escape>", lambda _e: self.close_guide())
        self.bind("<Right>", self._on_key_right)
        self.bind("<Left>", self._on_key_left)

    def _on_key_right(self, event: tk.Event[Any]) -> None:
        if event.widget == self.search_entry._entry:
            return
        self.next_chapter()

    def _on_key_left(self, event: tk.Event[Any]) -> None:
        if event.widget == self.search_entry._entry:
            return
        self.prev_chapter()

    def _bring_to_front(self) -> None:
        if self.winfo_exists():
            self.lift()
            self.focus_force()

    def close_guide(self) -> None:
        self.is_active = False
        try:
            if hasattr(self.master_app, "controller") and hasattr(
                self.master_app.controller, "mark_tutorial_completed"
            ):
                self.master_app.controller.mark_tutorial_completed()
        except Exception:
            pass
        if self._zoom_dialog is not None and self._zoom_dialog.winfo_exists():
            try:
                self._zoom_dialog.destroy()
            except Exception:
                pass
        if self.winfo_exists():
            self.destroy()
