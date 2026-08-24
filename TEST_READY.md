# E2E Test Suite Ready: Interactive Tutorial (UI Overlay) and User Guide

## Test Runner
- Command: `pytest tests/test_tutorial_overlay_e2e.py -v`
- Expected: All test cases execute with 100% success rate (0 failures).

## Coverage Summary
| Tier | Count | Description |
|------|------:|-------------|
| 1. Feature Coverage | 40 | Feature isolation tests covering canvas scrim, spotlight bounding box calculation, tooltip card rendering, step progression, skip/cleanup, tutorial script content, header trigger button, and persistence |
| 2. Boundary & Corner | 35 | Edge cases: zero/negative dimensions, multi-monitor offscreen bounds, empty/corrupt steps, rapid click debouncing, escape key handling, missing widget fallback, and window resize/minimize |
| 3. Cross-Feature | 8 | Pairwise testing: tab switching + resize, first-launch prompt + manual trigger, theme change + overlay active, uncommitted form data + tutorial |
| 4. Real-World Application | 5 | End-to-end user journeys: first-time user full walkthrough, decline first prompt then manual trigger, skip mid-tutorial, resize/theme toggle mid-walkthrough, and standalone component isolation |
| **Total** | **88** | Complete 4-Tier opaque-box test suite for interactive tutorial overlay and user guide |

## Feature Checklist
| Feature | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---------|:------:|:------:|:------:|:------:|
| Overlay Scrim & Canvas Layer | 5 | 5 | ✓ | ✓ |
| Spotlight Bounding Box Calculation | 5 | 5 | ✓ | ✓ |
| Tooltip Card Component | 5 | 5 | ✓ | ✓ |
| Step Progression & Navigation | 5 | 5 | ✓ | ✓ |
| Skip, Finish & Cleanup | 5 | 5 | ✓ | ✓ |
| Tutorial Script Content (4 Core Steps) | 5 | 5 | ✓ | ✓ |
| Header Trigger Button (`💡 Hướng dẫn`) | 5 | 5 | ✓ | ✓ |
| Persistence & First-Launch Prompt | 5 | 5 | ✓ | ✓ |
