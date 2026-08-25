from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from ui.components.qr_scan_dialog import QRScanPanel

if TYPE_CHECKING:
    from ui.app_controller import AppController


class QRScanTabPanel(ctk.CTkFrame):
    """Notebook tab hosting the QR scan workflow (Phân tách 分割 · Hoàn kho 戻入 · In lại 再発行).

    Consolidates the former sidebar '⚡ Quét QR' button and the data-tab header
    '📷 Quét QR' button into a single dedicated tab placed next to the EDI history tab.
    """

    def __init__(self, master, controller: AppController, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.app_state = controller.app_state

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scan_panel = QRScanPanel(self, controller, embedded=True)
        self.scan_panel.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def focus_scan_entry(self) -> None:
        """Focus the QR input field (called when the tab becomes active)."""
        self.scan_panel.focus_scan_entry()

    # --- TUTORIAL ACCESSOR ---

    def get_scan_panel_widget(self) -> ctk.CTkFrame:
        """Returns the embedded QRScanPanel widget for tutorial spotlight."""
        return self.scan_panel
