"""Interactive Tutorial Overlay & 4-Rectangle Spotlight Engine for InPhieuHienVat.

Provides a native in-window spotlight overlay and step-by-step walkthrough
across the core workflows of the SlipPrinterApp application.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence
import customtkinter as ctk


@dataclass
class TutorialStep:
    """Represents an individual step in the interactive tutorial walkthrough."""

    step_id: str
    title: str
    description: str
    target_widget_getter: Callable[[], Optional[tk.Widget | ctk.CTkBaseClass]]
    target_tab_index: Optional[int] = None
    tooltip_position: str = "auto"  # "auto", "bottom", "top", "left", "right", "center"
    padding: int = 6


class TooltipCard(ctk.CTkFrame):
    """Floating responsive glassmorphic tooltip card presenting step guidance and navigation buttons."""

    def __init__(
        self,
        master: tk.Widget | ctk.CTk,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_skip: Callable[[], None],
        width: int = 360,
        height: int = 200,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            width=width,
            height=height,
            corner_radius=14,
            border_width=2,
            border_color=("#10B981", "#10B981"),
            fg_color=("#FFFFFF", "#1E293B"),
            **kwargs,
        )
        self.on_next = on_next
        self.on_prev = on_prev
        self.on_skip = on_skip

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # 1. Header Frame: Title & Step Badge
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="💡 Hướng dẫn",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
            justify="left",
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.badge_frame = ctk.CTkFrame(
            self.header_frame,
            corner_radius=8,
            fg_color=("#E0E7FF", "#1E3A8A"),
        )
        self.badge_frame.grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.badge_label = ctk.CTkLabel(
            self.badge_frame,
            text="Bước 1 / 4",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#3730A3", "#93C5FD"),
        )
        self.badge_label.grid(row=0, column=0, padx=8, pady=2)

        # 2. Separator Line
        self.sep = ctk.CTkFrame(self, height=1, fg_color=("gray85", "gray30"))
        self.sep.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))

        # 3. Body Text (Description)
        self.desc_label = ctk.CTkLabel(
            self,
            text="Mô tả hướng dẫn sử dụng phần mềm...",
            font=ctk.CTkFont(size=13),
            wraplength=320,
            justify="left",
            anchor="w",
            text_color=("gray25", "gray85"),
        )
        self.desc_label.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 6))

        # 4. Micro-UX Keybinding Hint
        self.hint_label = ctk.CTkLabel(
            self,
            text="⌨ [Enter] Tiếp tục · [←] Quay lại · [Esc] Bỏ qua",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray50"),
        )
        self.hint_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        # 5. Action Button Row
        self.btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.btn_row.grid_columnconfigure(1, weight=1)

        self.skip_btn = ctk.CTkButton(
            self.btn_row,
            text="Bỏ qua",
            width=70,
            height=32,
            fg_color="transparent",
            hover_color=("gray85", "gray25"),
            text_color=("gray45", "gray55"),
            font=ctk.CTkFont(size=12),
            command=self.on_skip,
        )
        self.skip_btn.grid(row=0, column=0, sticky="w")

        self.right_btn_frame = ctk.CTkFrame(self.btn_row, fg_color="transparent")
        self.right_btn_frame.grid(row=0, column=2, sticky="e")

        self.prev_btn = ctk.CTkButton(
            self.right_btn_frame,
            text="◀ Quay lại",
            width=85,
            height=32,
            font=ctk.CTkFont(size=12),
            state="disabled",
            fg_color=("gray90", "gray20"),
            text_color=("gray60", "gray40"),
            hover_color=("gray70", "gray40"),
            command=self.on_prev,
        )
        self.prev_btn.grid(row=0, column=0, padx=(0, 8))
        self.prev_btn.invoke = lambda: self.on_prev()

        self.next_btn = ctk.CTkButton(
            self.right_btn_frame,
            text="Tiếp tục ▶",
            width=100,
            height=32,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            text_color="white",
            command=self.on_next,
        )
        self.next_btn.grid(row=0, column=1)

    def update_content(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Update the title, description, step counter badge, and button states.

        Supports standard signatures:
        - update_content(title, description, current_index, total_steps)
        - update_content(current, total, title, description)
        - update_content(title=..., description=..., current_index=..., total_steps=...)
        """
        title = kwargs.get("title", "")
        description = kwargs.get("description", "")
        current_index = kwargs.get("current_index", 0)
        total_steps = kwargs.get("total_steps", 1)

        if args:
            if len(args) == 4:
                # Check if first arg is int (current, total, title, desc) or str (title, desc, current, total)
                if isinstance(args[0], int) and isinstance(args[1], int):
                    curr, tot, title, description = args
                    current_index = curr - 1 if curr >= 1 else 0
                    total_steps = tot
                else:
                    title, description, current_index, total_steps = args
            elif len(args) == 2:
                title, description = args

        if "current" in kwargs:
            curr = kwargs["current"]
            current_index = curr - 1 if curr >= 1 else 0
        if "total" in kwargs:
            total_steps = kwargs["total"]

        total_steps = max(1, total_steps)
        current_index = max(0, min(current_index, total_steps - 1))
        step_number = current_index + 1

        self.title_label.configure(text=title)
        self.desc_label.configure(text=description)
        self.badge_label.configure(text=f"Bước {step_number} / {total_steps}")

        # Update Back button state
        if current_index == 0:
            self.prev_btn.configure(
                state="disabled",
                fg_color=("gray90", "gray20"),
                text_color=("gray60", "gray40"),
            )
        else:
            self.prev_btn.configure(
                state="normal",
                fg_color=("gray80", "gray30"),
                text_color=("black", "white"),
            )

        # Update Next / Complete button styling
        if current_index >= total_steps - 1:
            self.next_btn.configure(
                text="🎉 Hoàn tất",
                fg_color="#10B981",
                hover_color="#059669",
                width=110,
            )
        else:
            self.next_btn.configure(
                text="Tiếp tục ▶",
                fg_color="#2563EB",
                hover_color="#1D4ED8",
                width=100,
            )


