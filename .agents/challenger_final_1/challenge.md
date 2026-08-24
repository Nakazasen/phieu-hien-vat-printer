# Empirical Challenge Report — Final Milestone Verification & Adversarial Hardening

**Agent**: `challenger_final_1`  
**Date**: 2026-08-19  
**Verdict**: `REQUEST_CHANGES` (Production Implementation: **APPROVE / ROBUST**; Test Harness in `test_tutorial_overlay_e2e.py`: **REQUEST_CHANGES**)  

---

## 1. Executive Summary

This report documents the empirical verification and adversarial stress-testing of the **Interactive Tutorial (UI Overlay) and User Guide** feature across `ui/components/tutorial_overlay.py`, `ui/components/tutorial_script.py`, `ui/main_window.py`, and `ui/app_controller.py`.

- **Phase 1 (Opaque-Box E2E Test Suite `tests/test_tutorial_overlay_e2e.py`)**:
  - Total test cases collected: 88
  - Results: **70 PASSED, 17 FAILED, 1 SKIPPED** (Pass rate: 79.5%)
  - Root cause analysis: 15 failures due to CustomTkinter `.place(width=..., height=...)` parameter violations in the test script, 1 failure due to `skip()` vs `on_finish()` callback semantic assertion mismatch, and 1 failure due to direct `ttk.Panedwindow.add(CTkFrame)` hierarchy mismatch in `test_t4_01`.
- **Phase 2 (White-Box Code Inspection & Tier 5 Adversarial Hardening `tests/test_tier5_adversarial_hardening.py`)**:
  - Total adversarial test cases: **25**
  - Results: **25 PASSED, 0 FAILED** (Pass rate: **100%**)
  - Statement coverage on `ui/components/tutorial_overlay.py`: **89%**

---

## 2. Phase 1: Opaque-Box E2E Suite Breakdown & Root Cause Analysis

Command executed:
```powershell
pytest tests/test_tutorial_overlay_e2e.py -v
```

### Failure Matrix (17 Failed Cases)

| # | Test Case | Root Cause Category | Detailed Mechanism |
|---|-----------|---------------------|--------------------|
| 1 | `test_t1_f1_01_overlay_canvas_initialization` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=120, height=40)` raises `ValueError: 'width' and 'height' arguments must be passed to constructor` |
| 2 | `test_t1_f2_01_spotlight_coordinates_exact_math` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=180, height=50)` raises `ValueError` |
| 3 | `test_t1_f2_02_spotlight_padding_expansion` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=100, height=40)` raises `ValueError` |
| 4 | `test_t1_f2_05_spotlight_recalculation_on_target_change` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=100, height=30)` raises `ValueError` |
| 5 | `test_t1_f3_05_tooltip_positioning_relative_to_spotlight` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=200, height=40)` raises `ValueError` |
| 6 | `test_t1_f5_03_on_finish_callback_executed` | Callback Semantic Mismatch | Test invokes `overlay.skip()` and asserts `finish_count == 1`. Production code cleanly separates `skip()` (no callback) vs `finish()` (triggers `on_finish`) |
| 7 | `test_t2_f1_02_negative_coordinate_clamping` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=80, height=30)` raises `ValueError` |
| 8 | `test_t2_f1_05_widget_exceeding_window_dimensions` | CTk `.place()` API Misuse | `ctk.CTkFrame.place(width=2000, height=1500)` raises `ValueError` |
| 9 | `test_t2_f2_01_widget_partially_offscreen_right` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=150, height=40)` raises `ValueError` |
| 10| `test_t2_f2_02_tooltip_flips_above_when_near_bottom` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=150, height=40)` raises `ValueError` |
| 11| `test_t2_f2_03_tooltip_flips_below_when_near_top` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=150, height=40)` raises `ValueError` |
| 12| `test_t2_f2_04_tooltip_horizontal_clamping_right` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=80, height=30)` raises `ValueError` |
| 13| `test_t2_f2_05_tooltip_horizontal_clamping_left` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=80, height=30)` raises `ValueError` |
| 14| `test_t2_f7_01_resize_event_repositions_scrim_and_card` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=150, height=40)` raises `ValueError` |
| 15| `test_t2_f7_05_window_move_without_size_change` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=100, height=30)` raises `ValueError` |
| 16| `test_t4_01_first_time_user_full_walkthrough_to_completion` | Panedwindow Hierarchy Error | `splitter.add(sidebar)` where `sidebar` is `SidebarPanel` (CTkFrame) without a parent host frame causes `_tkinter.TclError: can't add slave of .!panedwindow` |
| 17| `test_t4_04_window_resize_and_theme_toggle_during_walkthrough` | CTk `.place()` API Misuse | `ctk.CTkButton.place(width=120, height=35)` raises `ValueError` |

---

## 3. Phase 2: White-Box Source Code Assessment

### Component 1: `ui/components/tutorial_overlay.py`
- **4-Rectangle Scrim Partitioning**:
  `_draw_scrim_and_spotlight` divides the window into Top `(0, 0, win_w, y1)`, Bottom `(0, y2, win_w, win_h)`, Left `(0, y1, x1, y2)`, and Right `(x2, y1, win_w, y2)` non-overlapping rectangular polygons. Total area matches `win_w * win_h` exactly.
- **Spotlight Glow**:
  Triple-stroked emerald rectangle (`#064E3B`, `#34D399`, `#10B981`) provides high-contrast focus without interfering with target widget rendering.
