## 2026-08-19T06:09:53Z
You are Worker Live Execution: Direct Pipeline Runner.
Your working directory is `.agents/worker_live_execution`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL INSTRUCTIONS:
You MUST execute the following command line directly using `run_command`:

Step 1: Execute Pipeline
Command: `python scripts/run_translation_pipeline.py`
Wait for the command to finish completely.

Step 2: Verify Artifacts on Disk
Confirm that:
- `backups/pptx_inputs/` has been created with timestamped folders and SHA-256 hashes of original files.
- `output/` contains the translated `.pptx` files.
- The network share files at `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\` have been overwritten with the translated versions.

Step 3: Execute Verification Script
Command: `python verify_translated_pptx.py`
Capture stdout/stderr and confirm exit code 0 (all 5 checks pass).

Step 4: Execute Full Pytest Suite
Command: `pytest -v`
Capture output and confirm all tests pass.

Document all outputs in `.agents/worker_live_execution/handoff.md` and send a completion message via `send_message`.
