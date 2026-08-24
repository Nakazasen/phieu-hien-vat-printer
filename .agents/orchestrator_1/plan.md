# Master Plan: Interactive Tutorial (UI Overlay) and User Guide

## Objective
Build an interactive UI overlay tutorial engine and user guide feature for PM_in_lai_phieuhienvat that walks users through core workflows:
1. Excel data loading (Nạp dữ liệu từ Excel)
2. QR Scanner tool & 3 modes: Separate/Split, Return to warehouse, Disassemble/Extract (Phân tách, Hoàn kho, Bóc tách)
3. Auto PO creation (Tạo mã Auto PO)
4. PDF generation & printing (Tạo và In file PDF)
Including first-time launch hint / persistence, UI trigger button, and graceful skip/navigation.

## Phase 0: Survey & Scope Mapping (Parallel Explorers & Spec Miner)
- Explorer 1: Inspect UI structure, main window, CustomTkinter layout, coordinate spaces, and modal overlay techniques.
- Explorer 2: Inspect business modules (Excel importer, QR scanner, Auto PO, PDF generation) and their widget handles.
- Spec Miner 1: Probe specifications, config files (`layout_config.json`, settings), and user requirements.

## Phase 1: Architecture & Decomposition
- Synthesize survey findings into `PROJECT.md` at project root with full Feature Inventory, Milestones, and Interface Contracts.
- Define test infrastructure and acceptance criteria.

## Phase 2: Dual Track Execution
- Track A (E2E Testing Track): Develop opaque-box E2E test runner and test cases (Tiers 1-4) covering UI overlay, coordinate bounding box, navigation, and persistence.
- Track B (Implementation Track):
  - Milestone 1: Overlay Engine & Highlighting Mechanism
  - Milestone 2: Tutorial Script & Business Flow Walkthrough
  - Milestone 3: UI Trigger & Persistence
  - Final Milestone: Pass 100% E2E tests + Tier 5 Adversarial Coverage Hardening

## Phase 3: Final Verification & Handover
- Complete Acceptance Gate.
- Notify Sentinel / Parent.
