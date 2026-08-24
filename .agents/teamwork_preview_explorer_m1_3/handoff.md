# Handoff Report: Tooltip Card UI & Step Navigation Controller Specification

**Specialist**: Tooltip UI & Navigation Specialist (`teamwork_preview_explorer_m1_3`)  
**Milestone**: Milestone 1 (Interactive Tutorial Overlay Engine)  
**Target File**: `ui/components/tutorial_overlay.py`  
**Date**: 2026-08-19  

---

## 1. Observation

Direct examination of the codebase and project specifications revealed key constraints and integration points:

1. **Host Window Hierarchy (`ui/main_window.py:31-43, 81-186`)**:
   - `SlipPrinterApp` inherits from `ctk.CTk`. Standard window geometry is `min(1400, max(1000, screen_w - 60)) x min(900, max(700, screen_h - 80))` with `minsize(1000, 700)`.
   - Layout is composed of a `ttk.Panedwindow` splitter (`sidebar_width=360`), `SidebarPanel` (left), and `ttk.Notebook` (right tabs: `DataTabPanel`, `LayoutTabPanel`, `HistoryTabPanel`).
   - The tutorial overlay layer must float on top of the root window (`ctk.CTk`), overlaying both the `Panedwindow` and `Notebook` without disrupting their underlying geometry.

2. **Design Tokens & Theme Guidelines (`python-gui-design`, `PROJECT.md:18-22`)**:
   - **Primary Action (CTA)**: Emerald Green (`#10B981`, hover `#059669`) for final step completion (`🎉 Hoàn tất`), Fluent Blue (`#2563EB`, hover `#1D4ED8`) for intermediary steps (`Tiếp tục ▶`).
   - **Secondary / Neutral Actions**: `[◀ Quay lại]` uses subtle gray (`("gray80", "gray30")`), `[Bỏ qua]` uses `fg_color="transparent"` with text `("gray40", "gray60")`.
   - **Card Frame Styling**: Corner radius `14`, border width `2px` (`#10B981` Emerald Glow or `#3B82F6` Fluent Blue), background `("#FFFFFF", "#1E293B")` (or `("gray95", "gray17")`).
   - **Grid Spacing**: 8-point grid spacing (`8px`, `12px`, `16px`, `24px`).

3. **Step Navigation Requirements (`ORIGINAL_REQUEST.md:19-28`, `PROJECT.md:50-69`)**:
   - Must support 4+ steps with seamless transitions (`[◀ Quay lại]`, `[Tiếp tục ▶]`, `[🎉 Hoàn tất]`, `[Bỏ qua]`).
   - Must support keyboard accessibility: `<Return>` / `<Right>` for Next, `<Left>` for Back, `<Escape>` for Skip.
   - Must automatically switch `ttk.Notebook` tabs if the target widget resides on an inactive tab (`target_tab_index`).

4. **Lifecycle & Clean Teardown**:
   - In Tkinter / CustomTkinter, background `after()` timer loops and global root event bindings (`<Configure>`, `<Key>`) will leak or raise `TclError` if destroyed widgets are accessed after dismissal.

---

## 2. Logic Chain & Architecture Design

### A. Component Hierarchy & Layering

```
SlipPrinterApp (ctk.CTk Root Window)
  │
  ├─ [Existing App UI: Splitter, Sidebar, Notebook, Footer]
  │
  └─ InteractiveTutorialOverlay (Placed on Root x=0, y=0, relwidth=1, relheight=1)
       │
       ├─ Overlay Canvas (Scrim background with 4-rectangle cutout & glowing border)
       │
       └─ TooltipCard (ctk.CTkFrame, placed dynamically via .place(x, y), .lift())
            ├─ Header Frame
            │    ├─ Icon + Title Label ("💡 1. Nạp dữ liệu Excel")
            │    └─ Step Badge Frame ("Bước 1 / 4")
            ├─ Separator Frame
            ├─ Body Text Label (Wraplength 320px, description)
            ├─ Micro-UX Shortcut Hint ("⌨ [Enter] Tiếp tục · [←] Quay lại · [Esc] Bỏ qua")
            └─ Action Button Bar
                 ├─ [Bỏ qua (Esc)] (Transparent, Left)
                 ├─ Spacer Frame (Weight 1)
                 ├─ [◀ Quay lại] (Gray, Disabled on Step 0)
                 └─ [Tiếp tục ▶] / [🎉 Hoàn tất] (Blue / Emerald CTA)
```

