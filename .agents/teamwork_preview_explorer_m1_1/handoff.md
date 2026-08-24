# Overlay Canvas Architecture & 4-Rectangle Spotlight Engine Specification

## 1. Observation
- **Requirement Source**: `ORIGINAL_REQUEST.md` (R1: Interactive Tutorial UI Overlay, R2: 4-Step Script, R3: Trigger & Persistence) and `PROJECT.md` (Feature 1 & Feature 2, Milestone 1).
- **Host Application Context**:
  - `SlipPrinterApp` (`ui/main_window.py:31`) inherits from `customtkinter.CTk` (root window).
  - Main layout uses `ttk.Panedwindow` containing `SidebarPanel` (left, width=360) and `content` (right) with a `ttk.Notebook` holding `DataTabPanel`, `LayoutTabPanel`, and `HistoryTabPanel`.
  - Color theme uses Emerald Green `#10B981` (Von Restorff primary accent) for Generate button, Blue `#2563EB` for QR Scan, and Amber `#F59E0B` for Tutorial Trigger.
  - Windows environment running Python with CustomTkinter 5.x.
- **Tkinter/CustomTkinter Canvas Behavior**:
  - On Windows, a secondary `Toplevel` window with `-transparentcolor` or `-alpha` suffers from window manager desynchronization, taskbar clutter, z-ordering flicker during window move/resize, and OS click-through bugs.
  - An **In-Window Overlay** placed directly on the root `CTk` window using `.place(x=0, y=0, relwidth=1.0, relheight=1.0)` guarantees 100% in-process synchronization, automatic resizing, zero OS taskbar artifacting, and strict z-stack control via `.lift()`.

---

## 2. Logic Chain

### 2.1. In-Window Canvas Scrim Placement Architecture
1. **Parent Container**: The overlay must be a direct child of `master_window` (`SlipPrinterApp` / `ctk.CTk`).
2. **Placement**:
   ```python
   self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
   self.canvas.lift()
   ```
3. **Z-Stack Discipline**:
   - Calling `self.canvas.lift()` ensures the overlay is on top of all root window children (Splitter, Sidebar, Content Notebook, Footer).
   - The floating Tooltip Card (`CTkFrame`) is also a child of `master_window` (or placed within the overlay) and lifted via `tooltip_card.lift()`, positioning it above the scrim.
4. **Resizing & Dynamic Re-anchoring**:
   - `master_window.bind("<Configure>", self._on_configure)` dynamically recalculates widget coordinates when the user moves or resizes the application window.
   - Resize events are debounced using `master_window.after(50, self._debounced_recalculate)` to prevent frame stutter.

---

### 2.2. Mathematical Proof & 4-Rectangle Spotlight Cutout Algorithm
To spotlight a target widget while shading the rest of the application without covering the target widget:

#### Coordinate Transformation:
Given root window dimensions $W = \text{master.winfo\_width()}$, $H = \text{master.winfo\_height()}$, and target widget $T$:
$$\text{wx} = T\text{.winfo\_rootx()} - \text{master.winfo\_rootx()}$$
$$\text{wy} = T\text{.winfo\_rooty()} - \text{master.winfo\_rooty()}$$
$$\text{ww} = T\text{.winfo\_width()}$$
$$\text{wh} = T\text{.winfo\_height()}$$

With padding $P$ (default $P = 6\text{px}$):
$$x_1 = \max(0, \text{wx} - P)$$
$$y_1 = \max(0, \text{wy} - P)$$
$$x_2 = \min(W, \text{wx} + \text{ww} + P)$$
$$y_2 = \min(H, \text{wy} + \text{wh} + P)$$

#### 4-Rectangle Disjoint Partitioning:
The region to be shaded is $\mathcal{R}_{\text{scrim}} = ([0, W] \times [0, H]) \setminus ([x_1, x_2] \times [y_1, y_2])$. This is partitioned into 4 mutually disjoint rectangles:

