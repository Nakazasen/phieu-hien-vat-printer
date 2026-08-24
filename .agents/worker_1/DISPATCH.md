# DISPATCH - Worker 1

## 2026-08-19T05:15:19Z
Task: Lead Automation Engineer for Japanese-to-Vietnamese PowerPoint Translation and Image OCR Project.
Working directory: .agents/worker_1

Objectives:
- R4: Backup & Safe Staging (Local backups with SHA-256 verification, staging working copies)
- R1: Text Translation (Recursive traversal of shapes, GroupShapes, Tables, Slide Notes, text boxes; High-quality JA->VN translation with engineering glossary; Paragraph-level aggregation)
- R2: Format & Typography Preservation (Strict Times New Roman font enforcement across latin/ea/cs/defRPr/endParaRPr in OpenXML, style preservation, auto-fit/margin adjustment)
- R3: Image OCR, Text Erasing & Vietnamese Overlay (OCR Japanese text in images, inpaint/erase, update image blob, create overlay text boxes on slide)
- Execution & Network Overwrite: Process both files, verify integrity, write back to target UNC share paths.
- Verification Script: verify_translated_pptx.py checking 100% traversal, 0 residual Japanese text, 100% Times New Roman font, OCR/overlay audit, SHA-256 checksums.
