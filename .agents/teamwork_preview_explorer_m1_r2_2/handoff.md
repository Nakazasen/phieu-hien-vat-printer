# Remediation Strategy: CustomTkinter `place()` Constraints & `TooltipCard` Initial State

## 1. Observation

Direct empirical observations from source code inspections, CustomTkinter runtime internals, and test suite executions:

### A. CustomTkinter `CTkBaseClass.place()` Restriction & TooltipCard Failure
1. **Source Code in `ui/components/tutorial_overlay.py` (lines 660–665)**:
   ```python
   self.tooltip.place(
       x=pos_x,
       y=pos_y,
       width=PlacementEngine.CARD_WIDTH,
       height=PlacementEngine.CARD_HEIGHT,
   )
   ```
2. **CustomTkinter Internal Implementation** (`customtkinter/windows/widgets/core_widget_classes/ctk_base_class.py:270-275`):
   ```python
   def place(self, **kwargs):
       """
       Place a widget in the parent widget...
       """
       if "width" in kwargs or "height" in kwargs:
           raise ValueError("'width' and 'height' arguments must be passed to the constructor of the widget, not the place method")
       self._last_geometry_manager_call = {"function": super().place, "kwargs": kwargs}
       return super().place(**self._apply_argument_scaling(kwargs))
   ```
3. **Runtime Execution Result**:
   Calling `self.tooltip.place(..., width=..., height=...)` raises:
   ```
   ValueError: 'width' and 'height' arguments must be passed to the constructor of the widget, not the place method
   ```
4. **Test Fixtures in `tests/test_tutorial_overlay.py` (lines 234–237)**:
   ```python
   btn1 = ctk.CTkButton(tk_root, text="Target 1")
   btn1.place(x=50, y=50, width=120, height=36)
   btn2 = ctk.CTkButton(tk_root, text="Target 2")
   btn2.place(x=300, y=100, width=150, height=40)
   ```
   Command: `python -m pytest tests/test_tutorial_overlay.py -k test_overlay_lifecycle_and_navigation`  
   Verbatim failure:
   ```
   tests\test_tutorial_overlay.py:235: in test_overlay_lifecycle_and_navigation
       btn1.place(x=50, y=50, width=120, height=36)
   C:\...\site-packages\customtkinter\windows\widgets\core_widget_classes\ctk_base_class.py:272: in place
       raise ValueError("'width' and 'height' arguments must be passed to the constructor of the widget, not the place method")
   E   ValueError: 'width' and 'height' arguments must be passed to the constructor of the widget, not the place method
   ```

### B. `TooltipCard` Initial State Defect (`prev_btn` normal vs disabled)
1. **Source Code in `ui/components/tutorial_overlay.py` (lines 131–142)**:
   ```python
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
   ```
2. **Initial State Comparison with `update_content()` (lines 201–206)**:
   ```python
   if current_index == 0:
       self.prev_btn.configure(
           state="disabled",
           fg_color=("gray90", "gray20"),
           text_color=("gray60", "gray40"),
       )
   ```
3. **Test Execution Result**:
   Command: `python -m pytest tests/test_tutorial_overlay.py -k test_tooltip_card_creation_and_callbacks`  
   Verbatim failure:
   ```
   tests\test_tutorial_overlay.py:193: in test_tooltip_card_creation_and_callbacks
       assert card.prev_btn.cget("state") == "disabled"
   E   AssertionError: assert 'normal' == 'disabled'
   E     - disabled
   E     + normal
   ```

---

## 2. Logic Chain

1. **CustomTkinter Geometry & Canvas Architecture**:
   - Unlike standard Tkinter widgets which rely entirely on Tcl/Tk's C-level window geometry manager for dimensions, `CustomTkinter` widgets (`CTkFrame`, `CTkButton`, `CTkLabel`, etc.) use an internal Canvas rendering engine with High-DPI scaling, corner radii smoothing, border strokes, and dark/light color transitions.
   - The internal dimensions of a CTk widget are stored in `self._current_width` and `self._current_height`, which are initialized during `__init__(..., width=..., height=...)` and updated through `.configure(width=..., height=...)`.
   - CustomTkinter's `CTkBaseClass.place()` explicitly disallows passing `width` and `height` parameters, raising a `ValueError` because passing geometry dimensions to Tk's `.place()` without routing through CTk's constructor or `configure()` would circumvent CTk's argument scaling and redraw pipeline (`_draw()`).

2. **Root Cause of Overlay Crash**:
   - `TooltipCard` inherits from `customtkinter.CTkFrame`.
   - In `ui/components/tutorial_overlay.py:660-665`, `_render_current_step()` attempts to pass `width=PlacementEngine.CARD_WIDTH, height=PlacementEngine.CARD_HEIGHT` to `self.tooltip.place(...)`.
   - This directly triggers the `ValueError` exception on any invocation of `.start()` or step rendering.

3. **Root Cause of `prev_btn` Assertion Failure**:
   - In a step-by-step walkthrough, the initial state is Step 1 (index 0).
   - In Step 1, navigating backwards is invalid, so the "◀ Quay lại" button must be disabled immediately upon construction.
   - In `TooltipCard._build_ui()`, `self.prev_btn` was instantiated without `state="disabled"` (defaulting to `state="normal"`).
   - Although `update_content()` disables `prev_btn` when called with `current_index=0`, when `TooltipCard` is instantiated in isolation (as in unit testing) or before `update_content()` is triggered, `self.prev_btn.cget("state")` evaluates to `"normal"`.