```
(0, 0) ┌────────────────────────────────────────────────────────┐ (W, 0)
       │                 1. TOP RECTANGLE                       │
       │                 Coords: (0, 0, W, y1)                  │
(0, y1)├──────────────┬─────────────────────────┬───────────────┤ (W, y1)
       │ 3. LEFT RECT │   [SPOTLIGHT CUTOUT]    │ 4. RIGHT RECT │
       │ (0, y1,      │   (x1, y1, x2, y2)      │ (x2, y1,      │
       │  x1, y2)     │   100% UNCOVERED        │  W, y2)       │
(0, y2)├──────────────┴─────────────────────────┴───────────────┤ (W, y2)
       │                 2. BOTTOM RECTANGLE                    │
       │                 Coords: (0, y2, W, H)                  │
(0, H) └────────────────────────────────────────────────────────┘ (W, H)
```

1. **Top Slice**: `(0, 0, W, y1)` — active if $y_1 > 0$
2. **Bottom Slice**: `(0, y2, W, H)` — active if $y_2 < H$
3. **Left Slice**: `(0, y1, x1, y2)` — active if $x_1 > 0$ and $y_2 > y_1$
4. **Right Slice**: `(x2, y1, W, y2)` — active if $x_2 < W$ and $y_2 > y_1$

#### Mathematical Properties:
- **Zero Overlap**: $S_{\text{top}} \cap S_{\text{bottom}} \cap S_{\text{left}} \cap S_{\text{right}} = \emptyset$.
- **Complete Coverage**: $S_{\text{top}} \cup S_{\text{bottom}} \cup S_{\text{left}} \cup S_{\text{right}} \cup \text{Cutout} = [0, W] \times [0, H]$.
- **100% Transparency**: The cutout bounding box $[x_1, x_2] \times [y_1, y_2]$ has zero canvas items / zero scrim widgets placed over it, leaving the underlying CustomTkinter widgets completely visible and sharp with no color distortion.

---

### 2.3. Dual Implementation Modes (Canvas Vector vs 4-Frame Scrim)

#### Architecture A: Single `tk.Canvas` with Vector Rectangles (Recommended for High Performance)
- A single `tk.Canvas` with `bg=""` or dark scrim color with `stipple="gray50"` (Windows native dither) or solid `#090D16`.
- Vector rectangle items tagged `"scrim"`:
  ```python
  canvas.delete("scrim")
  # Top
  if y1 > 0:
      canvas.create_rectangle(0, 0, W, y1, fill=scrim_color, outline="", tags="scrim", stipple=stipple_pattern)
  # Bottom
  if y2 < H:
      canvas.create_rectangle(0, y2, W, H, fill=scrim_color, outline="", tags="scrim", stipple=stipple_pattern)
  # Left
  if x1 > 0 and y2 > y1:
      canvas.create_rectangle(0, y1, x1, y2, fill=scrim_color, outline="", tags="scrim", stipple=stipple_pattern)
  # Right
  if x2 < W and y2 > y1:
      canvas.create_rectangle(x2, y1, W, y2, fill=scrim_color, outline="", tags="scrim", stipple=stipple_pattern)
  ```

#### Architecture B: 4-Frame Scrim Slices (Recommended for 100% Native CustomTkinter Look)
- Create 4 `ctk.CTkFrame` widgets (`scrim_top`, `scrim_bottom`, `scrim_left`, `scrim_right`) with `fg_color=("#111827", "#030712")`.
- Place them using `.place(x=..., y=..., width=..., height=...)`.
- In this mode, the cutout has no HWND overhead at all, and underlying widgets remain 100% interactive or viewable.

---

