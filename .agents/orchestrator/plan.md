# Orchestrator Plan — PM_in_lai_phieuhienvat UI Audit & Refactoring

## Objectives
1. Survey and audit recent UI changes in `ui/components/data_tab.py` (68/32 split, 2-row button layout, widened inputs) and related visual components across resolutions (1000x700 minimum, 1366x768 laptop, 1920x1080 desktop).
2. Refactor any hardcoded widths, padding anomalies, or fragile grid configurations to flexible constraints (weights, sticky).
3. Create and execute programmatic UI resize verification checking widget geometry, visibility, and clipping.
4. Run full pytest suite and `--health-check`.
5. Multi-agent review, challenge, and forensic audit.

## Milestones & Execution Strategy
- **Milestone 1: Comprehensive Survey & Analysis**
  - Spawn 3 Explorers:
    - Explorer 1: Inspect `ui/components/data_tab.py`, grid layout, column/row weights, entry field configurations, button rows, labels, padding.
    - Explorer 2: Inspect parent containers (`ui/main_window.py`, `ui/app.py`, or notebook containers), resize event handling, minimum window dimensions (1000x700), theme/scaling.
    - Explorer 3: Inspect existing test suite, health-check runner, and existing headless/UI test facilities to guide the programmatic verification script.
- **Milestone 2: Refactoring & Verification Implementation**
  - Worker refactors layout constraints in `data_tab.py` (and related files if needed) and creates a robust programmatic verification script for multi-resolution testing.
- **Milestone 3: Verification, Review, & Adversarial Testing**
  - Reviewers (2) and Challengers (2) evaluate responsiveness, run `--health-check`, and execute pytest test suite across resolutions.
- **Milestone 4: Forensic Audit & Gate Clearance**
  - Auditor validates integrity, authentic implementations, absence of test mocking/fabrication.
- **Milestone 5: Synthesis & Reporting**
  - Synthesize findings into final summary report and handoff.
