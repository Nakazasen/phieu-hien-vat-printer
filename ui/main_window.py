from __future__ import annotations

import json
import os
import queue
import time
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

import customtkinter as ctk

import sv_ttk

from core.po_registry import PORegistry
from core.runtime_paths import prepare_runtime_paths
from core.slip_printer_engine import (
    SlipRecord,
    ensure_layout_config_file,
    load_layout_config,
)
from ui.app_controller import APP_TITLE, AppController
from ui.app_state import AppState
from ui.components.data_tab import DataTabPanel
from ui.components.history_tab import HistoryTabPanel
from ui.components.layout_tab import LayoutTabPanel
from ui.components.sidebar import SidebarPanel

ctk.set_default_color_theme("green")


class SlipPrinterApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        target_w = min(1400, max(1000, screen_w - 60))
        target_h = min(900, max(700, screen_h - 80))
        pos_x = max(0, (screen_w - target_w) // 2)
        pos_y = max(0, (screen_h - target_h) // 2)
        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(1000, 700)

        # 1. Khởi tạo State & Controller
        self.app_state = AppState(self)
        self.controller = AppController(self.app_state)
        self.controller.set_view(self)

        # 2. Tải và áp dụng cấu hình giao diện người dùng đã lưu
        self._init_theme_mode()

        icon_path = self.app_state.paths.bundle_dir / "app_icon.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:  # noqa: BLE001
                pass

        self.sidebar_width = 360

        # 2. Xây dựng UI
        self._build_layout()

        # 3. Setup sau khi render
        self.protocol("WM_DELETE_WINDOW", self.controller.on_close)
        self._drain_job = self.after(150, self._drain_event_queue)
        self._update_job = self.after(1200, lambda: self.controller.check_for_update(automatic=True))
        self._tutorial_prompt_job = self.after(600, self._check_first_launch_tutorial)

    def destroy(self) -> None:
        if getattr(self, "_is_destroyed", False):
            return
        self._is_destroyed = True
        try:
            if hasattr(self, "_drain_job"):
                self.after_cancel(self._drain_job)
            if hasattr(self, "_update_job"):
                self.after_cancel(self._update_job)
            if hasattr(self, "_tutorial_prompt_job") and self._tutorial_prompt_job:
                self.after_cancel(self._tutorial_prompt_job)
            if hasattr(self, "_tutorial_overlay") and self._tutorial_overlay is not None:
                try:
                    self._tutorial_overlay.destroy()
                except Exception:
                    pass
                self._tutorial_overlay = None
            if hasattr(self, "app_state") and hasattr(self.app_state, "po_registry"):
                self.app_state.po_registry.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            super().destroy()
        except Exception:
            pass


    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.splitter = ttk.Panedwindow(self, orient="horizontal")
        self.splitter.grid(row=0, column=0, sticky="nsew", padx=16, pady=12)

        sidebar_host = ctk.CTkFrame(self.splitter, corner_radius=14, fg_color=("gray94", "gray14"))
        sidebar_host.grid_rowconfigure(0, weight=1)
        sidebar_host.grid_columnconfigure(0, weight=1)
        self.sidebar = SidebarPanel(sidebar_host, self.controller, corner_radius=14, fg_color=("gray94", "gray14"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")

        content = ctk.CTkFrame(self.splitter, corner_radius=14)

        self.splitter.add(sidebar_host, weight=0)
        self.splitter.add(content, weight=1)

        self._build_content(content)
        self.after(120, self._apply_splitter_width)

    def _build_content(self, parent: ctk.CTkFrame) -> None:
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(10, 4))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, textvariable=self.app_state.summary_var, font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkLabel(header, textvariable=self.app_state.status_var, font=ctk.CTkFont(size=12), text_color=("gray40", "gray60")).grid(
            row=1, column=0, sticky="w", pady=(3, 0)
        )

        preview_controls = ctk.CTkFrame(header, fg_color="transparent")
        preview_controls.grid(row=0, column=1, rowspan=2, sticky="e")

        ctk.CTkLabel(preview_controls, text="Giao diện:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, padx=(0, 4))
        self.theme_menu = ctk.CTkOptionMenu(
            preview_controls,
            values=["Tối 🌙", "Sáng ☀️", "Hệ thống 🖥️"],
            width=115,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self._on_theme_changed,
        )
        self.theme_menu.grid(row=0, column=1, padx=(0, 10))
        self.theme_menu.set(self._get_display_theme_label(self._current_theme_mode))

        ctk.CTkLabel(preview_controls, text="Số dòng:", font=ctk.CTkFont(size=12)).grid(row=0, column=2, padx=(0, 4))
        ctk.CTkComboBox(
            preview_controls,
            values=["20", "50", "100", "200"],
            variable=self.app_state.preview_limit_var,
            width=75,
            height=28,
            command=lambda _value: self.set_records(self.app_state.records, self.app_state.selected_record_index),
        ).grid(row=0, column=3)
        self.tutorial_btn = ctk.CTkButton(
            preview_controls,
            text="💡 Hướng dẫn",
            width=120,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#F59E0B", "#D97706"),
            hover_color=("#D97706", "#B45309"),
            text_color=("#FFFFFF", "#FFFFFF"),
            command=self.start_tutorial,
        )
        self.tutorial_btn.grid(row=1, column=0, columnspan=2, sticky="e", padx=(0, 8), pady=(4, 0))

        self.update_btn = ctk.CTkButton(
            preview_controls,
            text="Kiểm tra bản cập nhật",
            width=150,
            height=28,
            font=ctk.CTkFont(size=12),
            command=self.controller.check_for_update,
        )
        self.update_btn.grid(row=1, column=2, columnspan=2, sticky="e", pady=(4, 0))

        # Notebook
        self.notebook = ttk.Notebook(parent)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(2, 6))

        # Tab Data
        self.data_tab = DataTabPanel(self.notebook, self.controller, corner_radius=0)
        self.notebook.add(self.data_tab, text="Dữ liệu và xem trước")
        self.data_tab.set_records(select_index=None)

        # Tab Layout
        self.layout_tab = LayoutTabPanel(self.notebook, self.controller, corner_radius=0)
        self.notebook.add(self.layout_tab, text="Chỉnh sửa Layout PDF")
        self.layout_tab.refresh_tree()

        # Tab History
        self.history_tab = HistoryTabPanel(self.notebook, self.controller, corner_radius=0)
        self.notebook.add(self.history_tab, text="📊 Lịch sử Đăng ký EDI")
        self.history_tab.refresh_history()

        # Tự động nạp lại khi chuyển tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_notebook_tab_changed)

        # Footer
        footer = ctk.CTkFrame(parent, corner_radius=12)
        footer.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 6))
        footer.grid_columnconfigure(0, weight=1)

        self.progress = ctk.CTkProgressBar(footer, height=10)
        self.progress.grid(row=0, column=0, sticky="ew", padx=14, pady=(6, 3))
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(footer, height=45, font=ctk.CTkFont(size=11))
        self.log_box.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
        self.log_box.insert("1.0", "Ứng dụng đã khởi động.\n")
        self.log_box.configure(state="disabled")

    def _apply_splitter_width(self) -> None:
        try:
            self.splitter.sashpos(0, self.sidebar_width)
        except Exception:  # noqa: BLE001, S110
            pass

    # --- MAIN VIEW PROTOCOL (AppController -> View) ---

    def append_log(self, message: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message.rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def set_records(self, records: list[SlipRecord], select_index: int | None = None, source: str | None = None) -> None:
        self.app_state.records = list(records)
        self.app_state.selected_record_index = 0 if not self.app_state.records else min(select_index or 0, len(self.app_state.records) - 1)
        if source:
            self.append_log(source)
        self.data_tab.set_records(select_index=self.app_state.selected_record_index if self.app_state.records else None)

    def refresh_preview_image(self) -> None:
        # AppController relies on state.records and layout configuration
        # but the generation of the image is handled by AppController and set to AppState.
        # However, generate_preview_image is in slip_printer_engine, and requires record.
        # In the original code, this logic was complex. Let's rebuild it briefly here.
        if not self.app_state.records:
            self.app_state.preview_source_image = None
            self.data_tab.preview_image_label.configure(text="Chưa có dữ liệu để xem trước", image=None)
            self.data_tab.set_qr_payload_text("")
            return

        template_path = Path(self.app_state.template_var.get())
        if not template_path.is_file():
            self.app_state.preview_source_image = None
            self.data_tab.preview_image_label.configure(text="Chưa chọn PDF mẫu hợp lệ", image=None)
            return

        record_index = min(self.app_state.selected_record_index, len(self.app_state.records) - 1)
        record = self.app_state.records[record_index]
        from core.slip_printer_engine import generate_preview_image
        try:
            self.app_state.preview_source_image = generate_preview_image(
                record,
                template_path,
                self.app_state.layout_config,
                zoom=1.45,
            )
        except Exception as exc:  # noqa: BLE001
            self.app_state.preview_source_image = None
            self.data_tab.preview_image_label.configure(text=f"Lỗi render preview:\n{exc}", image=None)
            self.append_log(f"Lỗi preview: {exc}")
            return

        self.data_tab.set_qr_payload_text(record.qr_payload)
        self.update_preview_display()

    def update_preview_display(self) -> None:
        self.data_tab.update_preview_display()

    def refresh_layout_tree(self, select_id: str | None = None) -> None:
        self.layout_tab.refresh_tree(select_id)

    def refresh_history(self) -> None:
        self.history_tab.refresh_history()

    def _on_notebook_tab_changed(self, event) -> None:
        try:
            selected_tab = event.widget.tab(event.widget.select(), "text")
            if "Lịch sử" in selected_tab:
                self.history_tab.refresh_history()
        except Exception:  # noqa: BLE001
            pass

    def on_generation_start(self) -> None:
        self.sidebar.set_generate_button_state("disabled")
        self.progress.set(0)
        self.app_state.status_var.set("Đang tạo PDF...")

    def auto_commit_form(self) -> bool:
        return self.data_tab.auto_commit_form()

    def _drain_event_queue(self) -> None:
        while True:
            try:
                event_type, payload = self.app_state.event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "progress":
                current, total, message = payload
                ratio = 0 if total <= 0 else min(max(current / total, 0), 1)
                self.progress.set(ratio)
                self.app_state.status_var.set(message)
                self.append_log(message)
            elif event_type == "success":
                output_path, record_count = payload
                a4_page_count = (record_count + 3) // 4
                self.app_state.generated_output_path = Path(output_path)
                self.progress.set(1)
                self.app_state.status_var.set(f"Hoàn tất. Đã tạo {record_count} tem trên {a4_page_count} trang A4.")
                self.app_state.output_name_var.set(self.app_state._default_output_name())
                self.append_log(f"Hoàn tất: {output_path}")
                self.refresh_history()
                messagebox.showinfo(
                    APP_TITLE,
                    f"🎉 TẠO FILE PDF THÀNH CÔNG!\n\n"
                    f"- Số lượng tem: {record_count} tem\n"
                    f"- Quy cách in: {a4_page_count} trang A4\n"
                    f"- Vị trí lưu: {output_path}\n\n"
                    "👉 Bạn có thể nhấn nút 'Mở PDF vừa tạo' ở thanh bên trái để xem hoặc in trực tiếp.",
                )
                self.sidebar.set_generate_button_state("normal")
            elif event_type == "error":
                self.progress.set(0)
                self.app_state.status_var.set("Tạo PDF thất bại")
                self.append_log(f"Lỗi: {payload}")
                messagebox.showerror(
                    APP_TITLE,
                    f"❌ Quá trình tạo file PDF thất bại:\n{payload}\n\n"
                    "👉 Hướng dẫn khắc phục:\n"
                    "1. Đóng file PDF đích nếu đang mở trong Adobe Acrobat / trình duyệt.\n"
                    "2. Kiểm tra quyền ghi dữ liệu vào thư mục đầu ra.\n"
                    "3. Đảm bảo file PDF mẫu hợp lệ và không bị hỏng.",
                )
                self.sidebar.set_generate_button_state("normal")
            elif event_type == "update_available":
                candidate, app_root, automatic = payload
                self.app_state.update_check_running = False
                if candidate is None:
                    self.app_state.status_var.set("Bạn đang dùng phiên bản mới nhất.")
                    if not automatic:
                        messagebox.showinfo(
                            APP_TITLE,
                            "Bạn đang sử dụng phiên bản mới nhất của phần mềm.\n\nHiện tại không có bản cập nhật nào mới hơn.",
                        )
                elif messagebox.askyesno(
                    "Phát hiện bản cập nhật mới",
                    f"Đã có phiên bản mới ({candidate.version}) sẵn sàng cài đặt!\n\n"
                    f"📋 Nội dung cập nhật:\n{candidate.notes or 'Không có ghi chú phát hành.'}\n\n"
                    "👉 Bạn có muốn tự động tải về và nâng cấp ứng dụng ngay bây giờ không?",
                ):
                    self.app_state.update_check_running = True
                    self.controller.start_update_install(candidate, app_root)
            elif event_type == "update_success":
                state, app_root = payload
                self.app_state.update_check_running = False
                self.app_state.status_var.set(f"Đã kích hoạt bản {state['version']}. Đang khởi động lại...")
                from updater.app_updates import launch_activated_update
                try:
                    launch_activated_update(app_root, current_pid=os.getpid())
                    self.controller.on_close()
                    return
                except Exception as exc:  # noqa: BLE001
                    messagebox.showerror(
                        APP_TITLE,
                        f"Đã cài đặt bản cập nhật thành công nhưng phần mềm chưa thể tự động khởi động lại:\n{exc}\n\n"
                        "👉 Hướng dẫn: Vui lòng đóng ứng dụng và mở lại phần mềm thủ công.",
                    )
            elif event_type == "update_error":
                detail, automatic = payload
                self.app_state.update_check_running = False
                self.app_state.status_var.set("Kiểm tra/cài cập nhật không thành công.")
                self.append_log(f"Lỗi cập nhật: {detail}")
                if not automatic:
                    messagebox.showerror(
                        APP_TITLE,
                        f"Quá trình tải hoặc cài đặt bản cập nhật thất bại:\n{detail}\n\n"
                        "👉 Hướng dẫn: Vui lòng kiểm tra lại kết nối mạng nội bộ hoặc liên hệ kỹ thuật viên hỗ trợ.",
                    )

        self.after(150, self._drain_event_queue)

    def _init_theme_mode(self) -> None:
        saved_mode = self._load_theme_setting()
        self._current_theme_mode = saved_mode
        self._apply_theme_mode(saved_mode, persist=False)

    def _get_display_theme_label(self, mode: str) -> str:
        mapping = {
            "Dark": "Tối 🌙",
            "Light": "Sáng ☀️",
            "System": "Hệ thống 🖥️",
        }
        return mapping.get(mode, "Hệ thống 🖥️")

    def _on_theme_changed(self, choice: str) -> None:
        mapping = {
            "Tối 🌙": "Dark",
            "Sáng ☀️": "Light",
            "Hệ thống 🖥️": "System",
            "Dark": "Dark",
            "Light": "Light",
            "System": "System",
        }
        mode = mapping.get(choice, "System")
        self._current_theme_mode = mode
        self._apply_theme_mode(mode, persist=True)

    def _apply_theme_mode(self, mode: str, persist: bool = True) -> None:
        ctk.set_appearance_mode(mode)
        try:
            active_mode = ctk.get_appearance_mode().lower()
            if active_mode == "light":
                sv_ttk.use_light_theme()
            else:
                sv_ttk.use_dark_theme()
        except Exception:  # noqa: BLE001
            pass
        if persist:
            self._save_theme_setting(mode)

    # --- USER SETTINGS PERSISTENCE (THEME & TUTORIAL) ---

    def _get_settings_path(self) -> Path:
        """Return the resolved Path to user_settings.json."""
        if hasattr(self, "app_state") and hasattr(self.app_state, "paths"):
            return self.app_state.paths.data_dir / "user_settings.json"
        from core.runtime_paths import prepare_runtime_paths
        return prepare_runtime_paths().data_dir / "user_settings.json"

    def _load_user_settings(self) -> dict[str, Any]:
        """Load full user settings dictionary with robust default fallbacks."""
        defaults: dict[str, Any] = {
            "appearance_mode": "System",
            "has_seen_tutorial": False,
            "auto_suggest_tutorial": True,
        }
        try:
            settings_path = self._get_settings_path()
            if settings_path.is_file():
                raw = settings_path.read_text(encoding="utf-8-sig")
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    defaults.update(loaded)
        except Exception:  # noqa: BLE001
            pass
        return defaults

    def _save_user_settings(self, updates: dict[str, Any]) -> None:
        """Atomically merge and persist updates into user_settings.json."""
        try:
            settings_path = self._get_settings_path()
            current = self._load_user_settings()
            current.update(updates)
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps(current, indent=2, ensure_ascii=False) + "\n"
            temp_path = settings_path.with_suffix(".json.tmp")
            temp_path.write_text(payload, encoding="utf-8")
            try:
                os.replace(temp_path, settings_path)
            except OSError:
                settings_path.write_text(payload, encoding="utf-8")
                temp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    def _load_theme_setting(self) -> str:
        """Load appearance theme mode ('Dark', 'Light', 'System')."""
        settings = self._load_user_settings()
        mode = str(settings.get("appearance_mode", "System"))
        return mode if mode in ("Dark", "Light", "System") else "System"

    def _save_theme_setting(self, mode: str) -> None:
        """Save appearance theme mode to user_settings.json."""
        self._save_user_settings({"appearance_mode": mode})

    def _load_tutorial_seen_setting(self) -> bool:
        """Load tutorial completion flag from user_settings.json."""
        settings = self._load_user_settings()
        return bool(settings.get("has_seen_tutorial", False))

    def _save_tutorial_seen_setting(self, seen: bool = True) -> None:
        """Save tutorial completion flag to user_settings.json."""
        self._save_user_settings({"has_seen_tutorial": bool(seen)})

    def _should_prompt_first_launch_tutorial(self) -> bool:
        """Check whether the first-launch tutorial prompt should be presented."""
        settings = self._load_user_settings()
        has_seen = bool(settings.get("has_seen_tutorial", False))
        auto_suggest = bool(settings.get("auto_suggest_tutorial", True))
        return (not has_seen) and auto_suggest

    def _check_first_launch_tutorial(self) -> None:
        """Timer callback to display the first-launch onboarding prompt dialog."""
        if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("INPHIEUHIENVAT_DISABLE_TUTORIAL_PROMPT"):
            return
        if not self._should_prompt_first_launch_tutorial():
            return
        try:
            prompt_msg = (
                "👋 Chào mừng bạn đến với Phần mềm In Phiếu Hiện Vật!\n\n"
                "👉 Bạn có muốn xem hướng dẫn tương tác nhanh (4 bước thao tác: Import Excel, Quét QR, Tạo Auto PO, Xuất PDF) không?"
            )
            if messagebox.askyesno(APP_TITLE, prompt_msg, parent=self):
                self.start_tutorial()
        except Exception:  # noqa: BLE001
            pass

    def _check_first_run_tutorial(self) -> None:
        """Alias for _check_first_launch_tutorial."""
        self._check_first_launch_tutorial()

    # --- TUTORIAL ENGINE INTEGRATION ---

    def get_tutorial_steps(self=None):
        """Constructs and returns the 4-step tutorial script."""
        from ui.components.tutorial_script import build_tutorial_steps
        return build_tutorial_steps(self)

    def start_tutorial(self):
        """Launch the interactive tutorial overlay over the main window."""
        existing = getattr(self, "_tutorial_overlay", None)
        if existing is not None and getattr(existing, "is_active", False):
            existing.start(0)
            return existing

        from ui.components.tutorial_overlay import InteractiveTutorialOverlay
        from ui.components.tutorial_script import build_tutorial_steps

        def _on_finish():
            self._save_tutorial_seen_setting(True)
            self.append_log("Đã hoàn tất xem hướng dẫn sử dụng.")

        overlay = InteractiveTutorialOverlay(
            self,
            notebook=getattr(self, "notebook", None),
            on_finish=_on_finish,
        )
        steps = build_tutorial_steps(self)
        overlay.register_steps(steps)
        overlay.start(0)
        self._tutorial_overlay = overlay
        return overlay



def run_health_check() -> None:
    """Validate bundled assets and writable user state without starting the GUI."""
    paths = prepare_runtime_paths()
    ensure_layout_config_file(paths.layout_path)
    load_layout_config(paths.layout_path)
    registry = PORegistry(paths.registry_path)
    registry.close()
    print(f"Kiểm tra hệ thống thành công: {paths.template_path}")


def _wait_for_process_exit(pid: int, timeout_seconds: float = 120.0) -> None:
    if pid <= 0:
        raise ValueError("PID cần chờ phải lớn hơn 0.")
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        except PermissionError:
            return
        time.sleep(0.2)
    raise TimeoutError(f"Tiến trình {pid} chưa thoát sau {timeout_seconds:.0f} giây.")
