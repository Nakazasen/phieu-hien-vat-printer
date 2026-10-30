# Project: InPhiếuHiệnVật (Kyocera Slip Printer)

## Architecture

The `InPhieuHienVat` application consists of two primary architectural subsystems:
1. **Interactive UI & Tutorial Overlay Subsystem**
2. **EDI Slip Print & Layout Pipeline Subsystem**

### 1. Interactive UI & Tutorial Overlay Subsystem
Provides a non-intrusive, native in-window spotlight overlay and step-by-step walkthrough across the core workflows of the application.

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

### 2. EDI Slip Print & Layout Pipeline Subsystem
Generates production-grade multi-paper PDF documents with 100% original scale EDI slips, dual 2D QR + 1D Barcode Code 39, and blade cut clearances (A4: 6 slips/sheet with 5.0mm col gap, 2.32mm row gap; Letter: 4 slips/sheet with 5.0mm col & row gaps).

```
┌────────────────────────────────────────────────────────────────────────┐
│ SlipPrinterEngine (core/slip_printer_engine.py)                        │
│                                                                        │
│  [1. Overlay PDF Generator (ReportLab Landscape A4 Canvas)]            │
│   ├── Text Fields: PO, PO Detail, Part Code, Name, Qty, Box, Rev, Lot  │
│   ├── 2D QR Code Generator: qr_122 (122c) & qr_full (129c)             │
│   └── 1D Barcode Generator: Code 39 (Standard39, barWidth=0.65,        │
│       barHeight=28.0, checksum=0, record.item_code[:10], no text)      │
│                                                                        │
│  [2. Template Merge Layer (PyPDF2 & PyMuPDF / fitz)]                   │
│   └── Merge Overlay Buffer with template.pdf phôi chuẩn                │
│                                                                        │
│  [3. Multi-Paper Page Composer (A4 6-Slips / Letter 4-Slips Support)]  │
│   ├── Crop EDI Region: EDI_TEMPLATE_CROP (563.64, 3.96, 836.76, 280.20)│
│   ├── Paper Dimensions: A4 (595.28×841.89 pt) / Letter (612.00×792.00 pt)│
│   ├── 100% Unscaled Geometry: Destination box 273.12×276.24 pt         │
│   ├── Grid & Clearance Gaps:                                           │
│   │   • A4 (6 slips, 2×3): Col gap 17.30mm (49.035 pt), Row gap 2.32mm│
│   │     (6.584 pt), Margins X=0.0 pt, Y=0.0 pt (tối đa hóa khe dao cắt)│
│   │   • Letter (4 slips, 2×2): Col gap 5.0mm (14.17 pt), Row gap 5.0mm│
│   │     (14.17 pt), Margins X=25.80 pt, Y=112.68 pt                    │
│   │   • Centered Cut Lines: Midline X & horizontal gap dashed guidelines│
│   └── Page Ceiling Formula: A4=ceil(N/6), Letter=ceil(N/4)             │
└────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Overlay Scrim & Spotlight Engine | In-Window Canvas 4-Rectangle cutout with glowing highlight border, non-blocking mainloop | M1 | Survey / Spec |
| 2 | Tooltip Card Component | Floating responsive `CTkFrame` card with title, body, step counter, [Back], [Next], [Skip/Finish] buttons | M1 | Survey / Spec |
| 3 | Window Resize & DPI Handling | `<Configure>` listener for dynamic spotlight and tooltip re-anchoring on window resize/move | M1 | Spec Miner |
| 4 | Step 1: Excel Import Script | Highlights Sidebar Excel field & Import button, explains required columns and duplicate check | M2 | ORIGINAL_REQUEST R2.1 |
| 5 | Step 2: QR Scanner Script | Highlights QR button on Sidebar/DataTab, explains 3 modes (Phân tách, Hoàn kho, Bóc tách) | M2 | ORIGINAL_REQUEST R2.2 |
| 6 | Step 3: Auto PO Script | Auto-switches to DataTab, highlights Form & Add button, explains `11YYMMDDNN` auto-increment | M2 | ORIGINAL_REQUEST R2.3 |
| 7 | Step 4: PDF Generation Script | Highlights Generate PDF button & Preview Frame, explains printing process | M2 | ORIGINAL_REQUEST R2.4 |
| 8 | Header Trigger Button | `💡 Hướng dẫn` button on Header bar (#F59E0B Amber) for manual tutorial launch | M3 | ORIGINAL_REQUEST R3 |
| 9 | Persistence & First-Launch Prompt | `user_settings.json` persistence for `has_seen_tutorial` and first-launch auto-prompt dialog | M3 | ORIGINAL_REQUEST R3 |
| 10 | E2E & Unit Test Verification | Comprehensive automated test suite for overlay math, step transitions, persistence, and cleanup | Final Milestone | ORIGINAL_REQUEST Criteria |
| 11 | 1D Barcode Code 39 on EDI Slip | ReportLab Code 39 (`Standard39`, checksum=0, barWidth=0.65, barHeight=28.0) encoding first 10 chars of `item_code` (`record.item_code[:10]`) with `humanReadable=False` placed above QR code | R1 | ORIGINAL_REQUEST Follow-up R1 |
| 12 | 1D Barcode Layout Config & D-Pad Control | Configured in `layout_config.json` (`barcode_positions`), enumerated in `list_layout_items()`, adjustable via D-Pad nudge and 0.05-step resize | R1 | ORIGINAL_REQUEST Follow-up R1 |
| 13 | 6-Slips per A4 Page Grid Layout | Upgraded from legacy 4 slips to 6 slips / A4 page (`EDI_COLUMNS=2, EDI_ROWS=3, EDI_PER_A4_PAGE=6`) | R2 | ORIGINAL_REQUEST Follow-up R2 |
| 14 | Destination Box Geometry & Margins on Portrait A4 | 100% original scale destination box (273.12 pt × 276.24 pt), upgraded in R5 to 5.0mm col gap & 2.32mm row gap | R2/R5 | ORIGINAL_REQUEST Follow-up R2 & R5 |
| 15 | Ceiling Pagination Formula | Output page count $\lceil N / 6 \rceil$ on A4 and $\lceil N / 4 \rceil$ on Letter via `calculate_a4_page_count()` | R2/R5 | ORIGINAL_REQUEST Follow-up R2 & R5 |
| 16 | Live Preview with 1D Barcode | `generate_preview_image` renders 1D barcode in real time on the Data tab canvas | R1 | ORIGINAL_REQUEST Follow-up R1 |
| 17 | Kaizen Report Update | Updated `docs/BAO_CAO_KAIZEN_IN_PHIEU_HIEN_VAT.md` with 6-slip packing metrics (83.3% paper reduction) and 1D laser scanning | R3 | ORIGINAL_REQUEST Follow-up R3 |
| 18 | Automated Test Suite for Barcode 1D & 6-Slips | Dedicated test suite `tests/test_barcode_1d_and_6slips.py` validating 1D barcode, pagination, geometry, and full regression pass | R4 | ORIGINAL_REQUEST Follow-up R4 |
| 19 | Dual Paper Size Selection (A4 / Letter) | Sidebar Segmented Control for A4/Letter selection, persisted in `user_settings.json` (`paper_size`), dynamic paper size routing in PDF pipeline | R5 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 20 | Blade Cut Clearance Margin (4.5mm - 5.0mm) | 5.0 mm (14.17 pt) inter-slip gaps with dashed cut guidelines down gap centers for guillotine paper cutter alignment | R5 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 21 | Duplicate-Aware PDF Export | Preflight registered PO/detail/sub/Box combinations and duplicates in the current list; explain red rows and let the user export only new unique rows without deleting data | R6 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 22 | UI/UX Pro Max Card Grouping & Spacing | Sidebar structured into 3 distinct visual card containers with standard 8/16/24px spacing scale | R7 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 23 | Live Metrics Chip & Empty State on DataTab | Live counter chip displaying `X tem · Dự kiến: Y trang [A4/Letter]` and contextual guidance placeholder for empty data table | R7 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 24 | Modal & Table Keyboard Ergonomics | Escape key to dismiss LetterWarningDialog, Return key triggers primary safe action, Delete key deletes selected row in Treeview | R7 | ORIGINAL_REQUEST Follow-up 2026-09-23 |
| 25 | Vietnamese UI & Error Messages | User-facing labels, instructions, status text, and error details use Vietnamese; OS/library exception text is translated to actionable guidance | R7 | ORIGINAL_REQUEST Follow-up 2026-09-23 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Tutorial Overlay Engine & Highlighting Mechanism | `ui/components/tutorial_overlay.py` (Canvas Scrim, Spotlight math, Tooltip Card, Event binding & cleanup) | none | DONE |
| 2 | Tutorial Script & Business Flow Integration | Define 4 core business steps, wire up widget accessors in `SidebarPanel`, `DataTabPanel`, and `AppController` | M1 | DONE |
| 3 | UI Trigger Button, Persistence & First-Launch Prompt | Add `💡 Hướng dẫn` to Header in `main_window.py`, persist `has_seen_tutorial` in `user_settings.json`, prompt on first start | M1, M2 | DONE |
| Final | 100% E2E Test Suite & Adversarial Coverage Hardening | Pass all Tiers 1-4 tests from E2E Testing Track, then execute Tier 5 adversarial stress tests | M1, M2, M3, TEST_READY | DONE |
| R1 | 1D Barcode Code 39 Integration & Layout Config | Code 39 encoding 10 chars, `humanReadable=False`, `barcode_positions` in `layout_config.json`, D-Pad interaction, Live Canvas Preview | none | DONE |
| R2 | 6-Slips per A4 Page Layout & Pagination (Initial) | 2x3 grid, 100% scale (273.12 × 276.24 pt) (Superseded by Milestone R5 Option 2 dual-paper layout with blade cut clearance gaps) | none | DONE |
| R3 | Spec Enrichment (`PROJECT.md`) & Kaizen Report Update | Direct update to `PROJECT.md` and `docs/BAO_CAO_KAIZEN_IN_PHIEU_HIEN_VAT.md` (paper savings recalculation, XNHH laser scan) | R1, R2 | DONE |
| R4 | Comprehensive Test Suite & Regression Verification | Implement `tests/test_barcode_1d_and_6slips.py`, verify 100% test pass on complete test suite | R1, R2, R3 | DONE |
| R5 | Dual Paper Support & Blade Cut Clearance Gaps (Option 2: 100% Unscaled) | A4: 6 slips (5.0mm col gap, 2.32mm row gap); Letter: 4 slips (5.0mm col & row gaps); LetterWarningDialog with visual diagram; 100% unscaled scale | R1, R2, R4 | DONE |
| R6 | Clear Duplicate Feedback Before PDF Export | Count previously exported and within-list duplicate rows; offer localized “export new rows only” or cancel; preserve all rows; retain SQLite uniqueness as the final guard for concurrent workstations | Existing PO registry and Data tab | DONE |
| R7 | UI/UX Pro Max Industrial Polish & Ergonomics Upgrade | Visual card grouping in Sidebar, live metrics chip & empty state in DataTab, keyboard accessibility, and Vietnamese user-facing UI/error copy | R5, R6 | DONE |

## Interface Contracts

### UI/UX Pro Max Design System Tokens & Ergonomics Contract
- **Color Palette (Industrial Minimalist)**:
  * Primary Action: `#10B981` (Emerald Green, Von Restorff effect for "Tạo PDF" and Add record).
  * Brand & Accent: `#2563EB` (Industrial Royal Blue for table updates and manual PO actions).
  * Warning & Tutorial: `#F59E0B` (Amber for Letter warning modal and Tutorial button).
  * Neutral Surface / Cards: Light mode `gray90` / Dark mode `gray17` with subtle `corner_radius=10`.