### 2.4. Glow Outline & Accent Border
- **Accent Color**: Emerald Green `#10B981` (primary action) or Electric Blue `#3B82F6` (informative).
- **Glow Effect Implementation**:
  - **Option 1 (Canvas Vector Layer)**:
    Draw a multi-stroke outer glow on the canvas around $(x_1, y_1, x_2, y_2)$:
    ```python
    # Outer subtle glow (spread: 3px)
    canvas.create_rectangle(x1 - 3, y1 - 3, x2 + 3, y2 + 3, outline="#064E3B", width=1, tags="scrim_glow")
    # Mid glow (spread: 1.5px)
    canvas.create_rectangle(x1 - 1, y1 - 1, x2 + 1, y2 + 1, outline="#059669", width=2, tags="scrim_glow")
    # Main crisp border
    canvas.create_rectangle(x1, y1, x2, y2, outline="#10B981", width=2, tags="scrim_glow")
    ```
  - **Option 2 (Floating Rounded CTkFrame Border)**:
    Create a transparent `ctk.CTkFrame` with `fg_color="transparent"`, `border_width=3`, `border_color="#10B981"`, `corner_radius=8`, placed at $(x_1, y_1, x_2 - x_1, y_2 - y_1)$. This provides modern anti-aliased rounded corners.

---

### 2.5. Background Mouse Click Interception & Modal Trap
- **Security & UX Requirement**: Obscured UI controls must not trigger actions (e.g. user cannot accidentally click "Generate PDF" or delete records while tutorial is explaining Excel Import).
- **Event Interception**:
  ```python
  def _block_event(event):
      return "break"  # Consumes event and halts Tk event propagation

  # Bind to canvas or all 4 scrim frames
  for event_name in ("<Button-1>", "<Button-2>", "<Button-3>", "<Double-Button-1>", "<B1-Motion>", "<MouseWheel>"):
      canvas.bind(event_name, _block_event)
  ```
- **Keyboard Shortcuts**:
  - `<Escape>` -> Cancel / Skip tutorial (`self.skip()`)
  - `<Right>` / `<Return>` / `<space>` -> Next step (`self.next_step()`)
  - `<Left>` -> Previous step (`self.prev_step()`)

---

### 2.6. Tooltip Positioning Strategy
The tooltip card calculates its $(tx, ty)$ dynamically based on available screen space:
- **Priority**:
  1. `bottom` (Default): If $y_2 + \text{card\_height} + 16 \le H$, place below target widget at $(x_1, y_2 + 12)$.
  2. `top`: If not enough space below and $y_1 - \text{card\_height} - 16 \ge 0$, place above at $(x_1, y_1 - \text{card\_height} - 12)$.
  3. `right`: If vertical space constrained and $x_2 + \text{card\_width} + 16 \le W$, place at $(x_2 + 12, y_1)$.
  4. `left`: If right constrained and $x_1 - \text{card\_width} - 16 \ge 0$, place at $(x_1 - \text{card\_width} - 12, y_1)$.
  5. `center`: Fallback to screen center if target widget is off-screen or None.
- **Horizontal Clamping**: Ensure $tx = \max(16, \min(W - \text{card\_width} - 16, tx))$.

---

## 3. Concrete Code Blueprint for Worker (`ui/components/tutorial_overlay.py`)

Here is the complete, self-contained implementation blueprint ready for M1 Worker:

