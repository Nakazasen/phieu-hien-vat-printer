# E2E Test Infra: Interactive Tutorial (UI Overlay) and User Guide

## Test Philosophy
- **Opaque-Box & Empirical Verification**: Validate user-facing behavior, visual coordinate calculations, step progression, keyboard/mouse event dispatch, and settings persistence without relying on internal implementation private hacks.
- **Progressive Testability & Contract-Driven**: Strict alignment with interface contracts defined in `PROJECT.md` (`TutorialStep`, `InteractiveTutorialOverlay` / `TutorialOverlay`, and `user_settings.json`).
- **Multi-Tier Pyramid**:
  - **Tier 1**: Feature Coverage (>=5 test cases per feature covering overlay creation, spotlight math, tooltip card, step navigation, cleanup, tutorial script, trigger button, and persistence).
  - **Tier 2**: Boundary & Corner Cases (>=5 test cases per category: zero/negative dimensions, multi-monitor offscreen bounds, empty steps, rapid click debouncing, escape key handling, missing widget fallback, window resize/minimize).
  - **Tier 3**: Cross-Feature Combinations (Pairwise coverage: tab switching + resize, first-launch prompt + manual trigger, theme change + overlay active, uncommitted form data + tutorial).
  - **Tier 4**: Real-World Application Scenarios (Complete end-to-end user journeys from first launch to subsequent restart).

## Feature Inventory
| # | Feature | Source (Requirement) | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---|---------|---------------------|:------:|:------:|:------:|:------:|
| 1 | Overlay Scrim & Canvas Layer | ORIGINAL_REQUEST §R1, PROJECT §F1 | 5 | 5 | ✓ | ✓ |
| 2 | Spotlight Bounding Box Calculation | ORIGINAL_REQUEST §R1, PROJECT §F1 | 5 | 5 | ✓ | ✓ |
| 3 | Tooltip Card Component | ORIGINAL_REQUEST §R1, PROJECT §F2 | 5 | 5 | ✓ | ✓ |
| 4 | Step Progression & Navigation | ORIGINAL_REQUEST §R1, PROJECT §F2 | 5 | 5 | ✓ | ✓ |
| 5 | Skip, Finish & Cleanup | ORIGINAL_REQUEST §Acceptance, PROJECT §F1 | 5 | 5 | ✓ | ✓ |
| 6 | Tutorial Script Content (4 Core Steps) | ORIGINAL_REQUEST §R2, PROJECT §F4-F7 | 5 | 5 | ✓ | ✓ |
| 7 | Header Trigger Button (`💡 Hướng dẫn`) | ORIGINAL_REQUEST §R3, PROJECT §F8 | 5 | 5 | ✓ | ✓ |
| 8 | Persistence & First-Launch Prompt | ORIGINAL_REQUEST §R3, PROJECT §F9 | 5 | 5 | ✓ | ✓ |

## Test Architecture
- **Test Runner**: `pytest`
- **Execution Command**: `pytest tests/test_tutorial_overlay_e2e.py -v`
- **Test Target**: `tests/test_tutorial_overlay_e2e.py`
- **Environment Isolation**:
  - `conftest.py` isolates `%LOCALAPPDATA%\InPhieuHienVatData` to a temporary directory (`INPHIEUHIENVAT_DATA_DIR`).
  - Mocked `tkinter.messagebox` dialogs prevent modal blocking.
  - Tkinter root window lifecycle managed via `tk_root` fixture with proper `update_idletasks()` and timer cleanup.
- **Contract Adherence**:
  - `TutorialStep(step_id, title, description, target_widget_getter, target_tab_index, tooltip_position)`
  - `InteractiveTutorialOverlay(master_window, on_finish)` with `register_steps()`, `start()`, `next_step()`, `prev_step()`, `skip()`, `destroy()`
  - Persistence schema in `user_settings.json`: `{"has_seen_tutorial": bool, "auto_suggest_tutorial": bool, ...}`

