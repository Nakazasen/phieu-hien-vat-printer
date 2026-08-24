# Remediation Report: Tkinter Canvas Z-Order Lift Defect Strategy

**Explorer**: Explorer 1 (Milestone 1 Iteration 2)  
**Target Component**: `ui/components/tutorial_overlay.py`  
**Defect Classification**: Fatal Runtime `TclError` due to method shadowing in `tkinter.Canvas`

---

## 1. Observation

### Exact File Locations & Verbatim Code
In `ui/components/tutorial_overlay.py`:

1. **Location 1 — `_build_overlay()`** (line 498):
   ```python
   # Line 490-498
   self.canvas = tk.Canvas(
       self.master,
       highlightthickness=0,
       borderwidth=0,
       bg=self.SCRIM_COLOR,
       cursor="arrow",
   )
   self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
   self.canvas.lift()
   ```

2. **Location 2 — `_render_current_step()`** (line 668):
   ```python
   # Line 667-669
   # Ensure overlay and tooltip stay on top
   self.canvas.lift()
   self.tooltip.lift()
   ```

### Verbatim Runtime Error
When `InteractiveTutorialOverlay.start()` is invoked, calling `_build_overlay()` or `_render_current_step()` immediately crashes with the following exception:

```
_tkinter.TclError: wrong # args: should be ".!canvas raise tagOrId ?aboveThis?"
```

**Traceback Snippet (from Python 3.13 / `tkinter/__init__.py:3142`):**
```
  File "ui/components/tutorial_overlay.py", line 480, in start
    self._build_overlay()
  File "ui/components/tutorial_overlay.py", line 498, in _build_overlay
    self.canvas.lift()
  File "C:\Python313\Lib\tkinter\__init__.py", line 3142, in tag_raise
    self.tk.call((self._w, 'raise') + args)
_tkinter.TclError: wrong # args: should be ".!canvas raise tagOrId ?aboveThis?"
```

### Forensic Evidence Cross-References
- **Auditor Report** (`.agents/auditor_m1_1/handoff.md:29-35`): Identified `self.canvas.lift()` as Defect 1 causing 4/16 test failures in `tests/test_tutorial_overlay.py`.
- **Challenger 2 Report** (`.agents/challenger_m1_2/handoff.md:7-32`): Confirmed 14/15 tests in `tests/test_challenger_m1_overlay_stress.py` failed due to this exact TclError.
- **Empirical Bug Reproduction Test** (`tests/test_challenger1_empirical_stress.py:277-291`):
  Demonstrated that calling `canvas.lift()` throws `TclError`, whereas calling `tk.Misc.tkraise(canvas)` or `tk.Misc.lift(canvas)` succeeds without error.

---

## 2. Logic Chain

1. **Tkinter Inheritance & Method Shadowing**:
   - In Python's standard `tkinter`, base widgets inherit from `tkinter.Misc`, which defines the window Z-order management methods:
     ```python
     # In tkinter.Misc:
     def tkraise(self, aboveThis=None):
         """Raise this window in the stacking order."""
         self.tk.call('raise', self._w, aboveThis)
     lift = tkraise
     ```
     This executes the Tcl command `raise <windowPath> ?aboveThis?`, which instructs the Tk window manager to elevate the widget above its siblings in the window stacking order.

   - However, `tkinter.Canvas` manages internal drawing items (rectangles, polygons, text items, tags). To manage the display order of these items, `tkinter.Canvas` implements `tag_raise`:
     ```python
     # In tkinter.Canvas:
     def tag_raise(self, *args):
         """Raise an item TAGORID given in ARGS (optional above another item)."""
         self.tk.call((self._w, 'raise') + args)
     lift = tkraise = tag_raise
     ```

2. **Root Cause of `TclError`**:
   - In `tkinter.Canvas`, `Canvas.lift` is aliased directly to `tag_raise`.
   - When `self.canvas.lift()` is called with zero arguments (`args = ()`), it evaluates to:
     ```python
     self.tk.call((self._w, 'raise') + ())
     # Sends: ".!canvas raise" to Tcl
     ```
   - In Tcl/Tk Canvas widget syntax, the command `.<canvas_widget> raise` requires at least one argument: the item ID or tag name to raise (`pathName raise tagOrId ?aboveThis?`).
   - Consequently, the Tcl interpreter rejects the call with `_tkinter.TclError: wrong # args: should be ".!canvas raise tagOrId ?aboveThis?"`.

3. **Window Stacking vs Canvas Item Stacking**:
   - The developer's intent at lines 498 and 668 is to raise the **Canvas widget itself** above all other sibling widgets on `self.master` (the root window, splitters, sidebars, tabs).
   - Calling the instance method `self.canvas.lift()` incorrectly invokes the **canvas item** method instead of the **window widget** method.