---

### B. `TooltipCard` UI Specification

- **Class Name**: `TooltipCard(ctk.CTkFrame)`
- **Dimensions**: Fixed width `360px`, dynamic height auto-fitted to content (`~180px - 240px`).
- **Visual Styling**:
  - `corner_radius=14`
  - `border_width=2`
  - `border_color=("#10B981", "#10B981")` (Glowing Emerald border matching the spotlight cutout)
  - `fg_color=("#FFFFFF", "#1E293B")`
- **Internal Layout Grid / Pack**:
  1. **Header Row**:
     - `title_label = ctk.CTkLabel(header, text=step.title, font=ctk.CTkFont(size=15, weight="bold"), anchor="w")`
     - `badge_frame = ctk.CTkFrame(header, corner_radius=8, fg_color=("#E0E7FF", "#1E3A8A"))`
     - `badge_label = ctk.CTkLabel(badge_frame, text=f"Bước {current_index + 1} / {total_steps}", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#3730A3", "#93C5FD"))`
  2. **Separator**:
     - `sep = ctk.CTkFrame(self, height=1, fg_color=("gray85", "gray30"))`
  3. **Body Text**:
     - `body_label = ctk.CTkLabel(self, text=step.description, font=ctk.CTkFont(size=13), wraplength=320, justify="left", text_color=("gray25", "gray80"))`
  4. **Keybinding Hint**:
     - `hint_label = ctk.CTkLabel(self, text="⌨ [Enter] Tiếp tục · [←] Quay lại · [Esc] Bỏ qua", font=ctk.CTkFont(size=10), text_color=("gray50", "gray50"))`
  5. **Action Button Bar**:
     - `skip_btn = ctk.CTkButton(btn_row, text="Bỏ qua", width=70, height=32, fg_color="transparent", hover_color=("gray85", "gray25"), text_color=("gray45", "gray55"), command=controller.skip)`
     - `prev_btn = ctk.CTkButton(btn_row, text="◀ Quay lại", width=85, height=32, fg_color=("gray80", "gray30"), text_color=("black", "white"), hover_color=("gray70", "gray40"), command=controller.prev_step)`
     - `next_btn = ctk.CTkButton(btn_row, text="Tiếp tục ▶", width=100, height=32, font=ctk.CTkFont(size=13, weight="bold"), fg_color="#2563EB", hover_color="#1D4ED8", text_color="white", command=controller.next_step)`
     - When `current_index == total_steps - 1`:
       - `next_btn.configure(text="🎉 Hoàn tất", fg_color="#10B981", hover_color="#059669", width=110)`
     - When `current_index == 0`:
       - `prev_btn.configure(state="disabled", fg_color=("gray90", "gray20"), text_color=("gray60", "gray40"))`

---

### C. Intelligent Placement Algorithm (PlacementEngine)

The placement algorithm calculates the optimal `(x, y)` coordinates for the Tooltip Card relative to the Root window.

#### Geometric Variables:
- Root Window bounds: `W_root = master.winfo_width()`, `H_root = master.winfo_height()`
- Target Spotlight bounds (with padding): `(x1, y1, x2, y2)`
- Spotlight Center: `cx = (x1 + x2) / 2`, `cy = (y1 + y2) / 2`
- Card Dimensions: `w_card = 360`, `h_card = 200` (or `card.winfo_reqheight()`)
- Constants: `GAP = 14` (space between spotlight border and card), `MARGIN = 16` (screen margin)

#### Available Space in 4 Cardinal Directions:
1. **Bottom**: `space_bottom = H_root - (y2 + GAP) - MARGIN`
2. **Top**: `space_top = y1 - GAP - MARGIN`
3. **Right**: `space_right = W_root - (x2 + GAP) - MARGIN`
4. **Left**: `space_left = x1 - GAP - MARGIN`

