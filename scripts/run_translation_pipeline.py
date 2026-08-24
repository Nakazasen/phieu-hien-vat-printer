"""
Main Execution Script for Japanese-to-Vietnamese PPTX Translation and Image OCR.
Processes both target Athena QA presentations, executes local backup with SHA-256,
translates text containers, normalizes OpenXML typography to Times New Roman,
runs Tesseract 5.5 OCR + inpainting + overlay on embedded images, and safely overwrites target UNC files.
"""

import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from pptx_translation.pipeline import PPTXTranslationPipeline
from pptx_translation.backup_manager import BackupManager

TARGET_FILES = [
    r"\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程取り組み説明2025 VN.pptx",
    r"\\10.170.162.32\Data\00_KDTVN Common(KDTVN共通)\⑤Production Engineering(製造技術)\◆Iris EXP◆\Điều chỉnh\Athenal\Athena保証工程　RaspberryPI問題点 VN.pptx",
]


def run_pipeline():
    print("=" * 80)
    print("STARTING PPTX JAPANESE-TO-VIETNAMESE TRANSLATION & IMAGE OCR PIPELINE")
    print("=" * 80)
    
    pipeline = PPTXTranslationPipeline()
    results = []

    for idx, target_path in enumerate(TARGET_FILES, start=1):
        print(f"\n[{idx}/{len(TARGET_FILES)}] Processing: {target_path}")
        start_time = time.time()
        
        try:
            stats = pipeline.process_file(source_path=target_path)
            duration = time.time() - start_time
            stats["duration_seconds"] = round(duration, 2)
            results.append(stats)
            
            print(f" -> Completed in {duration:.2f}s")
            print(f" -> Slides: {stats['total_slides']}")
            print(f" -> Paragraphs Translated: {stats['paragraphs_translated']}")
            print(f" -> Table Cells Processed: {stats['table_cells_processed']}")
            print(f" -> Slide Notes Processed: {stats['slide_notes_processed']}")
            print(f" -> Images Found: {stats['images_found']} (with Japanese: {stats['images_with_japanese']})")
            print(f" -> Image Overlay Text Boxes: {stats['image_overlay_boxes']}")
            print(f" -> Backup SHA-256: {stats['original_sha256']}")
            print(f" -> Deployed SHA-256: {stats.get('deployed_sha256')}")
        except Exception as e:
            print(f" -> ERROR processing file: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 80)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    # Write execution log to output directory
    log_path = os.path.join(PROJECT_ROOT, "output", "pipeline_execution_log.json")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nExecution log written to: {log_path}")

    return results


if __name__ == "__main__":
    run_pipeline()