4. **Remediation Mechanism**:
   - By calling the unbound base method on `tkinter.Misc`:
     ```python
     tk.Misc.lift(self.canvas)
     # or
     tk.Misc.tkraise(self.canvas)
     ```
     Python dispatches directly to `Misc.tkraise`, which invokes:
     ```python
     self.canvas.tk.call('raise', self.canvas._w, None)
     ```
   - This sends the Tcl window command `raise .!canvas`, correctly raising the entire canvas widget to the top of the window's Z-order hierarchy.
   - Note on `TooltipCard`: `self.tooltip` is an instance of `TooltipCard` (inheriting from `ctk.CTkFrame` -> `tk.Frame` -> `tk.Misc`). Because `Frame` does not override `lift`, calling `self.tooltip.lift()` or `tk.Misc.lift(self.tooltip)` works correctly. Using `tk.Misc.lift(self.tooltip)` or `self.tooltip.lift()` is safe; using `tk.Misc.lift` across both provides clean consistency.

---

## 3. Caveats

1. **Read-Only Scope**: Explorer 1 operates under a read-only investigation mandate. No modifications have been made directly to `ui/components/tutorial_overlay.py`.
2. **Coupled Milestone 1 Defects**: Resolving `self.canvas.lift()` is necessary but not the sole fix for Milestone 1 test passing. The implementer must also:
   - Remove `width` and `height` keyword arguments from `self.tooltip.place(...)` at lines 660-665 (pass `width` and `height` in `TooltipCard` constructor instead).
   - Initialize `self.prev_btn` with `state="disabled"` in `TooltipCard._build_ui()` at line 131.

---

## 4. Conclusion

### Exact Remediation Strategy
Replace both occurrences of `self.canvas.lift()` in `ui/components/tutorial_overlay.py` with `tk.Misc.lift(self.canvas)`.

### Code Replacement Diffs

#### Diff 1: Line 498 (`_build_overlay`)
**Target File**: `ui/components/tutorial_overlay.py`  
**Location**: Line 490–500

```python
<<<< PREVIOUS (Defective)
        self.canvas = tk.Canvas(
            self.master,
            highlightthickness=0,
            borderwidth=0,
            bg=self.SCRIM_COLOR,
            cursor="arrow",
        )
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        self.canvas.lift()
==== REPLACEMENT (Fixed)
        self.canvas = tk.Canvas(
            self.master,
            highlightthickness=0,
            borderwidth=0,
            bg=self.SCRIM_COLOR,
            cursor="arrow",
        )
        self.canvas.place(x=0, y=0, relwidth=1.0, relheight=1.0)
        tk.Misc.lift(self.canvas)
>>>>
```

#### Diff 2: Line 668 (`_render_current_step`)
**Target File**: `ui/components/tutorial_overlay.py`  
**Location**: Line 667–670

```python
<<<< PREVIOUS (Defective)
        # Ensure overlay and tooltip stay on top
        self.canvas.lift()
        self.tooltip.lift()
==== REPLACEMENT (Fixed)
        # Ensure overlay and tooltip stay on top
        tk.Misc.lift(self.canvas)
        tk.Misc.lift(self.tooltip)
>>>>
```

---

## 5. Verification Method

To independently verify the fix:

1. **Run Empirical Bug Test**:
   ```powershell
   pytest tests/test_challenger1_empirical_stress.py -k test_canvas_lift_tcl_error_bug_identification -v
   ```
   *Expected*: Passes, demonstrating `tk.Misc.tkraise`/`tk.Misc.lift` succeeds without TclError.

2. **Run Challenger Stress Suite**:
   ```powershell
   pytest tests/test_challenger_m1_overlay_stress.py -v
   ```
   *Expected*: All 20 tests pass with 0 failures once `tk.Misc.lift(self.canvas)` and `TooltipCard` place parameters are applied.

3. **Run Milestone 1 Component Suite**:
   ```powershell
   pytest tests/test_tutorial_overlay.py -v
   ```
   *Expected*: All 16 tests pass with 0 failures.

### Invalidation Conditions
- If calling `self.canvas.lift()` is retained, `InteractiveTutorialOverlay.start()` will fail 100% of the time with `_tkinter.TclError`.
- If `self.canvas.tkraise()` is used without verifying that `Canvas.tkraise` is unshadowed in the target Python runtime, `tag_raise` aliasing may still trigger `TclError`. `tk.Misc.lift(self.canvas)` is the definitive, guaranteed fix.