#### Direction Decision Logic:
```python
def calculate_placement(
    root_w: int,
    root_h: int,
    spotlight_bounds: tuple[int, int, int, int] | None,
    card_w: int = 360,
    card_h: int = 200,
    preferred_position: str = "auto",
    gap: int = 14,
    margin: int = 16,
) -> tuple[int, int]:
    # Fallback: No spotlight or widget hidden -> Center in window
    if spotlight_bounds is None:
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

    # Determine candidate direction
    chosen_pos = preferred_position
    if chosen_pos == "auto":
        # Check standard priority: bottom -> top -> right -> left
        if space_bottom >= card_h:
            chosen_pos = "bottom"
        elif space_top >= card_h:
            chosen_pos = "top"
        elif space_right >= card_w:
            chosen_pos = "right"
        elif space_left >= card_w:
            chosen_pos = "left"
        else:
            # Pick direction with maximum available space
            spaces = {
                "bottom": space_bottom,
                "top": space_top,
                "right": space_right,
                "left": space_left,
            }
            chosen_pos = max(spaces, key=spaces.get)
    else:
        # Preferred position specified, verify if it fits; if not, flip to opposite
        if chosen_pos == "bottom" and space_bottom < card_h:
            chosen_pos = "top" if space_top >= card_h else "right"
        elif chosen_pos == "top" and space_top < card_h:
            chosen_pos = "bottom" if space_bottom >= card_h else "right"
        elif chosen_pos == "right" and space_right < card_w:
            chosen_pos = "left" if space_left >= card_w else "bottom"
        elif chosen_pos == "left" and space_left < card_w:
            chosen_pos = "right" if space_right >= card_w else "bottom"

    # Calculate raw position
    if chosen_pos == "bottom":
        raw_x = cx - (card_w // 2)
        raw_y = y2 + gap
    elif chosen_pos == "top":
        raw_x = cx - (card_w // 2)
        raw_y = y1 - gap - card_h
    elif chosen_pos == "right":
        raw_x = x2 + gap
        raw_y = cy - (card_h // 2)
    elif chosen_pos == "left":
        raw_x = x1 - gap - card_w
        raw_y = cy - (card_h // 2)
    else:
        raw_x = (root_w - card_w) // 2
        raw_y = (root_h - card_h) // 2

    # Clamping against window boundaries
    clamped_x = max(margin, min(raw_x, root_w - card_w - margin))
    clamped_y = max(margin, min(raw_y, root_h - card_h - margin))

    return (clamped_x, clamped_y)
```

---

### D. Step Navigation State Machine & Lifecycle

- **State Attributes**:
  - `_current_step_index: int = 0`
  - `_steps: list[TutorialStep] = []`
  - `_is_active: bool = False`
  - `_is_destroyed: bool = False`
  - `_bind_ids: list[tuple[str, str]] = []`
  - `_resize_timer_id: str | None = None`

- **Navigation Methods**:
  1. `start(start_step_index: int = 0)`:
     - Activates overlay layer, binds keyboard shortcuts, initializes step `start_step_index`.
  2. `next_step()`:
     - If `_current_step_index < len(_steps) - 1`:
       - `_current_step_index += 1`
       - `_render_current_step()`
     - Else:
       - `finish()`
  3. `prev_step()`:
     - If `_current_step_index > 0`:
       - `_current_step_index -= 1`
       - `_render_current_step()`
  4. `skip()`:
     - `dismiss(reason="skip")`
  5. `finish()`:
     - `dismiss(reason="finish")`
     - Invokes `on_finish` callback (which updates `user_settings.json` with `has_seen_tutorial = True`).

---

### E. Keyboard Accessibility & Event Swallowing

To avoid conflicts with background inputs and shortcuts:
1. Bindings are attached to `root` with `add="+"`.
2. Each handler returns `"break"` to swallow the keystroke during tutorial mode:
   - `<Escape>` -> calls `self.skip()`; returns `"break"`
   - `<Return>`, `<KP_Enter>`, `<Right>` -> calls `self.next_step()`; returns `"break"`
   - `<Left>` -> calls `self.prev_step()`; returns `"break"`
3. All registered bind IDs are tracked in `self._bind_ids` and cleanly removed via `root.unbind(seq, func_id)` during destruction.

---

### F. Clean Destruction & Memory Leak Prevention Protocol

