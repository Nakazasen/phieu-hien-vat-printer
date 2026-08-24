# Project: Interactive Tutorial (UI Overlay) and User Guide

## Architecture
The Interactive Tutorial feature provides a non-intrusive, native in-window spotlight overlay and step-by-step walkthrough across the core workflows of the `InPhieuHienVat` application.

```
┌────────────────────────────────────────────────────────────────────────┐
│ SlipPrinterApp (CustomTkinter Root Window)                             │
│  ├─ Header: [Summary/Status] ... [💡 Hướng dẫn (Amber)] [Theme] [Check]│
│  ├─ Splitter:                                                          │
│  │   ├─ SidebarPanel (Excel Import, QR Scanner, Generate PDF, Open PDF) │
│  │   └─ Notebook:                                                      │
│  │       ├─ DataTabPanel (Form Input, Auto PO, Treeview, Preview)      │
│  │       ├─ LayoutTabPanel (D-Pad, Coordinate Config)                  │
│  │       └─ HistoryTabPanel (PO Registry KPI, Search, EDI History)     │
│  └─ Footer (Progress Bar, Log Box)                                     │
│                                                                        │
│  [Dynamic Tutorial Overlay Layer] (Placed on root, z-lifted)           │
│   ├── In-Window Canvas (4-Rectangle Scrim Spotlight Cutout)            │
│   ├── Target Widget Highlight Border (Glow Emerald #10B981)            │
│   └── CTkFrame Tooltip Card ([Quay lại] [Tiếp tục] [Bỏ qua])          │
└────────────────────────────────────────────────────────────────────────┘
```

- **Persistence Layer**: `%LOCALAPPDATA%\InPhieuHienVatData\user_settings.json` stores user preferences including `has_seen_tutorial` and `auto_suggest_tutorial`.
- **Tutorial Engine**: `ui/components/tutorial_overlay.py` implements `TutorialOverlay` and `TutorialStep` with automatic coordinate tracking, `<Configure>` debounced re-anchoring, DPI scaling awareness, tab switching, and cleanup.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Overlay Scrim & Spotlight Engine | In-Window Canvas 4-Rectangle cutout with glowing highlight border, non-blocking mainloop | M1 | Survey / Spec |
| 2 | Tooltip Card Component | Floating responsive `CTkFrame` card with title, body, step counter, [Back], [Next], [Skip/Finish] buttons | M1 | Survey / Spec |
| 3 | Window Resize & DPI Handling | `<Configure>` listener for dynamic spotlight and tooltip re-anchoring on window resize/move | M1 | Spec Miner |
| 4 | Step 1: Excel Import Script | Highlights Sidebar Excel field & Import button, explains required columns and duplicate check | M2 | ORIGINAL_REQUEST R2.1 |
| 5 | Step 2: QR Scanner Script | Highlights QR button on Sidebar/DataTab, explains 3 modes (Phân tách, Hoàn kho, Bóc tách) | M2 | ORIGINAL_REQUEST R2.2 |
| 6 | Step 3: Auto PO Script | Auto-switches to DataTab, highlights Form & Add button, explains `11YYMMDDNN` auto-increment | M2 | ORIGINAL_REQUEST R2.3 |
| 7 | Step 4: PDF Generation Script | Highlights Generate PDF button & Preview Frame, explains 4 slips / A4 page & printing | M2 | ORIGINAL_REQUEST R2.4 |
| 8 | Header Trigger Button | `💡 Hướng dẫn` button on Header bar (#F59E0B Amber) for manual tutorial launch | M3 | ORIGINAL_REQUEST R3 |
| 9 | Persistence & First-Launch Prompt | `user_settings.json` persistence for `has_seen_tutorial` and first-launch auto-prompt dialog | M3 | ORIGINAL_REQUEST R3 |
| 10 | E2E & Unit Test Verification | Comprehensive automated test suite for overlay math, step transitions, persistence, and cleanup | Final Milestone | ORIGINAL_REQUEST Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Tutorial Overlay Engine & Highlighting Mechanism | `ui/components/tutorial_overlay.py` (Canvas Scrim, Spotlight math, Tooltip Card, Event binding & cleanup) | none | DONE |
| 2 | Tutorial Script & Business Flow Integration | Define 4 core business steps, wire up widget accessors in `SidebarPanel`, `DataTabPanel`, and `AppController` | M1 | DONE |
| 3 | UI Trigger Button, Persistence & First-Launch Prompt | Add `💡 Hướng dẫn` to Header in `main_window.py`, persist `has_seen_tutorial` in `user_settings.json`, prompt on first start | M1, M2 | DONE |
| Final | 100% E2E Test Suite & Adversarial Coverage Hardening | Pass all Tiers 1-4 tests from E2E Testing Track, then execute Tier 5 adversarial stress tests | M1, M2, M3, TEST_READY | DONE |

## Interface Contracts
### `ui.components.tutorial_overlay` ↔ `ui.main_window.SlipPrinterApp`
```python
class TutorialStep:
    step_id: str
    title: str
    description: str
    target_widget_getter: Callable[[], Optional[tk.Widget]]  # lambda returning widget
    target_tab_index: Optional[int] = None  # Notebook tab index to select if needed
    tooltip_position: str = "auto"  # "auto", "bottom", "top", "left", "right"

class InteractiveTutorialOverlay:
    def __init__(self, master_window: tk.Tk | ctk.CTk, on_finish: Optional[Callable[[], None]] = None): ...
    def register_steps(self, steps: list[TutorialStep]) -> None: ...
    def start(self, start_step_index: int = 0) -> None: ...
    def next_step(self) -> None: ...
    def prev_step(self) -> None: ...
    def skip(self) -> None: ...
    def destroy(self) -> None: ...
```

### `ui.main_window.SlipPrinterApp` ↔ `user_settings.json`
```json
{
  "appearance_mode": "System",
  "has_seen_tutorial": false,
  "auto_suggest_tutorial": true
}
```

## Code Layout
- `ui/components/tutorial_overlay.py`: Overlay Canvas, Spotlight Cutout, Tooltip Frame, Step Controller (Owner: M1 Worker)
- `ui/components/sidebar.py`: Named widget accessors for Excel import, QR Scan, and PDF Generate buttons (Owner: M2 Worker)
- `ui/components/data_tab.py`: Named widget accessors for Form, Add button, Preview frame (Owner: M2 Worker)
- `ui/main_window.py`: Header tutorial button, first-launch hook, user settings loading/saving (Owner: M3 Worker)
- `tests/test_tutorial_overlay_e2e.py`: Opaque-box E2E test suite (Owner: E2E Testing Track)
