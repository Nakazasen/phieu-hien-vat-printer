## 2026-08-18T05:11:10Z
You are survey_explorer_2 (Role: Architecture & Tech Debt Auditor).
Target Workspace: D:\Sandbox\PM_in_lai_phieuhienvat
Original User Request: D:\Sandbox\PM_in_lai_phieuhienvat\.agents\ORIGINAL_REQUEST.md
Reference Docs: D:\Sandbox\PM_in_lai_phieuhienvat\HANDOVER.md and D:\Sandbox\PM_in_lai_phieuhienvat\docs\ONBOARDING.md

Mission:
1. Read ORIGINAL_REQUEST.md, HANDOVER.md, and docs/ONBOARDING.md.
2. Analyze the actual refactored codebase against what HANDOVER.md and ONBOARDING.md describe.
3. Identify:
   - Any architectural gaps between documentation and implementation (e.g. modules mentioned in HANDOVER/ONBOARDING but missing or incomplete)
   - Technical debt: code duplication, god functions/classes, hardcoded magic numbers/strings, error handling omissions, missing type annotations, concurrency/threading issues in UI/updater
   - Missed refactoring steps or incomplete refactoring tasks
   - Dead code, unused files, or leftover legacy scripts
   - Documentation discrepancies (places where HANDOVER/ONBOARDING are out of sync with code)
4. Categorize all technical debt items by severity (High, Medium, Low) and provide actionable remediation advice.
5. Produce a structured handoff report and send completion message back to parent with the summary and report path.
