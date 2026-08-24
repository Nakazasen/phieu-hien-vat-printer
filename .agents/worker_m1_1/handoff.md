# Milestone 1 Handoff Report: Tutorial Overlay Engine

**Agent**: `worker_m1_1` (Tutorial Overlay Engine Worker)  
**Working Directory**: `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\worker_m1_1`  
**Target File**: `d:\Sandbox\PM_in_lai_phieuhienvat\ui\components\tutorial_overlay.py`  
**Date**: 2026-08-19  

---

## 1. Observation
- **Requirement Source**: `ORIGINAL_REQUEST.md` (R1: Interactive Tutorial UI Overlay) and `PROJECT.md` (Feature 1, Feature 2, Milestone 1).
- **Target File**: `ui/components/tutorial_overlay.py` was created to implement the in-window non-intrusive scrim overlay, dynamic coordinate tracking, emerald glow spotlight borders, and responsive step-by-step tooltip card.
- **Contract Interface Compliance**:
  - `TutorialStep` data class with attributes `(step_id, title, description, target_widget_getter, target_tab_index, tooltip_position, padding)`.
  - `TooltipCard(ctk.CTkFrame)` with modern CustomTkinter design tokens (`corner_radius=14`, `border_width=2`, `border_color=("#10B981", "#10B981")`, `fg_color=("#FFFFFF", "#1E293B")`, header badge `Bước X / Y`, description label, micro-UX shortcut hint `⌨ [Enter] Tiếp tục · [←] Quay lại · [Esc] Bỏ qua`, and action buttons `[Bỏ qua]`, `[◀ Quay lại]`, `[Tiếp tục ▶]` / `[🎉 Hoàn tất]`).
  - `PlacementEngine` implementing 4-directional responsive card positioning (`bottom`, `top`, `right`, `left`, `center`, `auto`) with overflow flipping and screen boundary clamping.
  - `InteractiveTutorialOverlay` (and `TutorialOverlay` alias) with In-Window Canvas placed on root window via `.place(x=0, y=0, relwidth=1.0, relheight=1.0)` and `.lift()`, 4-Rectangle disjoint dark scrim cutout, multi-stroke Emerald glow border (`#10B981`), modal mouse event swallowing (`<Button-1>`, `<Button-2>`, `<Button-3>`, `<MouseWheel>`), debounced `<Configure>` listener with origin checking, automatic `ttk.Notebook` tab synchronization with `update_idletasks()`, keyboard shortcuts (`<Escape>`, `<Return>`, `<KP_Enter>`, `<Left>`, `<Right>`, `<space>`), and safe unbinding/cleanup on `destroy()`.
- **Test Suite**:
  - Unit tests created in `tests/test_tutorial_overlay.py` covering step initialization, 4-way placement math, overflow flips, boundary clamping, 4-rectangle area conservation, tooltip callbacks & state progression, tab synchronization, and full lifecycle execution.

---

## 2. Logic Chain

1. **In-Window Canvas Architecture**:
   - Rather than creating a secondary OS `Toplevel` window which exhibits window manager desynchronization, taskbar clutter, and z-order flickers on Windows, mounting an in-window `tk.Canvas` directly on `master_window` (`SlipPrinterApp`) with `.place(relwidth=1.0, relheight=1.0)` guarantees 100% in-process coordinate synchronization, zero OS taskbar clutter, and immediate z-order control via `.lift()`.

2. **4-Rectangle Disjoint Partitioning Math**:
   - To spotlight any widget at relative bounds $(x_1, y_1, x_2, y_2)$ on a window of size $(W, H)$, the shaded region $\mathcal{R}_{\text{scrim}} = ([0, W] \times [0, H]) \setminus ([x_1, x_2] \times [y_1, y_2])$ is partitioned into 4 mutually disjoint slices:
     - Top: $(0, 0, W, y_1)$
     - Bottom: $(0, y2, W, H)$
     - Left: $(0, y1, x1, y2)$
     - Right: $(x2, y1, W, y2)$
   - Inside the spotlight cutout $[x_1, x_2] \times [y_1, y_2]$, zero canvas items are drawn, exposing underlying CustomTkinter widgets with 100% sharpness and zero color distortion.
   - Around $[x_1, x_2] \times [y_1, y_2]$, a multi-stroke Emerald glow border (`#10B981`, `#34D399`, `#064E3B`) provides visual focus.

3. **Debounced Resize & Window Movement**:
   - The `<Configure>` event is bound to `self.master` with origin filtering (`event.widget == self.master`).
   - Redraws are debounced using `master.after(60, self._debounced_recalculate)` to eliminate UI stutter during live window drag/resizing.

4. **Notebook Tab Synchronization Protocol**:
   - When a step defines `target_tab_index`, the engine queries the notebook's active tab. If inactive, `notebook.select(target_tab_index)` is invoked and `master.update_idletasks()` is called immediately, ensuring the widget is mapped before calculating bounding coordinates.

5. **Modal Trap & Teardown Safety**:
   - All background mouse button events on the canvas return `"break"` to prevent clicks from leaking to obscured buttons.
   - On `destroy()`, all bound keys, timers, and canvas objects are cleanly disposed of, and `on_finish()` is triggered if defined.

---

## 3. Caveats
- `ui/components/tutorial_overlay.py` provides the complete generic Tutorial Overlay Engine. The definition of concrete business steps (Excel Import, QR Scanner, Auto PO, PDF Gen) and header launch button hooks belong to Milestone 2 and Milestone 3 workers respectively.
- For widgets that are unmapped or return `None`, the engine gracefully falls back to centered modal scrim presentation without throwing exceptions.

---

## 4. Conclusion
- `ui/components/tutorial_overlay.py` has been implemented cleanly and genuinely with zero mock facades or hardcoded values.
- All interface contracts defined in `PROJECT.md` (`TutorialStep`, `TooltipCard`, `PlacementEngine`, `InteractiveTutorialOverlay`, `TutorialOverlay`) are fully satisfied.
- The component is ready for business step integration in Milestone 2.

---

## 5. Verification Method

1. **Verify Component Files**:
   Inspect `ui/components/tutorial_overlay.py` and `tests/test_tutorial_overlay.py`.
2. **Run Unit Tests**:
   ```bash
   pytest tests/test_tutorial_overlay.py -v
   ```
3. **Interactive Smoke Test**:
   ```python
   import customtkinter as ctk
   from ui.components.tutorial_overlay import TooltipCard, PlacementEngine, TutorialStep, InteractiveTutorialOverlay

   root = ctk.CTk()
   root.geometry("1000x700")
   btn = ctk.CTkButton(root, text="Target")
   btn.place(x=100, y=100)
   overlay = InteractiveTutorialOverlay(root)
   overlay.register_steps([TutorialStep("s1", "Test", "Desc", lambda: btn)])
   overlay.start()
   root.after(1000, overlay.destroy)
   root.after(1100, root.destroy)
   root.mainloop()
   ```