- **Keyboard Ergonomics**:
  * `LetterWarningDialog`: `<Escape>` calls `_on_cancel_clicked`, `<Return>` activates default action, initial focus set to cancel button.
  * `DataTabPanel`: `<Delete>` key bound on `preview_tree` to delete selected record, form entries normalize input on `<FocusOut>`.
  * **Vietnamese UI copy**: User-facing labels, guidance, status text, and error details are Vietnamese. Translate operating-system and library exceptions into short actionable Vietnamese messages; preserve Vietnamese validation details. Keep standard file formats, identifiers, and printed template field names (PDF, Excel, QR, PO, Rev, `PACKAGE QTY`, etc.) unchanged.

### Duplicate-Aware PDF Export
- Before PDF generation, validate the records and compare each non-empty PO combination `(po, po_detail, po_sub, box)` with the PO registry and earlier rows in the current list.
- Export each new combination once. Previously registered combinations and later occurrences of combinations already seen in the current list are skipped.
- If some rows are skipped, show their counts and offer **Chỉ xuất tem mới** or **Hủy**. Never remove or edit rows in the user's list as part of this flow.
- If no new rows remain, explain that no PDF was created and leave the list intact.
- Keep the SQLite unique constraint as the final concurrency guard. If another workstation registers a combination after preflight, show a clear message and let the user retry.
- Rows already registered or repeated in the current list remain highlighted red; the table explains the highlight.