class PlacementEngine:
    """Calculates responsive screen coordinates and boundary clamping for Tooltip placement."""

    CARD_WIDTH: int = 360
    CARD_HEIGHT: int = 200
    GAP: int = 14
    MARGIN: int = 16

    @classmethod
    def calculate(
        cls,
        root_w: int,
        root_h: int,
        spotlight_bounds: Optional[tuple[int, int, int, int]],
        card_w: int = CARD_WIDTH,
        card_h: int = CARD_HEIGHT,
        preferred_position: str = "auto",
        gap: int = GAP,
        margin: int = MARGIN,
    ) -> tuple[int, int]:
        """Calculates pixel-perfect clamped (x, y) coordinates for TooltipCard."""
        if spotlight_bounds is None or preferred_position == "center":
            pos_x = max(margin, (root_w - card_w) // 2)
            pos_y = max(margin, (root_h - card_h) // 2)
            return (pos_x, pos_y)

        x1, y1, x2, y2 = spotlight_bounds
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        space_bottom = root_h - (y2 + gap) - margin
        space_top = y1 - gap - margin
        space_right = root_w - (x2 + gap) - margin
        space_left = x1 - gap - margin

        pos = preferred_position.lower()
        if pos == "auto":
            if space_bottom >= card_h:
                pos = "bottom"
            elif space_top >= card_h:
                pos = "top"
            elif space_right >= card_w:
                pos = "right"
            elif space_left >= card_w:
                pos = "left"
            else:
                spaces = {
                    "bottom": space_bottom,
                    "top": space_top,
                    "right": space_right,
                    "left": space_left,
                }
                pos = max(spaces, key=spaces.get)
        else:
            # Check if preferred fits; flip to best alternative if overflow
            if pos == "bottom" and space_bottom < card_h:
                pos = "top" if space_top >= card_h else ("right" if space_right >= card_w else "left")
            elif pos == "top" and space_top < card_h:
                pos = "bottom" if space_bottom >= card_h else ("right" if space_right >= card_w else "left")
            elif pos == "right" and space_right < card_w:
                pos = "left" if space_left >= card_w else ("bottom" if space_bottom >= card_h else "top")
            elif pos == "left" and space_left < card_w:
                pos = "right" if space_right >= card_w else ("bottom" if space_bottom >= card_h else "top")

        if pos == "bottom":
            raw_x = cx - (card_w // 2)
            raw_y = y2 + gap
        elif pos == "top":
            raw_x = cx - (card_w // 2)
            raw_y = y1 - gap - card_h
        elif pos == "right":
            raw_x = x2 + gap
            raw_y = cy - (card_h // 2)
        elif pos == "left":
            raw_x = x1 - gap - card_w
            raw_y = cy - (card_h // 2)
        else:
            raw_x = (root_w - card_w) // 2
            raw_y = (root_h - card_h) // 2

        clamped_x = max(margin, min(raw_x, max(margin, root_w - card_w - margin)))
        clamped_y = max(margin, min(raw_y, max(margin, root_h - card_h - margin)))
        return (clamped_x, clamped_y)


class GeometryHelper:
    """Calculates screen-to-window relative coordinates, clamping, and visibility bounds."""

    @staticmethod
    def get_relative_bounds(
        root: tk.Tk | ctk.CTk,
        widget: Optional[tk.Widget | ctk.CTkBaseClass],
        pad: int = 6,
    ) -> Optional[tuple[int, int, int, int]]:
        """Calculate clamped relative (x1, y1, x2, y2) bounds of a widget inside root window."""
        if widget is None:
            return None

        actual_widget = getattr(widget, "_canvas", widget)
        try:
            if hasattr(actual_widget, "winfo_exists") and not actual_widget.winfo_exists():
                return None
            if hasattr(actual_widget, "winfo_ismapped") and not actual_widget.winfo_ismapped():
                return None

            w_w = actual_widget.winfo_width() if hasattr(actual_widget, "winfo_width") else 0
            w_h = actual_widget.winfo_height() if hasattr(actual_widget, "winfo_height") else 0
            if w_w <= 1 or w_h <= 1:
                return None

            root_x = root.winfo_rootx()
            root_y = root.winfo_rooty()
            root_w = root.winfo_width()
            root_h = root.winfo_height()

            w_x = actual_widget.winfo_rootx()
            w_y = actual_widget.winfo_rooty()

            rel_x = w_x - root_x
            rel_y = w_y - root_y

            x1 = max(0, rel_x - pad)
            y1 = max(0, rel_y - pad)
            x2 = min(root_w, rel_x + w_w + pad)
            y2 = min(root_h, rel_y + w_h + pad)

            if x2 <= x1 or y2 <= y1:
                return None

            return (x1, y1, x2, y2)
        except Exception:
            return None


class TabSyncHelper:
    """Manages switching and stabilizing ttk.Notebook tabs for target widgets."""

    @staticmethod
    def ensure_tab_active(
        root: tk.Tk | ctk.CTk,
        notebook: Optional[ttk.Notebook | tk.Widget],
        target_tab_index: Optional[int],
        target_widget: Optional[tk.Widget | ctk.CTkBaseClass] = None,
    ) -> bool:
        """Switches to target tab if needed and executes synchronous layout updates."""
        if notebook is None and target_widget is not None:
            notebook = TabSyncHelper.find_parent_notebook(target_widget)

        if notebook is None or target_tab_index is None:
            return False

        try:
            if isinstance(notebook, ttk.Notebook):
                current_tab = notebook.index(notebook.select())
                if current_tab != target_tab_index:
                    notebook.select(target_tab_index)
                    root.update_idletasks()
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def find_parent_notebook(widget: tk.Widget | ctk.CTkBaseClass) -> Optional[ttk.Notebook]:
        """Crawl ancestor hierarchy to locate enclosing ttk.Notebook."""
        curr = getattr(widget, "_canvas", widget)
        while curr:
            try:
                parent_name = curr.winfo_parent()
                if not parent_name:
                    break
                parent = curr.nametowidget(parent_name)
                if isinstance(parent, ttk.Notebook):
                    return parent
                curr = parent
            except Exception:
                break
        return None


class InteractiveTutorialOverlay:
    """Main Tutorial Engine.

    Orchestrates:
    - In-Window Canvas placed on root window
    - 4-Rectangle dark scrim cutout
    - Multi-stroke Emerald glow highlight border (#10B981)
    - Modal mouse click event interception
    - Debounced <Configure> resize / move listener
    - Automatic ttk.Notebook tab selection with update_idletasks()
    - Full keyboard navigation (<Escape>, <Return>, <Left>, <Right>, <space>)
    - Clean teardown and unbinding.
    """

    SCRIM_COLOR: str = "#0B0F19"
    SCRIM_STIPPLE: str = "gray50"
    BORDER_COLOR: str = "#10B981"
    GLOW_INNER: str = "#34D399"
    GLOW_OUTER: str = "#064E3B"

    def __init__(
        self,
        master_window: tk.Tk | ctk.CTk,
        on_finish: Optional[Callable[[], None]] = None,
        notebook: Optional[ttk.Notebook | tk.Widget] = None,
    ) -> None:
        self.master = master_window
        self.on_finish = on_finish
        self.notebook = notebook

        self.steps: list[TutorialStep] = []
        self._current_step_index: int = 0
        self._is_active: bool = False
        self._is_destroyed: bool = False

        self._configure_timer_id: Optional[str] = None
        self._bound_events: list[tuple[str, str]] = []

        self.canvas: Optional[tk.Canvas] = None
        self.tooltip: Optional[TooltipCard] = None

    @property
    def is_active(self) -> bool:
        """Returns True if the tutorial overlay is currently displayed."""
        return self._is_active and not self._is_destroyed

    @property
    def current_step_index(self) -> int:
        """Returns the current step index (0-based)."""
        return self._current_step_index

    @property
    def tooltip_card(self) -> Optional[TooltipCard]:
        """Accessor for the active tooltip card component."""
        return self.tooltip

    def register_steps(self, steps: Sequence[TutorialStep]) -> None:
        """Register the sequence of tutorial steps to be presented."""
        self.steps = list(steps)

    def start(self, start_step_index: int = 0) -> None:
        """Activate the overlay and begin the interactive walkthrough."""
        if not self.steps:
            return

        self._is_destroyed = False
        self._is_active = True
        self._current_step_index = max(0, min(start_step_index, len(self.steps) - 1))

        self._build_overlay()
        self._bind_events()
        self._render_current_step()

    def _build_overlay(self) -> None:
        """Create and place the scrim Canvas and TooltipCard on the master window."""
        if self.canvas is not None or getattr(self, "overlay_win", None) is not None:
            self._cleanup_widgets()

        # 1. Full-window Toplevel Overlay (Windows native semi-transparency)
        self.overlay_win = tk.Toplevel(self.master)
        self.overlay_win.overrideredirect(True)
        self.overlay_win.attributes("-alpha", 0.75)
        # "magenta" will be our transparent cutout color
        self.overlay_win.attributes("-transparentcolor", "magenta")
        self.overlay_win.configure(bg="magenta")
        
        # Match master window geometry
        self._sync_overlay_geometry()

        self.canvas = tk.Canvas(
            self.overlay_win,
            highlightthickness=0,
            borderwidth=0,
            bg="magenta",
            cursor="arrow",
        )
        self.canvas.pack(fill="both", expand=True)

        # Intercept background mouse events on the overlay
        for event_name in (
            "<Button-1>", "<Button-2>", "<Button-3>",
            "<Double-Button-1>", "<Triple-Button-1>",
            "<B1-Motion>", "<B2-Motion>", "<B3-Motion>", "<MouseWheel>"
        ):
            self.canvas.bind(event_name, lambda e: "break")

        # 2. Tooltip Card (now placed on the overlay window so it can be clicked)
        self.tooltip = TooltipCard(
            self.overlay_win,
            width=PlacementEngine.CARD_WIDTH,
            height=PlacementEngine.CARD_HEIGHT,
            on_next=self.next_step,
            on_prev=self.prev_step,
            on_skip=self.skip,
        )
        # Note: CTk widgets on a Toplevel with transparentcolor might render strangely if they contain the transparent color, but magenta is safe.
        
        # Disable the main window to trap focus and prevent clicking through the transparent hole
        try:
            self.master.attributes("-disabled", True)
        except Exception:
            pass

    def _sync_overlay_geometry(self) -> None:
        if getattr(self, "overlay_win", None) and self.overlay_win.winfo_exists():
            w = self.master.winfo_width()
            h = self.master.winfo_height()
            x = self.master.winfo_rootx()
            y = self.master.winfo_rooty()
            self.overlay_win.geometry(f"{w}x{h}+{x}+{y}")

    def _bind_events(self) -> None:
        """Register keyboard navigation shortcuts and window resize listener."""
        self._unbind_events()

        def _on_key_skip(e: tk.Event) -> str:
            self.skip()
            return "break"

        def _on_key_next(e: tk.Event) -> str:
            self.next_step()
            return "break"

        def _on_key_prev(e: tk.Event) -> str:
            self.prev_step()
            return "break"

        key_mappings = [
            ("<Escape>", _on_key_skip),
            ("<Return>", _on_key_next),
            ("<KP_Enter>", _on_key_next),
            ("<Right>", _on_key_next),
            ("<space>", _on_key_next),
            ("<Left>", _on_key_prev),
        ]

        for seq, handler in key_mappings:
            try:
                func_id = self.master.bind(seq, handler, add="+")
                self._bound_events.append((seq, func_id))
            except Exception:
                pass

        try:
            cfg_func_id = self.master.bind("<Configure>", self._on_configure, add="+")
            self._bound_events.append(("<Configure>", cfg_func_id))
        except Exception:
            pass

    def _unbind_events(self) -> None:
        """Safely unbind all registered event listeners from master window."""
        for seq, func_id in self._bound_events:
            try:
                self.master.unbind(seq, func_id)
            except Exception:
                pass
        self._bound_events.clear()

    def _on_configure(self, event: tk.Event) -> None:
        """Debounced handler for root window resize and movement events."""
        if not self._is_active or self._is_destroyed:
            return

        # Filter out child widget configure notifications
        if event.widget != self.master:
            return

        if self._configure_timer_id is not None:
            try:
                self.master.after_cancel(self._configure_timer_id)
            except Exception:
                pass
            self._configure_timer_id = None

        self._configure_timer_id = self.master.after(60, self._debounced_recalculate)

    def _debounced_recalculate(self) -> None:
        """Executes actual redraw after resize settling."""
        self._configure_timer_id = None
        if self._is_active and not self._is_destroyed:
            self._sync_overlay_geometry()
            self._render_current_step()

    def _calculate_spotlight_bounds(
        self,
        target: Optional[tk.Widget | ctk.CTkBaseClass],
        padding: int = 6,
    ) -> Optional[tuple[int, int, int, int]]:
        """Calculates spotlight coordinates with padding for a given target widget."""
        return GeometryHelper.get_relative_bounds(self.master, target, pad=padding)

    def _render_current_step(self) -> None:
        """Renders the current step's spotlight cutout, glow borders, and tooltip."""
        if not self._is_active or self._is_destroyed or not self.canvas or not self.tooltip:
            return

        if not self.steps or self._current_step_index >= len(self.steps):
            self.destroy()
            return

        step = self.steps[self._current_step_index]

        # 1. Synchronize Notebook Tab if step targets an inactive tab
        notebook = self.notebook
        if notebook is None:
            notebook = getattr(self.master, "notebook", None)

        if step.target_tab_index is not None and notebook is not None:
            try:
                current_tab = notebook.index(notebook.select())
                if current_tab != step.target_tab_index:
                    notebook.select(step.target_tab_index)
                    self.master.update_idletasks()
            except Exception:
                pass

        # 2. Get target widget and calculate bounding coordinates
        target_widget = None
        if step.target_widget_getter:
            try:
                target_widget = step.target_widget_getter()
            except Exception:
                target_widget = None

        self.master.update_idletasks()
        bounds = self._calculate_spotlight_bounds(target_widget, padding=step.padding)

        # 3. Draw 4-Rectangle Scrim and Spotlight Glow Border
        self._draw_scrim_and_spotlight(bounds)

        # 4. Update Tooltip Content & Position
        self.tooltip.update_content(
            title=step.title,
            description=step.description,
            current_index=self._current_step_index,
            total_steps=len(self.steps),
        )

        root_w = max(100, self.master.winfo_width())
        root_h = max(100, self.master.winfo_height())
        pos_x, pos_y = PlacementEngine.calculate(
            root_w=root_w,
            root_h=root_h,
            spotlight_bounds=bounds,
            card_w=PlacementEngine.CARD_WIDTH,
            card_h=PlacementEngine.CARD_HEIGHT,
            preferred_position=step.tooltip_position,
        )

        self.tooltip.place(
            x=pos_x,
            y=pos_y,
        )

        # Ensure overlay and tooltip stay on top
        tk.Misc.lift(self.canvas)
        tk.Misc.lift(self.tooltip)

    def _draw_scrim_and_spotlight(self, bounds: Optional[tuple[int, int, int, int]]) -> None:
        """Draws the 4-Rectangle dark scrim cutout and multi-stroke Emerald glow border."""
        if not self.canvas:
            return

        self.canvas.delete("all")
        win_w = max(100, self.master.winfo_width())
        win_h = max(100, self.master.winfo_height())

        if bounds is None:
            # Modal mode: Full blackout scrim when target is None or unmapped
            self.canvas.create_rectangle(
                0,
                0,
                win_w,
                win_h,
                fill=self.SCRIM_COLOR,
                outline="",
                tags="scrim_slice",
            )
            return

        x1, y1, x2, y2 = bounds

        # 4-Rectangle Disjoint Partitioning
        # 1. Top Slice: (0, 0, win_w, y1)
        if y1 > 0:
            self.canvas.create_rectangle(
                0,
                0,
                win_w,
                y1,
                fill=self.SCRIM_COLOR,
                outline="",
                tags="scrim_slice",
            )

        # 2. Bottom Slice: (0, y2, win_w, win_h)
        if y2 < win_h:
            self.canvas.create_rectangle(
                0,
                y2,
                win_w,
                win_h,
                fill=self.SCRIM_COLOR,
                outline="",
                tags="scrim_slice",
            )

        # 3. Left Slice: (0, y1, x1, y2)
        if x1 > 0 and y2 > y1:
            self.canvas.create_rectangle(
                0,
                y1,
                x1,
                y2,
                fill=self.SCRIM_COLOR,
                outline="",
                tags="scrim_slice",
            )

        # 4. Right Slice: (x2, y1, win_w, y2)
        if x2 < win_w and y2 > y1:
            self.canvas.create_rectangle(
                x2,
                y1,
                win_w,
                y2,
                fill=self.SCRIM_COLOR,
                outline="",
                tags="scrim_slice",
            )

        # Multi-stroke Emerald Glow Spotlight Border
        # Outer subtle glow
        self.canvas.create_rectangle(
            x1 - 3,
            y1 - 3,
            x2 + 3,
            y2 + 3,
            outline=self.GLOW_OUTER,
            width=1,
            tags="scrim_glow",
        )
        # Mid glow
        self.canvas.create_rectangle(
            x1 - 1,
            y1 - 1,
            x2 + 1,
            y2 + 1,
            outline=self.GLOW_INNER,
            width=1,
            tags="scrim_glow",
        )
        # Crisp accent border
        self.canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            outline=self.BORDER_COLOR,
            width=2,
            tags="scrim_glow",
        )

    def next_step(self) -> None:
        """Advance to the next tutorial step or complete walkthrough."""
        if not self._is_active or self._is_destroyed:
            return

        if self._current_step_index < len(self.steps) - 1:
            self._current_step_index += 1
            self._render_current_step()
        else:
            self.finish()

    def prev_step(self) -> None:
        """Go back to the previous tutorial step."""
        if not self._is_active or self._is_destroyed:
            return

        if self._current_step_index > 0:
            self._current_step_index -= 1
            self._render_current_step()

    def skip(self) -> None:
        """Dismiss and skip the tutorial walkthrough."""
        self.destroy()

    def finish(self) -> None:
        """Complete the tutorial walkthrough and trigger completion callback."""
        callback = self.on_finish
        self.destroy()
        if callback is not None:
            try:
                callback()
            except Exception:
                pass

    def _cleanup_widgets(self) -> None:
        """Destroys tooltip card and canvas."""
        if self.tooltip is not None:
            try:
                self.tooltip.destroy()
            except Exception:
                pass
            self.tooltip = None

        if self.canvas is not None:
            try:
                self.canvas.destroy()
            except Exception:
                pass
            self.canvas = None

        if getattr(self, "overlay_win", None) is not None:
            try:
                self.overlay_win.destroy()
            except Exception:
                pass
            self.overlay_win = None

        try:
            self.master.attributes("-disabled", False)
        except Exception:
            pass

    def destroy(self) -> None:
        """Clean teardown: unbind events, cancel timers, and remove UI widgets."""
        if self._is_destroyed:
            return

        self._is_destroyed = True
        self._is_active = False

        if self._configure_timer_id is not None:
            try:
                self.master.after_cancel(self._configure_timer_id)
            except Exception:
                pass
            self._configure_timer_id = None

        self._unbind_events()
        self._cleanup_widgets()

        try:
            self.master.focus_set()
        except Exception:
            pass


# Compatibility Alias & Re-exports
TutorialOverlay = InteractiveTutorialOverlay
from ui.components.tutorial_script import build_tutorial_steps  # noqa: E402

__all__ = [
    "InteractiveTutorialOverlay",
    "TutorialOverlay",
    "TutorialStep",
    "TooltipCard",
    "PlacementEngine",
    "GeometryHelper",
    "TabSyncHelper",
    "build_tutorial_steps",
]