4. **Remediation Strategy**:
   - Set default dimensions (`width=360, height=200`) in `TooltipCard.__init__` and pass `width=PlacementEngine.CARD_WIDTH, height=PlacementEngine.CARD_HEIGHT` when `TooltipCard` is instantiated in `InteractiveTutorialOverlay._build_overlay()`.
   - In `InteractiveTutorialOverlay._render_current_step()`, invoke `self.tooltip.place(x=pos_x, y=pos_y)` using strictly positional arguments.
   - In `TooltipCard._build_ui()`, initialize `self.prev_btn` with `state="disabled"`, `fg_color=("gray90", "gray20")`, and `text_color=("gray60", "gray40")`.
   - In `tests/test_tutorial_overlay.py`, update dummy `ctk.CTkButton` fixtures to pass `width` and `height` in their constructor calls rather than via `.place()`.

---

## 3. Caveats

1. **CustomTkinter vs Tkinter/ttk Widgets**:
   - Standard Tkinter widgets (e.g. `tk.Canvas`, `ttk.Notebook`) still support `width` and `height` in `.place()`. Only widgets inheriting from `ctk.CTkBaseClass` (`CTkFrame`, `CTkButton`, `CTkLabel`, etc.) enforce this restriction.
2. **Order of Class Definitions**:
   - `TooltipCard` is defined at line 28 of `ui/components/tutorial_overlay.py`, whereas `PlacementEngine` is defined at line 231.
   - If setting default parameter values in `TooltipCard.__init__`, use numeric literals `width: int = 360, height: int = 200` (or `width: int = PlacementEngine.CARD_WIDTH` if `PlacementEngine` is placed before `TooltipCard`) to avoid Python `NameError` at module import time.
3. **Dynamic Resize**:
   - If the tooltip card size ever needs dynamic adjustment in future features, call `self.tooltip.configure(width=new_w, height=new_h)` before calling `self.tooltip.place(x=pos_x, y=pos_y)`.

---

## 4. Conclusion & Exact Code Replacements

### Remediation A: `TooltipCard.__init__` & `_build_ui()`
**Target File**: `ui/components/tutorial_overlay.py` (lines 31–46, 131–142)

```python
<<<<
    def __init__(
        self,
        master: tk.Widget | ctk.CTk,
        on_next: Callable[[], None],
        on_prev: Callable[[], None],
        on_skip: Callable[[], None],
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            corner_radius=14,
            border_width=2,
            border_color=("#10B981", "#10B981"),
            fg_color=("#FFFFFF", "#1E293B"),
            **kwargs,
        )
====
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
>>>>
```

```python
<<<<
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
====
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
>>>>
```

---

### Remediation B: `InteractiveTutorialOverlay._build_overlay()`
**Target File**: `ui/components/tutorial_overlay.py` (lines 515–521)

```python
<<<<
        # 2. Tooltip Card
        self.tooltip = TooltipCard(
            self.master,
            on_next=self.next_step,
            on_prev=self.prev_step,
            on_skip=self.skip,
        )
====
        # 2. Tooltip Card
        self.tooltip = TooltipCard(
            self.master,
            width=PlacementEngine.CARD_WIDTH,
            height=PlacementEngine.CARD_HEIGHT,
            on_next=self.next_step,
            on_prev=self.prev_step,
            on_skip=self.skip,
        )
>>>>
```

---

### Remediation C: `InteractiveTutorialOverlay._render_current_step()`
**Target File**: `ui/components/tutorial_overlay.py` (lines 660–665)

```python
<<<<
        self.tooltip.place(
            x=pos_x,
            y=pos_y,
            width=PlacementEngine.CARD_WIDTH,
            height=PlacementEngine.CARD_HEIGHT,
        )
====
        self.tooltip.place(
            x=pos_x,
            y=pos_y,
        )
>>>>
```

---

### Remediation D: Test Fixtures in `tests/test_tutorial_overlay.py`
**Target File**: `tests/test_tutorial_overlay.py` (lines 234–238)

```python
<<<<
        # Create dummy target widgets
        btn1 = ctk.CTkButton(tk_root, text="Target 1")
        btn1.place(x=50, y=50, width=120, height=36)
        btn2 = ctk.CTkButton(tk_root, text="Target 2")
        btn2.place(x=300, y=100, width=150, height=40)
====
        # Create dummy target widgets
        btn1 = ctk.CTkButton(tk_root, text="Target 1", width=120, height=36)
        btn1.place(x=50, y=50)
        btn2 = ctk.CTkButton(tk_root, text="Target 2", width=150, height=40)
        btn2.place(x=300, y=100)
>>>>
```

---

## 5. Verification Method

### Independent Test Execution Commands:
1. **Component Test Suite**:
   ```powershell
   python -m pytest tests/test_tutorial_overlay.py -v
   ```
2. **Specific Unit Test for TooltipCard Button State**:
   ```powershell
   python -m pytest tests/test_tutorial_overlay.py::TestTooltipCard::test_tooltip_card_creation_and_callbacks -v
   ```
3. **Specific Lifecycle Navigation Test**:
   ```powershell
   python -m pytest tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_lifecycle_and_navigation -v
   ```
4. **Challenger Empirical Stress Test Suite**:
   ```powershell
   python -m pytest tests/test_challenger_m1_overlay_stress.py -v
   ```

### Invalidation Conditions:
- The remediation is confirmed valid if all 16 tests in `tests/test_tutorial_overlay.py` and all 20 tests in `tests/test_challenger_m1_overlay_stress.py` pass cleanly with 0 `ValueError` and 0 `AssertionError` (combined with `tk.Misc.lift(self.canvas)` fix for `Canvas.lift`).
- If any CustomTkinter widget is called with `.place(..., width=..., height=...)`, `ValueError` will be thrown immediately and the test will fail.