### `layout_config.json` (Barcode Positions Contract)
```json
{
  "barcode_positions": {
    "barcode_item_code": {
      "label": "Mã vạch 1D linh kiện (Code 39)",
      "field": "item_code",
      "x": 711,
      "y": 162,
      "width": 0.65,
      "height": 28.0,
      "barWidth": 0.65,
      "barHeight": 28.0,
      "checksum": 0,
      "humanReadable": false
    }
  }
}
```

### `core.slip_printer_engine` (Layout Item Accessors & Geometry Contract)
```python
def list_layout_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Enumerate all layout items including QR codes, 1D barcodes (kind='barcode'), and text positions."""
    ...

def update_layout_item(
    config: dict[str, Any],
    item_id: str,
    *,
    x: float,
    y: float,
    width: float | None = None,
    height: float | None = None,
) -> dict[str, Any]:
    """Update position and dimensions of QR or barcode items (updating both width/barWidth and height/barHeight)."""
    ...

# Dual Paper Layout Contract (Option 2: 100% Unscaled Original Geometry)
PAPER_CONFIGS = {
    "A4": {
        "width": 595.28,      # 210.0 mm
        "height": 841.89,     # 297.0 mm
        "columns": 2,
        "rows": 3,
        "per_page": 6,
        "scale": 1.0,         # 100% unscaled (never shrunk)
        "label_w": 273.12,    # 96.35 mm
        "label_h": 276.24,    # 97.45 mm
        "left_margin": 0.0,   # 0 mm (giảm viền xung quanh về 0)
        "top_margin": 0.0,    # 0 mm (giảm viền xung quanh về 0)
        "col_gap": 49.035,    # 17.30 mm tối đa hóa khe hở giữa 2 cột cho dao cắt
        "row_gap": 6.584,     # 2.32 mm tối đa hóa khe hở giữa 3 hàng trên A4
        "midline_x": 297.64,  # Exact A4 Center Line
    },
    "Letter": {
        "width": 612.00,      # 215.9 mm
        "height": 792.00,     # 279.4 mm
        "columns": 2,
        "rows": 2,
        "per_page": 4,
        "scale": 1.0,         # 100% unscaled (never shrunk)
        "label_w": 273.12,    # 96.35 mm
        "label_h": 276.24,    # 97.45 mm
        "left_margin": 25.795, # 9.10 mm
        "top_margin": 112.675, # 39.75 mm (rộng rãi, an toàn tuyệt đối khỏi kẹp giấy)
        "col_gap": 14.17,     # 5.0 mm blade cut clearance gap
        "row_gap": 14.17,     # 5.0 mm blade cut clearance gap
        "midline_x": 306.00,  # Exact Letter Center Line
    }
}

def calculate_a4_page_count(record_count: int, paper_size: str = "A4") -> int:
    """Calculate the number of pages required: ceil(N / 6) on A4, ceil(N / 4) on Letter."""
    ...
```

