## 2026-08-19T05:38:32Z
You are Challenger 2 (Final Round): Network Share & Live Output Challenger.
Your working directory is `.agents/challenger_2_final`.

Mission:
1. Run `python scripts/run_translation_pipeline.py` directly if not already executed or execute `python verify_translated_pptx.py`.
2. Inspect `backups/pptx_inputs/` and confirm timestamped backups and SHA-256 hashes exist.
3. Inspect `output/` and the network share target files `\\10.170.162.32\...` and verify they are valid PPTX presentations with translated Vietnamese text and Times New Roman font.
4. Record your final verdict (APPROVE or REQUEST_CHANGES) in `.agents/challenger_2_final/handoff.md`.
5. Send a completion message via `send_message`.
