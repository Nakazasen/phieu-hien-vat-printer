# BRIEFING — 2026-08-19T10:25:00Z

## Mission
Mine and document all configuration persistence mechanisms, user tutorial persistence options, UI placement for the tutorial button, constraints, and edge cases for the interactive tutorial feature in the Phieu Hien Vat Printer application.

## 🔒 My Identity
- Archetype: teamwork_preview_spec_miner
- Roles: Specification Miner, Teamwork Specialist
- Working directory: d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_spec_miner_survey_1
- Original parent: f58a2051-81bc-43da-94ee-7a06808f5dda
- Milestone: Specification Mining for Interactive Step-by-Step Tutorial & UI Placement

## 🔒 Key Constraints
- Read-only on source code: Do NOT implement anything.
- Probe authoritative specifications (codebase, config files, ORIGINAL_REQUEST.md).
- Document features in the required table formats: Features Discovered, Edge Cases.
- Deliver self-contained handoff report at handoff.md with 5 components (Observation, Logic Chain, Caveats, Conclusion, Verification Method).

## Current Parent
- Conversation ID: f58a2051-81bc-43da-94ee-7a06808f5dda
- Updated: not yet

## Task Summary
- **What to build/mine**: Configuration persistence architecture, tutorial state storage, UI trigger button placement options, constraints & edge cases.
- **Success criteria**: Comprehensive specification mining report covering all 4 task items and standard tables.
- **Interface contracts**: ORIGINAL_REQUEST.md, codebase config modules.
- **Code layout**: d:\Sandbox\PM_in_lai_phieuhienvat\

## Key Decisions Made
- Confirmed `user_settings.json` in `%LOCALAPPDATA%\InPhieuHienVatData\` as the optimal store for tutorial flags (`has_seen_tutorial`, `auto_suggest_tutorial`) to avoid polluting `layout_config.json` (used strictly for ReportLab PDF coordinate geometry).
- Identified Top-Right Header Bar (`header -> preview_controls`) as the optimal location for the `💡 Hướng dẫn (Tutorial)` button (#F59E0B Amber), ensuring visibility across all tabs.
- Mined all 4 core business tutorial steps (Import Excel ➔ Quét QR Nghiệp Vụ ➔ Form & Auto PO ➔ Tạo PDF & In Ấn).
- Detailed 10 comprehensive edge cases and technical constraints (Window resize, High DPI scaling, Tab auto-selection, Debounce locking, Scrim modal grab, Skip/Escape cleanup).

## Artifact Index
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_spec_miner_survey_1\DISPATCH.md — Dispatch instructions log
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_spec_miner_survey_1\progress.md — Liveness & progress tracking
- d:\Sandbox\PM_in_lai_phieuhienvat\.agents\teamwork_preview_spec_miner_survey_1\handoff.md — Final specification mining report