> [!WARNING]
> **Phân tích kỹ thuật về vùng không in được (Hardware Non-Printable Margins) trên khổ A4:**
> - Chiều dài giấy A4 là $297.0\text{ mm}$, trong khi $3$ hàng tem $100\%$ không co hình chiếm $3 \times 97.45\text{ mm} = 292.35\text{ mm}$. Khoảng thừa chiều dài của cả trang A4 chỉ còn vỏn vẹn $4.65\text{ mm}$.
> - Bố cục A4 hiện tại phân bổ toàn bộ $4.65\text{ mm}$ này vào $2$ khe hở hàng ($2.32\text{ mm}$ mỗi khe), khiến lề trên và lề dưới bằng $0\text{ mm}$.
> - Các máy in laser văn phòng thông thường có vùng kẹp giấy không in được (gripper margin) từ $3.5\text{ mm} - 5.0\text{ mm}$ ở mép giấy. Vì vậy, trên các máy in không hỗ trợ in tràn viền (borderless printing), đường viền đen trên cùng của hàng 1 và dưới cùng của hàng 3 có thể bị xén mất khi in thực tế.
> - **Khuyến nghị vận hành:** Cần in thử nghiệm trước trên máy in mục tiêu tại xưởng. Nếu máy in bị mất viền mép ngoài khi in A4, công nhân nên chuyển sang tùy chọn **Letter (4 tem/trang)**: Khổ Letter có lề trên/dưới rộng rãi ($39.75\text{ mm}$) và lề ngang $9.10\text{ mm}$, giúp giảm đáng kể nguy cơ bị xén viền so với A4. Tuy nhiên khả năng in thực tế vẫn phụ thuộc vào dòng máy in, driver và thiết lập trang giấy, vì vậy xưởng luôn cần in thử nghiệm để xác nhận chất lượng trước khi in hàng loạt.

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
  "auto_suggest_tutorial": true,
  "paper_size": "A4"
}
```

## Code Layout
- `core/slip_printer_engine.py`: PDF generator, ReportLab Code 39 barcode, 100% scale 6-slip A4 layout composer, fitz renderer
- `core/po_registry.py`: Atomic PO counter `11YYMMDDNN`, LAN SQLite concurrency locking, corruption auto-recovery
- `layout_config.json`: Master coordinate and dimension configuration for QR, Barcode 1D, and text items
- `ui/app_controller.py`: Controller handling events, record operations, D-Pad layout adjustments, barcode resizing
- `ui/components/tutorial_overlay.py`: Overlay Canvas, Spotlight Cutout, Tooltip Frame, Step Controller
- `ui/components/layout_tab.py`: Layout editor tab with Treeview, D-Pad nudge, and dimension controls
- `ui/components/data_tab.py`: Data entry tab with form, Treeview, and Live Canvas Preview
- `docs/BAO_CAO_KAIZEN_IN_PHIEU_HIEN_VAT.md`: Kaizen improvement report documenting 6-slip efficiency & 1D barcode
- `tests/test_barcode_1d_and_6slips.py`: Test suite for 1D Barcode Code 39, 6-slip pagination, and layout geometry