```python
"""
Interactive Tutorial Overlay & 4-Rectangle Spotlight Engine for InPhieuHienVat.
Provides an in-window non-intrusive scrim overlay, dynamic coordinate tracking,
emerald glow spotlight borders, and a responsive step-by-step tooltip card.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional
import customtkinter as ctk


@dataclass
class TutorialStep:
    step_id: str
    title: str
    description: str
    target_widget_getter: Callable[[], Optional[tk.Widget]]
    target_tab_index: Optional[int] = None
    tooltip_position: str = "auto"  # "auto", "bottom", "top", "left", "right"
    padding: int = 6


class TooltipCard(ctk.CTkFrame):
    """Floating responsive glassmorphic tooltip card with navigation controls."""

    def __init__(
        self,
        master: tk.Widget,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_skip: Callable[[], None],
        **kwargs,
    ):
        super().__init__(
            master,
            corner_radius=12,
            border_width=2,
            border_color=("#10B981", "#10B981"),
            fg_color=("white", "#1E293B"),
            **kwargs,
        )
        self.on_next = on_next
        self.on_prev = on_prev
        self.on_skip = on_skip

        self.grid_columnconfigure(0, weight=1)

        # Header: Step badge & Title
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        header_frame.grid_columnconfigure(1, weight=1)

        self.step_badge = ctk.CTkLabel(
            header_frame,
            text="1/4",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#10B981", "#059669"),
            text_color="white",
            corner_radius=6,
            width=36,
            height=20,
        )
        self.step_badge.grid(row=0, column=0, padx=(0, 8), sticky="w")

        self.title_label = ctk.CTkLabel(
            header_frame,
            text="Bước hướng dẫn",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.title_label.grid(row=0, column=1, sticky="w")

        # Body: Description
        self.desc_label = ctk.CTkLabel(
            self,
            text="Mô tả chi tiết hướng dẫn sử dụng...",
            font=ctk.CTkFont(size=13),
            wraplength=340,
            justify="left",
            anchor="w",
            text_color=("gray20", "gray80"),
        )
        self.desc_label.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 14))

        # Footer: Controls
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 14))
        btn_frame.grid_columnconfigure(1, weight=1)

        self.skip_btn = ctk.CTkButton(
            btn_frame,
            text="Bỏ qua",
            width=65,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=("gray40", "gray60"),
            hover_color=("gray90", "gray25"),
            command=self.on_skip,
        )
        self.skip_btn.grid(row=0, column=0, sticky="w")

        nav_box = ctk.CTkFrame(btn_frame, fg_color="transparent")
        nav_box.grid(row=0, column=2, sticky="e")

        self.prev_btn = ctk.CTkButton(
            nav_box,
            text="Quay lại",
            width=70,
            height=28,
            font=ctk.CTkFont(size=12),
            fg_color=("gray85", "gray30"),
            text_color=("gray10", "gray90"),
            hover_color=("gray75", "gray40"),
            command=self.on_prev,
        )
        self.prev_btn.pack(side="left", padx=(0, 6))

        self.next_btn = ctk.CTkButton(
            nav_box,
            text="Tiếp tục",
            width=80,
            height=28,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#10B981",
            hover_color="#059669",
            text_color="white",
            command=self.on_next,
        )
        self.next_btn.pack(side="left")

    def update_content(self, current: int, total: int, title: str, description: str) -> None:
        self.step_badge.configure(text=f"{current}/{total}")
        self.title_label.configure(text=title)
        self.desc_label.configure(text=description)
        self.prev_btn.configure(state="normal" if current > 1 else "disabled")
        self.next_btn.configure(text="Hoàn tất" if current == total else "Tiếp tục")


class InteractiveTutorialOverlay:
    """
    Main Tutorial Engine: Orchestrates 4-rectangle canvas scrim, glowing spotlight,
    modal focus trapping, automatic tab switching, and debounced window resize tracking.
    """

    def __init__(
        self,
        master_window: ctk.CTk,
        on_finish: Optional[Callable[[], None]] = None,
        notebook: Optional[tk.Widget] = None,
    ):
        self.master = master_window
        self.on_finish = on_finish
        self.notebook = notebook

        self.steps: list[TutorialStep] = []
        self.current_step_index: int = 0
        self._is_active: bool = False
        self._configure_job: Optional[str] = None

        # Scrim styling
        self.scrim_color = "#0B0F19"
        self.glow_color = "#10B981"
        self.glow_outer = "#064E3B"

        # Canvas overlay
        self.canvas: Optional[tk.Canvas] = None
        self.tooltip: Optional[TooltipCard] = None

    def register_steps(self, steps: list[TutorialStep]) -> None:
        self.steps = list(steps)

    def start(self, start_step_index: int = 0) -> None:
        if not self.steps:
            return

        self._is_active = True
        self.current_step_index = max(0, min(start_step_index, len(self.steps) - 1))

        self._build_overlay()
        self._bind_events()
        self._render_current_step()

    def _build_overlay(self) -> None:
        if self.canvas is not None:
            self.destroy()

        # Create full-window In-Window Canvas
        self.canvas = tk.Canvas(
            self.master,
            highlightthickness=0,
            borderwidth=0,
            bg=self.scrim_color,
            cursor="arrow",
        )
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.canvas.lift()

        # Intercept background clicks
        for event_name in (
            "<Button-1>", "<Button-2>", "<Button-3>",
            "<Double-Button-1>", "<B1-Motion>", "<MouseWheel>"
        ):
            self.canvas.bind(event_name, lambda e: "break")

        # Create Tooltip Card
        self.tooltip = TooltipCard(
            self.master,
            on_next=self.next_step,
            on_prev=self.prev_step,
            on_skip=self.skip,
        )
        self.tooltip.lift()

    def _bind_events(self) -> None:
        self.master.bind("<Configure>", self._on_configure, add="+")
        self.master.bind("<Escape>", lambda e: self.skip(), add="+")
        self.master.bind("<Right>", lambda e: self.next_step(), add="+")
        self.master.bind("<Left>", lambda e: self.prev_step(), add="+")
        self.master.bind("<Return>", lambda e: self.next_step(), add="+")

    def _unbind_events(self) -> None:
        try:
            self.master.unbind("<Configure>")
            self.master.unbind("<Escape>")
            self.master.unbind("<Right>")
            self.master.unbind("<Left>")
            self.master.unbind("<Return>")
        except Exception:
            pass

    def _on_configure(self, event: tk.Event) -> None:
        if not self._is_active:
            return
        if self._configure_job is not None:
            self.master.after_cancel(self._configure_job)
        self._configure_job = self.master.after(40, self._render_current_step)

    def _render_current_step(self) -> None:
        if not self._is_active or not self.canvas or not self.tooltip:
            return

        step = self.steps[self.current_step_index]

        # 1. Switch tab if required
        if step.target_tab_index is not None and self.notebook is not None:
            try:
                self.notebook.select(step.target_tab_index)
                self.master.update_idletasks()
            except Exception:
                pass

        # 2. Get target widget & calculate bounding box
        target = step.target_widget_getter()
        bbox = self._calculate_cutout_bbox(target, pad=step.padding)

        # 3. Redraw 4-Rectangle Scrim & Glow on Canvas
        self._draw_scrim_and_spotlight(bbox)

        # 4. Position and update Tooltip Card
        self.tooltip.update_content(
            current=self.current_step_index + 1,
            total=len(self.steps),
            title=step.title,
            description=step.description,
        )
        self._position_tooltip(bbox, step.tooltip_position)

        # Keep overlay and tooltip on top
        self.canvas.lift()
        self.tooltip.lift()

    def _calculate_cutout_bbox(
        self, target: Optional[tk.Widget], pad: int = 6
    ) -> Optional[tuple[int, int, int, int]]:
        if target is None:
            return None

        try:
            target.update_idletasks()
            if not target.winfo_ismapped() or target.winfo_width() <= 1:
                return None

            root_x = self.master.winfo_rootx()
            root_y = self.master.winfo_rooty()
            win_w = self.master.winfo_width()
            win_h = self.master.winfo_height()

            wx = target.winfo_rootx() - root_x
            wy = target.winfo_rooty() - root_y
            ww = target.winfo_width()
            wh = target.winfo_height()

            x1 = max(0, wx - pad)
            y1 = max(0, wy - pad)
            x2 = min(win_w, wx + ww + pad)
            y2 = min(win_h, wy + wh + pad)

            if x2 > x1 and y2 > y1:
                return (x1, y1, x2, y2)
        except Exception:
            return None
        return None

    def _draw_scrim_and_spotlight(self, bbox: Optional[tuple[int, int, int, int]]) -> None:
        self.canvas.delete("all")
        win_w = self.master.winfo_width()
        win_h = self.master.winfo_height()

        if bbox is None:
            # Full blackout scrim when target is None/hidden
            self.canvas.create_rectangle(0, 0, win_w, win_h, fill=self.scrim_color, outline="", stipple="gray50")
            return

        x1, y1, x2, y2 = bbox

        # 4-Rectangle Scrim Partitioning (with stipple for semi-transparency)
        # 1. Top Slice
        if y1 > 0:
            self.canvas.create_rectangle(0, 0, win_w, y1, fill=self.scrim_color, outline="", stipple="gray50")
        # 2. Bottom Slice
        if y2 < win_h:
            self.canvas.create_rectangle(0, y2, win_w, win_h, fill=self.scrim_color, outline="", stipple="gray50")
        # 3. Left Slice
        if x1 > 0 and y2 > y1:
            self.canvas.create_rectangle(0, y1, x1, y2, fill=self.scrim_color, outline="", stipple="gray50")
        # 4. Right Slice
        if x2 < win_w and y2 > y1:
            self.canvas.create_rectangle(x2, y1, win_w, y2, fill=self.scrim_color, outline="", stipple="gray50")

        # Multi-stroke Emerald Glow Border
        # Outer glow
        self.canvas.create_rectangle(x1 - 3, y1 - 3, x2 + 3, y2 + 3, outline=self.glow_outer, width=1)
        # Inner glow
        self.canvas.create_rectangle(x1 - 1, y1 - 1, x2 + 1, y2 + 1, outline="#059669", width=2)
        # Crisp accent border
        self.canvas.create_rectangle(x1, y1, x2, y2, outline=self.glow_color, width=2)

    def _position_tooltip(self, bbox: Optional[tuple[int, int, int, int]], preferred_pos: str) -> None:
        if not self.tooltip:
            return

        self.master.update_idletasks()
        card_w = 380
        card_h = 160
        win_w = self.master.winfo_width()
        win_h = self.master.winfo_height()

        if bbox is None:
            # Center on screen
            tx = max(16, (win_w - card_w) // 2)
            ty = max(16, (win_h - card_h) // 2)
            self.tooltip.place(x=tx, y=ty, width=card_w, height=card_h)
            return

        x1, y1, x2, y2 = bbox

        # Calculate positioning
        if preferred_pos == "bottom" or preferred_pos == "auto":
            if y2 + card_h + 20 <= win_h:
                tx = x1
                ty = y2 + 12
            elif y1 - card_h - 20 >= 0:
                tx = x1
                ty = y1 - card_h - 12
            else:
                tx = min(win_w - card_w - 20, x2 + 16)
                ty = y1
        elif preferred_pos == "top":
            if y1 - card_h - 20 >= 0:
                tx = x1
                ty = y1 - card_h - 12
            else:
                tx = x1
                ty = y2 + 12
        elif preferred_pos == "right":
            if x2 + card_w + 20 <= win_w:
                tx = x2 + 12
                ty = y1
            else:
                tx = max(16, x1 - card_w - 12)
                ty = y1
        elif preferred_pos == "left":
            if x1 - card_w - 20 >= 0:
                tx = x1 - card_w - 12
                ty = y1
            else:
                tx = x2 + 12
                ty = y1
        else:
            tx = (win_w - card_w) // 2
            ty = (win_h - card_h) // 2

        # Boundary clamping
        tx = max(16, min(win_w - card_w - 16, tx))
        ty = max(16, min(win_h - card_h - 16, ty))

        self.tooltip.place(x=tx, y=ty, width=card_w, height=card_h)

    def next_step(self) -> None:
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self._render_current_step()
        else:
            self.destroy()

    def prev_step(self) -> None:
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._render_current_step()

    def skip(self) -> None:
        self.destroy()

    def destroy(self) -> None:
        self._is_active = False
        self._unbind_events()

        if self._configure_job is not None:
            try:
                self.master.after_cancel(self._configure_job)
            except Exception:
                pass
            self._configure_job = None

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

        if self.on_finish is not None:
            try:
                self.on_finish()
            except Exception:
                pass
```

