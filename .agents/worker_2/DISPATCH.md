## 2026-08-19T05:25:30Z
You are Worker 2: PPTX Pipeline Final Execution & Remediation Worker.
Your working directory is `.agents/worker_2`.

Tasks to Implement:
1. Fix GroupShape Coordinate Offset in Image OCR Overlays (`pptx_translation/image_ocr_overlay.py`):
   - In `_find_all_pictures(shape_tree, parent_offset_x=0, parent_offset_y=0)`, accumulate `parent_offset_x + shape.left` and `parent_offset_y + shape.top` when traversing nested `GroupShape` items.
   - Ensure the slide overlay text boxes use these accumulated global coordinates so text positions on grouped images are pixel-perfect on the slide.

2. Atomic Safe Write-Back on Network Share (`pptx_translation/backup_manager.py`):
   - In `deploy_to_network(staged_path, target_unc_path)`:
     - Write first to `target_unc_path + ".tmp"`.
     - Verify SHA-256 of `target_unc_path + ".tmp"` matches `staged_path`.
     - Perform atomic replace (`os.replace(target_unc_path + ".tmp", target_unc_path)`) or safe rename.

3. Fix `scripts/inspect_pptx_target.py`:
   - Fix `AttributeError: type object 'MSO_SHAPE_TYPE' has no attribute 'GRAPHIC_FRAME'`.

4. Live Execution of the Translation Pipeline:
   - Run `python scripts/run_translation_pipeline.py`.
   - Ensure both target PPTX files:
     1. `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx`
     2. `\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx`
     are backed up to `backups/pptx_inputs/<timestamp>/` with SHA-256 hashes, completely translated to Vietnamese with Times New Roman OpenXML typography, images OCR'd / inpainted / text overlaid, and safely deployed to the network share.

5. Run Verification & Tests:
   - Run `python verify_translated_pptx.py` and capture full output.
   - Run `pytest tests/` and capture full output.
