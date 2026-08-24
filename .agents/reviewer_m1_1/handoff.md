# Milestone 1 Code & Architecture Review Report: Tutorial Overlay Engine

**Reviewer**: `reviewer_m1_1` (Teamwork Reviewer & Adversarial Critic)  
**Target Milestone**: Milestone 1 (Tutorial Overlay Engine & Highlighting Mechanism)  
**Target File**: `d:\Sandbox\PM_in_lai_phieuhienvat\ui\components\tutorial_overlay.py`  
**Test Suite**: `d:\Sandbox\PM_in_lai_phieuhienvat\tests\test_tutorial_overlay.py`  
**Verdict**: **APPROVE**  
**Date**: 2026-08-19  

---

## 1. Observation

1. **Interface Contract Compliance (`PROJECT.md` Lines 51–69)**:
   - `TutorialStep` (`ui/components/tutorial_overlay.py` lines 15–26) is implemented as a `@dataclass` with the exact required fields: `step_id: str`, `title: str`, `description: str`, `target_widget_getter: Callable[[], Optional[tk.Widget | ctk.CTkBaseClass]]`, `target_tab_index: Optional[int] = None`, `tooltip_position: str = "auto"`, and an additional ergonomic `padding: int = 6` parameter with default value.
   - `InteractiveTutorialOverlay` (`ui/components/tutorial_overlay.py` lines 411–857) implements all required public interface methods:
     - `__init__(master_window, on_finish=None, notebook=None)`
     - `register_steps(steps: Sequence[TutorialStep]) -> None`
     - `start(start_step_index: int = 0) -> None`
     - `next_step() -> None`
     - `prev_step() -> None`
     - `skip() -> None`
     - `destroy() -> None`
     - `TutorialOverlay = InteractiveTutorialOverlay` alias exported at line 856 for backwards compatibility.

2. **Core Architectural Elements**:
   - **In-Window Canvas Mount** (`ui/components/tutorial_overlay.py` lines 490–513): Mounted directly onto `master_window` with `place(x=0, y=0, relwidth=1.0, relheight=1.0)` and lifted to top z-order (`.lift()`). Intercepts all background mouse events (`<Button-1>`, `<Button-2>`, `<Button-3>`, `<MouseWheel>`, etc.) returning `"break"` to establish an airtight modal focus trap.
   - **4-Rectangle Disjoint Partitioning Math** (`ui/components/tutorial_overlay.py` lines 671–748):
     - Top slice: `(0, 0, win_w, y1)`
     - Bottom slice: `(0, y2, win_w, win_h)`
     - Left slice: `(0, y1, x1, y2)`
     - Right slice: `(x2, y1, win_w, y2)`
     - Mathematical area conservation: $\text{Top} + \text{Bottom} + \text{Left} + \text{Right} + \text{Cutout} = W \times H$.
   - **Emerald Glow Spotlight Border** (`ui/components/tutorial_overlay.py` lines 749–780): Draws triple-layered glow borders using `#064E3B`, `#34D399`, and `#10B981` around the spotlight cutout.
   - **Responsive Tooltip Card** (`ui/components/tutorial_overlay.py` lines 28–230): `TooltipCard(ctk.CTkFrame)` with `corner_radius=14`, `border_width=2`, `border_color=("#10B981", "#10B981")`, `fg_color=("#FFFFFF", "#1E293B")`, step counter badge `Bước X / Y`, micro-UX shortcut hint, Back/Next/Skip/Finish action buttons, and automatic label configuration.
   - **Placement & Clamping Engine** (`ui/components/tutorial_overlay.py` lines 231–314): 4-way direction auto-fitting (`bottom` -> `top` -> `right` -> `left`), overflow flipping, and screen boundary clamping with margin.
   - **Tab Synchronization** (`ui/components/tutorial_overlay.py` lines 365–409): Auto-selects `target_tab_index` on `ttk.Notebook` and calls `update_idletasks()` to flush geometry before bounds calculation.
   - **Resize Debouncing & Lifecycle Teardown** (`ui/components/tutorial_overlay.py` lines 561–593, 831–853): Listens to `<Configure>` on root with origin filtering (`event.widget == self.master`), debounces redraws via `after(60, ...)`, and disposes all bound keys, timers, and canvas objects on `destroy()`.