```python
def destroy(self) -> None:
    if self._is_destroyed:
        return
    self._is_destroyed = True
    self._is_active = False

    # 1. Cancel pending after() debouncers
    if self._resize_timer_id is not None:
        try:
            self.master.after_cancel(self._resize_timer_id)
        except Exception:
            pass
        self._resize_timer_id = None

    # 2. Unbind all keyboard handlers from root
    for seq, func_id in self._bind_ids:
        try:
            self.master.unbind(seq, func_id)
        except Exception:
            pass
    self._bind_ids.clear()

    # 3. Unbind <Configure> listener from root
    if hasattr(self, "_configure_bind_id") and self._configure_bind_id:
        try:
            self.master.unbind("<Configure>", self._configure_bind_id)
        except Exception:
            pass
        self._configure_bind_id = None

    # 4. Destroy Tooltip Card
    if hasattr(self, "tooltip_card") and self.tooltip_card is not None:
        try:
            self.tooltip_card.destroy()
        except Exception:
            pass
        self.tooltip_card = None

    # 5. Destroy Overlay Canvas
    if hasattr(self, "canvas") and self.canvas is not None:
        try:
            self.canvas.destroy()
        except Exception:
            pass
        self.canvas = None

    # 6. Restore focus to master window
    try:
        self.master.focus_set()
    except Exception:
        pass

    # 7. Destroy container frame if subclassed
    super().destroy()
```

---

## 3. Concrete Code Snippets for Worker Implementation

The following complete and modular code structures are ready for direct inclusion in `ui/components/tutorial_overlay.py`:

```python
# ui/components/tutorial_overlay.py
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


class TooltipCard(ctk.CTkFrame):
    """Floating responsive CTkFrame card presenting tutorial step info and navigation buttons."""

    def __init__(
        self,
        master: tk.Misc,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_skip: Callable[[], None],
        **kwargs,
    ):
        super().__init__(
            master,
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

        # Header: Title & Step Badge
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="💡 Tiêu đề bước",
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

        # Thin Separator
        self.sep = ctk.CTkFrame(self, height=1, fg_color=("gray85", "gray30"))
        self.sep.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))

        # Body Text
        self.body_label = ctk.CTkLabel(
            self,
            text="Nội dung hướng dẫn chi tiết...",
            font=ctk.CTkFont(size=13),
            wraplength=320,
            justify="left",
            text_color=("gray25", "gray85"),
        )
        self.body_label.grid(row=2, column=0, sticky="w", padx=16, pady=(0, 6))

        # Micro-UX Shortcut Hint
        self.hint_label = ctk.CTkLabel(
            self,
            text="⌨ [Enter] Tiếp tục · [←] Quay lại · [Esc] Bỏ qua",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray50"),
        )
        self.hint_label.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        # Action Button Row
        self.btn_row = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 14))
        self.btn_row.grid_columnconfigure(1, weight=1)  # Spacer

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

        # Cluster right
        self.right_btn_frame = ctk.CTkFrame(self.btn_row, fg_color="transparent")
        self.right_btn_frame.grid(row=0, column=2, sticky="e")

        self.prev_btn = ctk.CTkButton(
            self.right_btn_frame,
            text="◀ Quay lại",
            width=85,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=("gray80", "gray30"),
            text_color=("black", "white"),
            hover_color=("gray70", "gray40"),
            command=self.on_prev,
        )
        self.prev_btn.grid(row=0, column=0, padx=(0, 8))

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
        title: str,
        description: str,
        current_index: int,
        total_steps: int,
    ) -> None:
        self.title_label.configure(text=title)
        self.body_label.configure(text=description)
        self.badge_label.configure(text=f"Bước {current_index + 1} / {total_steps}")

        # Update Back button state
        if current_index == 0:
            self.prev_btn.configure(state="disabled", fg_color=("gray90", "gray20"), text_color=("gray60", "gray40"))
        else:
            self.prev_btn.configure(state="normal", fg_color=("gray80", "gray30"), text_color=("black", "white"))

        # Update Next / Finish button styling
        if current_index == total_steps - 1:
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

    CARD_WIDTH = 360
    CARD_HEIGHT = 200
    GAP = 14
    MARGIN = 16

    @classmethod
    def calculate(
        cls,
        root_w: int,
        root_h: int,
        spotlight_bounds: Optional[tuple[int, int, int, int]],
        card_w: int = CARD_WIDTH,
        card_h: int = CARD_HEIGHT,
        preferred_position: str = "auto",
    ) -> tuple[int, int]:
        if not spotlight_bounds:
            return (
                max(cls.MARGIN, (root_w - card_w) // 2),
                max(cls.MARGIN, (root_h - card_h) // 2),
            )

        x1, y1, x2, y2 = spotlight_bounds
        cx = (x1 + x2) // 2
        cy = (y1 + y2) // 2

        space_bottom = root_h - (y2 + cls.GAP) - cls.MARGIN
        space_top = y1 - cls.GAP - cls.MARGIN
        space_right = root_w - (x2 + cls.GAP) - cls.MARGIN
        space_left = x1 - cls.GAP - cls.MARGIN

        pos = preferred_position
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
                spaces = {"bottom": space_bottom, "top": space_top, "right": space_right, "left": space_left}
                pos = max(spaces, key=spaces.get)
        else:
            # Flip if preferred position overflows
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
            raw_y = y2 + cls.GAP
        elif pos == "top":
            raw_x = cx - (card_w // 2)
            raw_y = y1 - cls.GAP - card_h
        elif pos == "right":
            raw_x = x2 + cls.GAP
            raw_y = cy - (card_h // 2)
        elif pos == "left":
            raw_x = x1 - cls.GAP - card_w
            raw_y = cy - (card_h // 2)
        else:
            raw_x = (root_w - card_w) // 2
            raw_y = (root_h - card_h) // 2

        clamped_x = max(cls.MARGIN, min(raw_x, root_w - card_w - cls.MARGIN))
        clamped_y = max(cls.MARGIN, min(raw_y, root_h - card_h - cls.MARGIN))
        return (clamped_x, clamped_y)
```

