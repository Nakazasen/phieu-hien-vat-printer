# Plan: Inno Setup 6 Packaging & Auto-Update Engine for PM_in_lai_phieuhienvat

## Objective
Port and adapt the packaging setup (Inno Setup 6 `.iss`, PyInstaller/build scripts) and Auto-Update engine from the reference project `D:\Sandbox\MP2027` into `PM_in_lai_phieuhienvat`, ensuring automated building, smooth non-blocking UI checks, shared network drive compatibility, shortcuts, clean uninstallation, and full test suite verification.

## Phase 0: Parallel Survey (3 Explorers)
1. **Explorer 1 (Reference Investigation)**: Investigate `D:\Sandbox\MP2027` (docs/handover, Inno Setup `.iss`, build scripts, auto-update module, network share logic, process restart handling).
2. **Explorer 2 (Target Codebase Survey)**: Investigate `D:\Sandbox\PM_in_lai_phieuhienvat` (architecture, entry point, main window/controller, versioning constants, network paths for database vs updater).
3. **Explorer 3 (Tooling & Integration Specialist)**: Investigate Inno Setup 6 compiler (ISCC) on system, PyInstaller specs, build workflows, and test harness strategies for auto-update simulation.

## Phase 1: Architecture & Decomposition (PROJECT.md)
- Feature Inventory mapping all R1, R2, R3 requirements.
- Milestones with clear interfaces.
- Test infrastructure planning (TEST_INFRA.md).

## Phase 2: Execution via Iteration Loops
- M1: Inno Setup 6 Packaging & Build Scripts.
- M2: Auto-Update Engine & Non-Blocking UI Integration.
- M3: E2E Verification & Test Suite.

## Phase 3: Forensic Integrity Audit & Final Handoff
- Clean audit verification.
- Report synthesis and handoff to Sentinel.