3. **Integrity & Code Quality Audit**:
   - **Integrity Check**: No hardcoded test values, no fake stubs, no facade implementations, no external bypasses detected.
   - **Type Annotations**: Comprehensive type hinting across all classes and functions (`from __future__ import annotations`, `dataclass`, `Callable`, `Optional`, `Sequence`, `Any`).
   - **Error Handling**: All coordinate extraction and geometry querying methods are fail-safe (`try...except` returning fallback modal placement without crashing Tkinter mainloop).

4. **Test Suite Analysis (`tests/test_tutorial_overlay.py`)**:
   - Contains 12 dedicated unit tests spanning:
     - Step initialization and custom property assignment (`TestTutorialStep`).
     - Center fallback, 4-direction fitting, overflow flipping, and boundary clamping (`TestPlacementEngine`).
     - Mathematical area conservation of 4-rectangle disjoint partitioning (`TestGeometryAndPartitioning`).
     - Tooltip card rendering, callback triggers, and dynamic text/badge updates (`TestTooltipCard`).
     - Overlay lifecycle, forward/backward navigation, skip teardown, and notebook tab switching (`TestInteractiveTutorialOverlay`).

---

## 2. Logic Chain

1. **Correctness & Contract Adherence**:
   - *Observation 1* establishes that `TutorialStep` and `InteractiveTutorialOverlay` expose all methods, types, and signatures required by `PROJECT.md`.
   - *Observation 2* verifies that the 4-rectangle scrim geometry leaves a transparent spotlight aperture over the target widget while dimming the surrounding window area.
   - Therefore, the implementation fully satisfies the specifications of Milestone 1.

2. **Adversarial & Edge Case Resilience**:
   - *Assumption Tested: Missing or unmapped widget.*  
     When `target_widget_getter` returns `None` or an unmapped widget, `GeometryHelper.get_relative_bounds` returns `None`. `_draw_scrim_and_spotlight` draws a full scrim blackout rectangle and centers the tooltip card safely.
   - *Assumption Tested: Live window resize flutter.*  
     Debounced `<Configure>` listener with a 60ms timer and event origin filtering (`event.widget == self.master`) prevents layout thrashing during active window drag.
   - *Assumption Tested: Background click leakage.*  
     Canvas binds all mouse buttons (`<Button-1>`, `<Button-2>`, `<Button-3>`, `<MouseWheel>`, etc.) returning `"break"`, creating a complete modal focus trap.
   - *Assumption Tested: Multi-destroy idempotency.*  
     `destroy()` checks `if self._is_destroyed: return`, cancelling pending after-timers and unbinding event IDs cleanly without throwing Tcl/Tk exceptions.

3. **Code Quality & Maintainability**:
   - Separation of concerns between `TutorialStep` (data model), `TooltipCard` (view component), `PlacementEngine` (geometry math), `GeometryHelper` / `TabSyncHelper` (utilities), and `InteractiveTutorialOverlay` (controller engine) complies with Clean Code standards.
   - Clean CustomTkinter aesthetic matching the emerald/slate dark-mode palette.

---

## 3. Caveats

- Milestone 1 implements the generic overlay engine and spotlight mechanics. The concrete 4-step business script (Excel Import, QR Scanner, Auto PO, PDF Generation) and UI Header trigger button will be integrated in Milestones 2 and 3 as scheduled.

---

## 4. Conclusion

- **Verdict**: **APPROVE**
- `ui/components/tutorial_overlay.py` is robust, cleanly written, fully typed, mathematically sound, and completely satisfies the Milestone 1 contract.

---

## 5. Verification Method

To independently verify:
1. **Source Inspection**:
   - `ui/components/tutorial_overlay.py`
   - `tests/test_tutorial_overlay.py`
2. **Execute Pytest Suite**:
   ```bash
   pytest tests/test_tutorial_overlay.py -v
   ```
3. **Interactive Smoke Test**:
   ```python
   import customtkinter as ctk
   from ui.components.tutorial_overlay import TutorialStep, InteractiveTutorialOverlay

   root = ctk.CTk()
   root.geometry("1000x700")
   btn = ctk.CTkButton(root, text="Target Widget")
   btn.place(x=150, y=150, width=140, height=40)

   overlay = InteractiveTutorialOverlay(root)
   overlay.register_steps([
       TutorialStep("step_1", "Test Title", "Test Description", lambda: btn)
   ])
   overlay.start()
   root.after(1000, overlay.destroy)
   root.after(1100, root.destroy)
   root.mainloop()
   ```
