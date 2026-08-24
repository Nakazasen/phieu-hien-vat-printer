"""
PPTX Japanese-to-Vietnamese Translation and Image OCR Package.
Provides end-to-end automation for PowerPoint presentation translation,
OpenXML Times New Roman typography enforcement, image OCR inpainting,
and coordinate-accurate Vietnamese text overlay.
"""

from .backup_manager import BackupManager
from .glossary import MANUFACTURING_GLOSSARY, translate_with_glossary
from .translator_engine import PPTXTranslatorEngine
from .openxml_typography import OpenXMLTypographyNormalizer, apply_times_new_roman_complete
from .image_ocr_overlay import ImageOCROverlayProcessor
from .pipeline import PPTXTranslationPipeline

__all__ = [
    "BackupManager",
    "MANUFACTURING_GLOSSARY",
    "translate_with_glossary",
    "PPTXTranslatorEngine",
    "OpenXMLTypographyNormalizer",
    "apply_times_new_roman_complete",
    "ImageOCROverlayProcessor",
    "PPTXTranslationPipeline",
]