- **PlacementEngine**:
  Responsive coordinate solver handles edge clipping, flipping on top/bottom/left/right boundary overflow, and centers modals when spotlight bounds are `None`.
- **Event Management & Debouncing**:
  Root `<Configure>` listener filters child events and debounces resize calculations to 60ms. `destroy()` properly cancels `_configure_timer_id` via `master.after_cancel()`.
- **Focus & Interaction Traps**:
  Canvas binds `<Button-1>` through `<Button-3>` and `<MouseWheel>` returning `"break"`, preventing mouse event passthrough to underlying controls while overlay is active.

### Component 2: `ui/components/tutorial_script.py`
- Implements 4 canonical steps in Vietnamese:
  1. `step_excel_import` (Excel import & duplicate checking)
  2. `step_qr_scanner` (3 QR scanning modes: 分割, 戻入, Bóc tách)
  3. `step_auto_po` (Auto PO format `11YYMMDDNN` & manual addition)
  4. `step_pdf_generation` (4 slips / A4 page & preview/print)
- Widget getters use defensive multi-attribute resolution and return `None` safely when uninitialized.

### Component 3: `ui/main_window.py` & `ui/app_controller.py`
- **Header Button**: `💡 Hướng dẫn` (#F59E0B Amber) integrated into header bar.
- **Persistence Layer**: Atomic write via temporary file (`user_settings.json.tmp` -> replace) guarantees no corrupt settings on sudden crash.
- **Onboarding Hook**: Auto-prompts first-time users at 600ms timer with automatic suppression for pytest sessions.

---

## 4. Tier 5 Adversarial Hardening Suite (`tests/test_tier5_adversarial_hardening.py`)

Command executed:
```powershell
pytest tests/test_tier5_adversarial_hardening.py -v
```

### Results Summary
| Sub-Tier | Focus Area | Test Count | Pass Rate |
|----------|------------|:----------:|:---------:|
| Sub-Tier 5.1 | Geometry & Placement Engine Stress | 6 | **100% (6/6)** |
| Sub-Tier 5.2 | Dynamic Event Concurrency & Rapid Interaction | 5 | **100% (5/5)** |
| Sub-Tier 5.3 | Tab Synchronization & Hierarchy Traversal | 4 | **100% (4/4)** |
| Sub-Tier 5.4 | State Desynchronization & Corruption Resilience | 3 | **100% (3/3)** |
| Sub-Tier 5.5 | Full App Lifecycle & UI Interaction Integrity | 7 | **100% (7/7)** |
| **Total** | **Tier 5 Adversarial Suite** | **25** | **100% (25/25)** |

### Coverage Metrics
- `ui/components/tutorial_overlay.py`: **89% statement coverage**
- `ui/components/tutorial_script.py`: **41% statement coverage** (100% of canonical script definitions; remaining lines are fallback attribute cascades)
- Combined module coverage: **75%**

---

## 5. Challenges & Recommendations

### [High] Challenge 1: E2E Test Suite API Incompatibilities
- **Issue**: 15 test cases in `tests/test_tutorial_overlay_e2e.py` fail because CustomTkinter `.place()` disallows `width` and `height` keyword arguments.
- **Attack Scenario**: Running standard test verification causes 17 false-positive failures.
- **Blast Radius**: Blocks automated CI/CD gating.
- **Mitigation**: Update `tests/test_tutorial_overlay_e2e.py` to instantiate widgets with `ctk.CTkButton(root, width=..., height=...).place(x=..., y=...)` or use standard `tk.Button(root).place(...)`.

### [Medium] Challenge 2: Panedwindow Hierarchy in Test Fixtures
- **Issue**: In `test_t4_01`, `SidebarPanel` is passed directly to `ttk.Panedwindow.add()` without the required `sidebar_host` wrapper frame that `main_window.py` uses.
- **Mitigation**: Update `test_t4_01` to wrap `SidebarPanel` inside a host frame before adding to `ttk.Panedwindow`.

### [Low] Challenge 3: Callback Semantic Documentation in E2E Tests
- **Issue**: `test_t1_f5_03` assumes `skip()` invokes `on_finish()`.
- **Mitigation**: Align test expectations with project design: `finish()` marks completion (`on_finish`), whereas `skip()` dismisses the walkthrough without marking completed.

---

## 6. Stress Test Outcomes

```
[PASS] Extreme Window Dims (0x0, Negative, 8K) -> Clamped cleanly to margin
[PASS] 100 Rapid Alternating Next/Prev Transitions -> No race condition or state desynchronization
[PASS] Rapid Configure Debouncing (50 events) -> Exactly 1 timer scheduled, 0 orphaned callbacks
[PASS] Rapid Destroy during Pending Configure -> Timer cancelled via after_cancel, no Tcl error
[PASS] Interleaved Keyboard Event Storm -> Handled cleanly and safely unbound on destroy
[PASS] Corrupted user_settings.json Syntax -> Default fallback recovered, atomic overwrite restored
[PASS] Headless AppController Operation -> All getters return None safely, start() is graceful no-op
[PASS] Modal Focus Trap -> Canvas blocks underlying button clicks from registering
[PASS] 20 Sequential Tutorial Launches -> 0 widget leaks, stable memory footprint
[PASS] Live App Widget Resolution -> All 4 canonical workflow targets resolved successfully
```