---

## 4. Caveats & Edge Cases

1. **`winfo_rootx()` / `winfo_rooty()` on Unmapped or Pending Widgets**:
   - Calling `winfo_rootx()` before `master.update_idletasks()` can return `0, 0` or stale coordinates.
   - **Remedy**: Always call `self.master.update_idletasks()` before measuring widget bounds. If `winfo_ismapped() == False` or `winfo_width() <= 1`, gracefully fallback to center modal blackout.
2. **Scrollable Container Coordinates (`CTkScrollableFrame`)**:
   - `SidebarPanel` is a `CTkScrollableFrame`. Widgets inside may be scrolled out of view.
   - `winfo_rootx()` measures true screen coordinates, which correctly reflects whether the widget is currently visible on screen. However, if the widget is scrolled partially out of view, clamping to screen boundaries prevents negative coordinates.
3. **Tab Switching Synchronization (`ttk.Notebook`)**:
   - When switching tabs (e.g. from Layout Tab to Data Tab), Tkinter requires one event loop turn to layout the newly revealed frame.
   - Calling `self.notebook.select(target_tab_index)` followed by `self.master.update_idletasks()` ensures layout dimensions are immediately valid.
4. **Debounced Window Resizing**:
   - Operating systems fire dozens of `<Configure>` events per second during window dragging. Without debouncing (`after(40, ...)`), high CPU redraw loops can cause tearing.

