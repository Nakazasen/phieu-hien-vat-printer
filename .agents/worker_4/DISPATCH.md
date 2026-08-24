## 2026-08-19T05:41:09Z
You are Worker 4: Dedicated Live Pipeline Execution Worker.
Your working directory is `.agents/worker_4`.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

CRITICAL TASK:
You MUST run the translation pipeline and verification commands directly using `run_command`:

Step 1: Run the pipeline
Execute via `run_command`:
`python scripts/run_translation_pipeline.py`
Wait for it to finish processing both target PPTX presentations:
1. `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx` (17 slides)
2. `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx` (6 slides)

Step 2: Run verification
Execute via `run_command`:
`python verify_translated_pptx.py`
Verify that all 5 tests pass (Backups, Presentation Traversal, OpenXML Typography, Network Deployment, Adversarial Robustness).

Step 3: Run pytest
Execute via `run_command`:
`pytest tests/`

Record the command outputs, SHA-256 hashes, backup folders, and results in `.agents/worker_4/handoff.md`.
Send a completion message via `send_message` when done.
