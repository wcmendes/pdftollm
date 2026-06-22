"""Módulo de OCR com fallback entre motores."""

from src.ocr.markdown_quality_detector import MarkdownQualityDetector
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager

__all__ = [
    "EasyOCREngine",
    "MarkdownQualityDetector",
    "OCREngine",
    "OCRManager",
    "TesseractEngine",
]


def __getattr__(name: str):
    """Lazy import para motores OCR com dependências pesadas."""
    if name == "TesseractEngine":
        from src.ocr.tesseract_engine import TesseractEngine

        return TesseractEngine
    if name == "EasyOCREngine":
        from src.ocr.easyocr_engine import EasyOCREngine

        return EasyOCREngine
    raise AttributeError(f"module 'src.ocr' has no attribute {name!r}")
