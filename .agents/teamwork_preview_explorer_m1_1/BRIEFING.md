# BRIEFING — 2026-08-19T10:27:00Z

## Mission
Analyze and formulate the exact architecture, mathematical algorithms, and implementation plan for the In-Window Canvas Scrim and 4-Rectangle Spotlight Cutout Engine in ui/components/tutorial_overlay.py.

## 🔒 My Identity
- Archetype: teamwork_preview_explorer
- Roles: Overlay Canvas Architecture Specialist
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_1
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: M1 (Tutorial Overlay Engine & Highlighting Mechanism)

## 🔒 Key Constraints
- Read-only investigation — do NOT modify application source code
- Formulate complete, concrete code snippets and technical recommendations for the Worker
- Produce 5-Component handoff report in handoff.md

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: 2026-08-19T10:27:00Z

## Investigation State
- **Explored paths**:
  - `ORIGINAL_REQUEST.md`: Core requirements R1 (Interactive Tutorial UI Overlay), R2 (4 core steps), R3 (Trigger button & persistence).
  - `PROJECT.md`: System architecture, interface contracts (`TutorialStep`, `InteractiveTutorialOverlay`), milestone decomposition.
  - `ui/main_window.py`: `SlipPrinterApp` root window setup, ttk.Notebook tabs, Splitter, SidebarPanel.
  - `ui/components/sidebar.py`: Sidebar buttons (Import Excel, QR Scan, Generate PDF, Open PDF).
  - `tests/conftest.py`: Tkinter testing fixtures, test isolation.
- **Key findings**:
  - In-Window Overlay vs Toplevel: In-Window overlay eliminates Win32 window manager focus/flashing/z-order desync and transparentcolor click-through bugs.
  - 4-Rectangle Geometry: Mathematically partitions $[0, W] \times [0, H] \setminus [x1, x2] \times [y1, y2]$ into 4 non-overlapping regions (Top, Bottom, Left, Right) to keep cutout 100% transparent and visible.
  - Dual-Implementation Strategy: Single `tk.Canvas` with vector rectangles + stipple vs 4-slice `CTkFrame` scrims + rounded highlight frame. 4-slice Frame / Canvas approach ensures true see-through clarity for CustomTkinter widgets.
  - Emerald Glow Accent: `#10B981` matching app's primary action color theme, with rounded anti-aliased border.
  - Click Interception: Binding `<Button-1>`..`<Button-3>` with `lambda e: "break"` on scrim surfaces prevents interaction with obscured widgets.
- **Unexplored areas**: None for M1 Overlay Canvas scope.

## Key Decisions Made
- Use composite scrim architecture with coordinate clamping and debounced `<Configure>` re-anchoring.
- Provide full production-ready implementation snippets for `InteractiveTutorialOverlay` and `TutorialStep` in `handoff.md`.

## Artifact Index
- `d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_explorer_m1_1\handoff.md` — 5-Component Handoff Report for Worker
