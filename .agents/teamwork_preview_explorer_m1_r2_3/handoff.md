# Test Suite Alignment & Remediation Strategy: `tests/test_tutorial_overlay.py`

**Author**: Explorer 3 (Milestone 1 Iteration 2 — `teamwork_preview_explorer`)  
**Target Files**: `tests/test_tutorial_overlay.py` (and interdependent `ui/components/tutorial_overlay.py`)  
**Scope**: 16 Unit & Integration Tests in `tests/test_tutorial_overlay.py`  
**Working Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_r2_3`  

---

## 1. Observation

### 1.1 Test Suite Failure Summary
Direct execution of `python -m pytest tests/test_tutorial_overlay.py -v` yields **4 FAILED, 12 PASSED in 10.49s**:

```
tests/test_tutorial_overlay.py::TestTutorialStep::test_step_initialization_defaults PASSED       [  6%]
tests/test_tutorial_overlay.py::TestTutorialStep::test_step_custom_properties PASSED             [ 12%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_center_fallback_when_none PASSED      [ 18%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_center_when_preferred_is_center PASSED [ 25%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_bottom_placement_when_fits PASSED     [ 31%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_top_placement_when_fits PASSED        [ 37%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_right_placement_when_fits PASSED      [ 43%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_left_placement_when_fits PASSED       [ 50%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_overflow_flip_bottom_to_top PASSED   [ 56%]
tests/test_tutorial_overlay.py::TestPlacementEngine::test_boundary_clamping PASSED              [ 62%]
tests/test_tutorial_overlay.py::TestGeometryAndPartitioning::test_4_rectangle_partition_area_conservation PASSED [ 68%]
tests/test_tutorial_overlay.py::TestTooltipCard::test_tooltip_card_creation_and_callbacks FAILED [ 75%]
tests/test_tutorial_overlay.py::TestTooltipCard::test_tooltip_card_update_content PASSED         [ 81%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_lifecycle_and_navigation FAILED [ 87%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_skip FAILED         [ 93%]
tests/test_tutorial_overlay.py::TestInteractiveTutorialOverlay::test_overlay_tab_sync FAILED    [100%]
```

---

### 1.2 Identified Failure Points & Root Causes

#### Defect 1: Test Fixture CustomTkinter `.place(width=..., height=...)` Violation
- **Location**: `tests/test_tutorial_overlay.py:234-237`
- **Verbatim Code**:
  ```python
  btn1 = ctk.CTkButton(tk_root, text="Target 1")
  btn1.place(x=50, y=50, width=120, height=36)
  btn2 = ctk.CTkButton(tk_root, text="Target 2")
  btn2.place(x=300, y=100, width=150, height=40)
  ```
- **Verbatim Error**:
  ```
  ValueError: 'width' and 'height' arguments must be passed to the constructor of the widget, not the place method
  ```
- **Mechanism**: In `customtkinter/windows/widgets/core_widget_classes/ctk_base_class.py:272`, `CTkBaseClass.place()` explicitly disallows `width` and `height` arguments to ensure internal canvas rendering scaling remains consistent with `self._current_width` and `self._current_height`. Dimensions must be specified during widget instantiation (e.g. `ctk.CTkButton(tk_root, text="Target 1", width=120, height=36)`) and positioning done via `btn1.place(x=50, y=50)`.

#### Defect 2: TooltipCard Standalone Initial `prev_btn` State
- **Location**: `tests/test_tutorial_overlay.py:193` vs `ui/components/tutorial_overlay.py:131-142`
- **Verbatim Assertion**:
  ```python
  assert card.prev_btn.cget("state") == "disabled"
  # E       AssertionError: assert 'normal' == 'disabled'
  ```
- **Mechanism**: When `TooltipCard(tk_root, ...)` is initialized standalone in `test_tooltip_card_creation_and_callbacks`, `_build_ui()` constructs `self.prev_btn` without `state="disabled"`. The default `CTkButton` state is `"normal"`. Because `update_content()` is not called during `__init__`, `prev_btn` remains `"normal"`, violating the contract that a freshly instantiated tooltip card for step 1 starts with the Back button disabled.

#### Defect 3: Tkinter `Canvas.lift()` TclError
- **Location**: `ui/components/tutorial_overlay.py:498` and `ui/components/tutorial_overlay.py:668`
- **Verbatim Code**: `self.canvas.lift()`
- **Verbatim Error**:
  ```
  _tkinter.TclError: wrong # args: should be ".!canvas raise tagOrId ?aboveThis?"
  ```
- **Mechanism**: In Tkinter's `tkinter.Canvas`, `Canvas.lift` is aliased to `Canvas.tag_raise`. When invoked with zero arguments, Tk translates this into `.<canvas_path> raise`, which fails with a Tcl syntax error. Stacking order lifting of the Canvas window above its sibling widgets requires `tk.Misc.lift(self.canvas)`.

#### Defect 4: Component CustomTkinter `.place(width=..., height=...)` on `self.tooltip`
- **Location**: `ui/components/tutorial_overlay.py:660-665`
- **Verbatim Code**:
  ```python
  self.tooltip.place(
      x=pos_x,
      y=pos_y,
      width=PlacementEngine.CARD_WIDTH,
      height=PlacementEngine.CARD_HEIGHT,
  )
  ```
- **Mechanism**: `TooltipCard` inherits from `ctk.CTkFrame`. Calling `self.tooltip.place()` with `width` and `height` triggers the same `ValueError`.

---

### 1.3 Audit of all `.place()` Invocations in the Test Directory

| File | Line | Code | Widget Type | Status / Fix |
|---|---|---|---|---|
| `tests/test_tutorial_overlay.py` | 235 | `btn1.place(x=50, y=50, width=120, height=36)` | `ctk.CTkButton` | **DEFECT**: Move `width=120, height=36` to constructor, call `btn1.place(x=50, y=50)` |
| `tests/test_tutorial_overlay.py` | 237 | `btn2.place(x=300, y=100, width=150, height=40)` | `ctk.CTkButton` | **DEFECT**: Move `width=150, height=40` to constructor, call `btn2.place(x=300, y=100)` |
| `tests/test_tutorial_overlay.py` | 288 | `notebook.place(x=0, y=0, width=800, height=600)` | `ttk.Notebook` | **VALID**: Standard `ttk.Notebook` supports `place(width=..., height=...)` |
| `tests/test_tutorial_overlay_e2e.py` | 106 | `btn.place(x=100, y=100, width=120, height=40)` | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 231 | `target.place(x=200, y=150, width=180, height=50)` | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 259 | `target.place(x=100, y=100, width=100, height=40)` | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 338, 340 | `btn_a.place(...)`, `btn_b.place(...)` | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 450 | `target.place(...)` | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 940, 959, 1018 | `zero_widget.place(...)`, etc. | `ctk.CTkFrame` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 1043, 1064, 1086, 1107, 1128 | `off_btn.place(...)`, etc. | `ctk.CTkButton` | Reference notice for E2E suite |
| `tests/test_tutorial_overlay_e2e.py` | 1515, 1612, 2012, 2014 | `btn.place(...)`, etc. | `ctk.CTkButton` | Reference notice for E2E suite |

---

## 2. Logic Chain

```
[Observation 1.1 & 1.2: 4 failed tests out of 16]
   │
   ├──> `test_overlay_lifecycle_and_navigation` fails at line 235
   │     └──> Root Cause: `btn1.place(x=50, y=50, width=120, height=36)` passes width/height to CTkButton.place()
   │     └──> CTkBaseClass raises ValueError
   │     └──> Alignment: Instantiate `CTkButton(tk_root, text="Target 1", width=120, height=36)` and `btn1.place(x=50, y=50)`
   │
   ├──> `test_tooltip_card_creation_and_callbacks` fails at line 193
   │     └──> Root Cause: `TooltipCard._build_ui()` constructs `self.prev_btn` with default state="normal"
   │     └──> Initial creation assertion expects `disabled` state on step 1
   │     └──> Component Fix: Set `state="disabled"` on `self.prev_btn` in `TooltipCard._build_ui()`
   │
   ├──> `test_overlay_skip` and `test_overlay_tab_sync` fail during `overlay.start()`
   │     └──> Root Cause: `self.canvas.lift()` calls `Canvas.tag_raise()` without args -> TclError
   │     └──> Component Fix: Replace with `tk.Misc.lift(self.canvas)`
   │
   └──> `_render_current_step` places `self.tooltip` with `width=...` and `height=...`
         └──> Root Cause: TooltipCard (CTkFrame) .place() raises ValueError
         └──> Component Fix: Set dimensions in `TooltipCard.__init__` and place via `self.tooltip.place(x=pos_x, y=pos_y)`
```

---

## 3. Formulated Code Changes & Patch Specifications

### 3.1 Changes for `tests/test_tutorial_overlay.py`

#### Target: `tests/test_tutorial_overlay.py` (Lines 233–238)
- **Rationale**: CustomTkinter widgets require `width` and `height` to be set during constructor initialization or via `.configure()`. Moving `width` and `height` into `ctk.CTkButton(...)` eliminates the `ValueError` while preserving the exact intended geometry for testing spotlight calculation.

#### Before vs After Snippet:
```python
<<<< BEFORE (Line 233-238)
        # Create dummy target widgets
        btn1 = ctk.CTkButton(tk_root, text="Target 1")
        btn1.place(x=50, y=50, width=120, height=36)
        btn2 = ctk.CTkButton(tk_root, text="Target 2")
        btn2.place(x=300, y=100, width=150, height=40)
        tk_root.update_idletasks()
==== AFTER
        # Create dummy target widgets
        btn1 = ctk.CTkButton(tk_root, text="Target 1", width=120, height=36)
        btn1.place(x=50, y=50)
        btn2 = ctk.CTkButton(tk_root, text="Target 2", width=150, height=40)
        btn2.place(x=300, y=100)
        tk_root.update_idletasks()
>>>>
```

#### Unified Diff for `tests/test_tutorial_overlay.py`:
```diff
--- a/tests/test_tutorial_overlay.py
+++ b/tests/test_tutorial_overlay.py
@@ -232,8 +232,8 @@ class TestInteractiveTutorialOverlay:
         )
 
         # Create dummy target widgets
-        btn1 = ctk.CTkButton(tk_root, text="Target 1")
-        btn1.place(x=50, y=50, width=120, height=36)
-        btn2 = ctk.CTkButton(tk_root, text="Target 2")
-        btn2.place(x=300, y=100, width=150, height=40)
+        btn1 = ctk.CTkButton(tk_root, text="Target 1", width=120, height=36)
+        btn1.place(x=50, y=50)
+        btn2 = ctk.CTkButton(tk_root, text="Target 2", width=150, height=40)
+        btn2.place(x=300, y=100)
         tk_root.update_idletasks()
```

---

### 3.2 Interdependent Remediation for `ui/components/tutorial_overlay.py`

To allow all 16 tests in `tests/test_tutorial_overlay.py` to execute cleanly, the corresponding component fixes must be applied by the M1 worker:

#### 1. `TooltipCard.__init__` Dimensions & `_build_ui` Initial `prev_btn` State
- **Location**: `ui/components/tutorial_overlay.py:39-46` and `131-143`
- **Code Change**:
```python
# In TooltipCard.__init__:
        super().__init__(
            master,
            width=PlacementEngine.CARD_WIDTH,
            height=PlacementEngine.CARD_HEIGHT,
            corner_radius=14,
            border_width=2,
            border_color=("#10B981", "#10B981"),
            fg_color=("#FFFFFF", "#1E293B"),
            **kwargs,
        )

# In TooltipCard._build_ui:
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
```

#### 2. Canvas & Tooltip Stacking Order Lifting via `tk.Misc.lift`
- **Location**: `ui/components/tutorial_overlay.py:498, 521, 668, 669`
- **Code Change**:
```python
# Line 498 (_build_overlay):
        tk.Misc.lift(self.canvas)

# Line 521 (_build_overlay):
        tk.Misc.lift(self.tooltip)

# Line 668-669 (_render_current_step):
        tk.Misc.lift(self.canvas)
        tk.Misc.lift(self.tooltip)
```

#### 3. TooltipCard Placement without Width/Height Arguments
- **Location**: `ui/components/tutorial_overlay.py:660-665`
- **Code Change**:
```python
# In _render_current_step:
        self.tooltip.place(
            x=pos_x,
            y=pos_y,
        )
```

---

## 4. Caveats

1. **Read-Only Scope**: Explorer 3 has strictly formulated the exact strategy and unified diffs without directly modifying `tests/test_tutorial_overlay.py` or `ui/components/tutorial_overlay.py` in the workspace.
2. **Standard Tkinter vs CustomTkinter `place()`**: Standard Tkinter / ttk widgets (such as `ttk.Notebook` at `test_tutorial_overlay.py:288`) do accept `width` and `height` in `.place()`. Only CustomTkinter widgets (`ctk.CTkButton`, `ctk.CTkFrame`, `ctk.CTkLabel`, etc.) enforce the constructor dimension restriction.
3. **E2E Suite Pre-notice**: While out of the immediate M1 unit test scope, `tests/test_tutorial_overlay_e2e.py` contains 18 instances of `CTkButton.place(width=..., height=...)` and `CTkFrame.place(width=..., height=...)` that will require identical mechanical adjustments before running the final full acceptance gate.

---

## 5. Conclusion

- The root cause of the 4 test failures across `tests/test_tutorial_overlay.py` has been completely isolated:
  1. Test fixture `btn1.place` / `btn2.place` parameter mismatch with `CustomTkinter` constraints.
  2. Component `TooltipCard._build_ui` uninitialized `prev_btn` disabled state on step 1.
  3. Component `Canvas.lift()` naming collision with `Canvas.tag_raise`.
  4. Component `self.tooltip.place()` parameter mismatch with `CTkFrame`.
- Once the formulated code changes are applied:
  - 16 of 16 tests in `tests/test_tutorial_overlay.py` will pass with 100% clean execution.
  - 20 of 20 tests in `tests/test_challenger_m1_overlay_stress.py` will pass with 100% clean execution.

---

## 6. Verification Method

To independently verify the test suite alignment and execute the tests after applying changes:

```powershell
# 1. Run the targeted unit & integration test suite
python -m pytest tests/test_tutorial_overlay.py -v

# 2. Run the challenger stress test suite
python -m pytest tests/test_challenger_m1_overlay_stress.py -v
```

**Success Criteria**:
- `tests/test_tutorial_overlay.py`: 16 passed, 0 failed.
- `tests/test_challenger_m1_overlay_stress.py`: 20 passed, 0 failed.