## Boundary & Corner Cases (Tier 2 Matrix)
| # | Category | Edge Condition | Expected Behavior |
|---|----------|----------------|-------------------|
| 1 | Zero / Negative Dimensions | Target widget has 0 width/height or unmapped | Fallback center card without division by zero |
| 2 | Minimal / 4K Window Geometry | Window sized at 800x600 or 3840x2160 | Scrim and tooltip clamped cleanly inside window |
| 3 | Offscreen Bounds | Target widget extends beyond window edges | Spotlight and tooltip clamped to visible viewport |
| 4 | Tooltip Flipping | Widget at extreme top/bottom/left/right | Tooltip flips/shifts to avoid clipping |
| 5 | Empty / Corrupt Steps | `register_steps([])` or `start(999)` | Graceful no-op or boundary clamping without crash |
| 6 | Rapid Click Debouncing | 20 rapid clicks on Next/Back in 100ms | Smooth transition without race condition or memory leak |
| 7 | Keyboard Navigation | `<Escape>` (Skip), `<Return>` / `<Right>` (Next), `<Left>` (Back) | Clean event handling and post-destruction unbinding |
| 8 | Missing Widget Fallback | `target_widget_getter` returns `None` or raises error | Safe modal fallback card, no unhandled exception |
| 9 | Dynamic Window Resize | Window resized during active tutorial | `<Configure>` debounced re-anchoring of spotlight & card |
| 10| Dynamic Theme Change | Theme switched (Light <-> Dark) during overlay | Scrim and tooltip colors adapt without destroying state |

## Cross-Feature Combinations (Tier 3 Matrix)
| # | Pairwise Interaction | Test Verification |
|---|----------------------|-------------------|
| 1 | Tab Switching + Window Resize | Switching notebook tab to highlight widget + immediate window resize -> spotlight tracks new widget position |
| 2 | First-Launch Prompt + Manual Trigger | User declines first-launch prompt -> clicks `💡 Hướng dẫn` later -> launches successfully |
| 3 | Theme Change + Active Overlay | Dark/Light mode switch while overlay active maintains contrast and visibility |
| 4 | Uncommitted Form Data + Tutorial | Active form edits are preserved without data corruption during tutorial walkthrough |
| 5 | QR Scan Dialog + Tutorial Completion | Tutorial Step 2 highlights QR Scan -> tutorial finishes -> QR Dialog opens normally |
| 6 | Rapid Tab Switches + Overlay Events | Rapid tab changes under overlay do not cause orphaned canvas highlights |

## Real-World Application Scenarios (Tier 4 Matrix)
| # | Scenario | Walkthrough Sequence | Success Criteria |
|---|----------|----------------------|------------------|
| 1 | First-Time User Complete Walkthrough | Clean settings -> First-launch dialog -> Accept -> Steps 1 to 4 -> Finish -> Restart app | `has_seen_tutorial` set to `true`, no prompt on second launch |
| 2 | User Declines Prompt Then Uses Header | Clean settings -> First-launch dialog -> Decline -> Manual Header button -> Walkthrough -> Finish | Tutorial completes, settings persisted, subsequent launch silent |
| 3 | User Skips Mid-Tutorial | Start tutorial -> Advance to Step 2 (QR) -> Click "Bỏ qua" | Immediate destruction, UI controls immediately clickable |
| 4 | Window Resize & Theme Change Mid-Tutorial | Start tutorial -> Step 3 (DataTab) -> Resize window -> Change theme -> Finish | Spotlight re-anchors, theme applies, UI remains consistent |
| 5 | Standalone Component Isolation | Bare `ctk.CTk` / `tk.Tk` root -> instantiate overlay -> custom steps -> navigation -> cleanup | 100% contract compliance in isolation |

## Coverage Thresholds
- **Tier 1 (Feature Coverage)**: ≥40 test cases (8 features × 5 cases)
- **Tier 2 (Boundary & Corner)**: ≥35 test cases (7 categories × 5 cases)
- **Tier 3 (Cross-Feature Combinations)**: ≥8 pairwise integration test cases
- **Tier 4 (Real-World Application Scenarios)**: ≥5 comprehensive end-to-end scenario test cases
- **Total Target**: ≥88 test cases executed via `pytest tests/test_tutorial_overlay_e2e.py -v`