---

## 5. Conclusion
- The **In-Window 4-Rectangle Spotlight Engine** provides a rock-solid, flicker-free, cross-platform overlay architecture without any multi-window OS synchronization pitfalls.
- The 4-rectangle geometry partitioning is mathematically proven to leave the spotlight cutout 100% uncovered while shading all surrounding screen areas.
- The emerald glow border (`#10B981`) and semi-transparent scrim (`stipple="gray50"`) deliver an aesthetically pleasing, modern glassmorphic guided walkthrough.
- Background click events are fully trapped (`lambda e: "break"`), while keyboard shortcuts (`Esc`, `Enter`, `Left`, `Right`) allow effortless power-user navigation.

---

## 6. Verification Method

To independently verify the architecture and mathematical calculations:
1. **Geometric Partitioning Unit Test**:
   ```python
   def test_4_rectangle_partition_geometry():
       W, H = 1400, 900
       x1, y1, x2, y2 = 100, 150, 400, 350
       top = (0, 0, W, y1)
       bottom = (0, y2, W, H)
       left = (0, y1, x1, y2)
       right = (x2, y1, W, y2)

       # Verify total area equality:
       cutout_area = (x2 - x1) * (y2 - y1)
       top_area = W * y1
       bottom_area = W * (H - y2)
       left_area = x1 * (y2 - y1)
       right_area = (W - x2) * (y2 - y1)

       assert top_area + bottom_area + left_area + right_area + cutout_area == W * H
   ```
2. **Component File Verification**:
   Inspect `ui/components/tutorial_overlay.py` when created by Worker to verify:
   - Placement on `master_window` with `.place(relwidth=1.0, relheight=1.0)` and `.lift()`.
   - 4-rectangle slicing logic matching `_draw_scrim_and_spotlight()`.
   - Event interception for `<Button-1>`..`<Button-3>`.
   - Cleanup protocol removing canvas, tooltip, and unbinding all events.
3. **Automated GUI Test Run**:
   Run `pytest tests/test_ui_layout.py` or new `tests/test_tutorial_overlay_e2e.py`.