---

## 4. Caveats

1. **Geometry Mapping Latency**:
   - When switching `ttk.Notebook` tabs programmatically for steps that reside on non-active tabs (e.g. Data Tab vs Layout Tab), `master.update_idletasks()` MUST be called before retrieving widget bounds. Otherwise, `winfo_rootx()` / `winfo_rooty()` will return `0` or stale values.
2. **DPI Awareness & Scaling**:
   - CustomTkinter applies scaling factor `ctk.ThemeManager.theme[...]` or internal DPI scaling. `winfo_width()`, `winfo_height()`, and `winfo_rootx()` return screen pixel units. Relative coordinate math `(widget.winfo_rootx() - master.winfo_rootx())` is self-normalizing and works consistently across high-DPI displays.
3. **Modal Dialogs Interruption**:
   - If the user opens another modal (such as `QRScanDialog` or `messagebox`), the tutorial overlay must remain passive and avoid recalculating until the dialog resolves.

---

## 5. Conclusion

The specifications and code provided herein fulfill all requirements for Milestone 1:
- **Card UI**: Follows modern CustomTkinter design tokens with distinct badges, typography, Emerald glowing borders, and Von Restorff CTAs.
- **Navigation**: Clean step state machine supporting forward, backward, skip, and complete transitions.
- **Placement**: Responsive 4-directional placement algorithm with automatic overflow flipping and boundary clamping.
- **Keybindings**: Accessible shortcuts (`Enter`, `Left`, `Right`, `Esc`) with event swallowing (`return "break"`).
- **Cleanup**: Zero-leak destruction pattern removing all debouncers, keybindings, and canvas artifacts.

---

## 6. Verification Method

To independently verify the implementation, the Worker and QA agents can run the following test commands:

```bash
# 1. Run unit and layout tests
pytest tests/test_ui_layout.py -v

# 2. Run tutorial overlay unit & integration tests
pytest tests/test_tutorial_overlay_e2e.py -v

# 3. Interactive Smoke Test
python -c "
import customtkinter as ctk
from ui.components.tutorial_overlay import TooltipCard, PlacementEngine, TutorialStep

root = ctk.CTk()
root.geometry('1000x700')
card = TooltipCard(root, on_next=lambda: print('Next'), on_prev=lambda: print('Prev'), on_skip=lambda: root.destroy())
card.update_content('Bước 1: Import Excel', 'Chọn file Excel cần nạp dữ liệu vào bảng.', 0, 4)
pos = PlacementEngine.calculate(1000, 700, (100, 100, 300, 150))
card.place(x=pos[0], y=pos[1])
root.after(1000, root.destroy)
root.mainloop()
print('Smoke test successful!')
"
```
