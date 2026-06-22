"""Testes unitários para OCREngine, TesseractEngine e EasyOCREngine."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ocr.ocr_engine import OCREngine
from src.ocr.tesseract_engine import TesseractEngine


# Mock easyocr before importing EasyOCREngine since it may not be installed
if "easyocr" not in sys.modules:
    sys.modules["easyocr"] = MagicMock()

from src.ocr.easyocr_engine import EasyOCREngine


class TestOCREngineInterface:
    """Testes para a interface abstrata OCREngine."""

    def test_cannot_instantiate_abstract_class(self):
        """OCREngine não pode ser instanciada diretamente."""
        with pytest.raises(TypeError):
            OCREngine()  # type: ignore

    def test_concrete_subclass_must_implement_name(self):
        """Subclasses devem implementar a propriedade name."""

        class IncompleteEngine(OCREngine):
            def extract_text(self, pdf_path: Path) -> str:
                return ""

        with pytest.raises(TypeError):
            IncompleteEngine()  # type: ignore

    def test_concrete_subclass_must_implement_extract_text(self):
        """Subclasses devem implementar o método extract_text."""

        class IncompleteEngine(OCREngine):
            @property
            def name(self) -> str:
                return "Incomplete"

        with pytest.raises(TypeError):
            IncompleteEngine()  # type: ignore

    def test_valid_subclass_can_be_instantiated(self):
        """Subclasse completa pode ser instanciada."""

        class DummyEngine(OCREngine):
            @property
            def name(self) -> str:
                return "Dummy"

            def extract_text(self, pdf_path: Path) -> str:
                return "text"

        engine = DummyEngine()
        assert engine.name == "Dummy"
        assert engine.extract_text(Path("test.pdf")) == "text"


class TestTesseractEngine:
    """Testes para TesseractEngine."""

    def test_name_is_tesseract(self):
        """O nome do motor deve ser 'Tesseract'."""
        engine = TesseractEngine()
        assert engine.name == "Tesseract"

    def test_is_ocr_engine_subclass(self):
        """TesseractEngine é subclasse de OCREngine."""
        assert issubclass(TesseractEngine, OCREngine)

    @patch("src.ocr.tesseract_engine.fitz")
    @patch("src.ocr.tesseract_engine.pytesseract")
    def test_extract_text_single_page(self, mock_pytesseract, mock_fitz):
        """Extrai texto de PDF com uma página."""
        # Setup mock document
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_pytesseract.image_to_string.return_value = "Texto OCR extraído"

        engine = TesseractEngine()
        result = engine.extract_text(Path("test.pdf"))

        assert result == "Texto OCR extraído"
        mock_fitz.open.assert_called_once_with("test.pdf")
        mock_doc.close.assert_called_once()

    @patch("src.ocr.tesseract_engine.fitz")
    @patch("src.ocr.tesseract_engine.pytesseract")
    def test_extract_text_multiple_pages(self, mock_pytesseract, mock_fitz):
        """Extrai e concatena texto de PDF com múltiplas páginas."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)

        mock_page1 = MagicMock()
        mock_page1.get_pixmap.return_value = mock_pixmap
        mock_page2 = MagicMock()
        mock_page2.get_pixmap.return_value = mock_pixmap

        mock_doc.__getitem__ = MagicMock(side_effect=[mock_page1, mock_page2])
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_pytesseract.image_to_string.side_effect = ["Página 1", "Página 2"]

        engine = TesseractEngine()
        result = engine.extract_text(Path("multi.pdf"))

        assert "Página 1" in result
        assert "Página 2" in result
        assert result == "Página 1\n\nPágina 2"

    @patch("src.ocr.tesseract_engine.fitz")
    def test_extract_text_returns_empty_on_open_failure(self, mock_fitz):
        """Retorna string vazia se não conseguir abrir o PDF."""
        mock_fitz.open.side_effect = Exception("Cannot open file")

        engine = TesseractEngine()
        result = engine.extract_text(Path("broken.pdf"))

        assert result == ""

    @patch("src.ocr.tesseract_engine.fitz")
    @patch("src.ocr.tesseract_engine.pytesseract")
    def test_extract_text_handles_page_error_gracefully(
        self, mock_pytesseract, mock_fitz
    ):
        """Continua processando se uma página falhar."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)

        # First page raises error, second succeeds
        mock_page1 = MagicMock()
        mock_page1.get_pixmap.side_effect = RuntimeError("Page corrupted")
        mock_page2 = MagicMock()
        mock_page2.get_pixmap.return_value = mock_pixmap

        mock_doc.__getitem__ = MagicMock(side_effect=[mock_page1, mock_page2])
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_pytesseract.image_to_string.return_value = "Page 2 text"

        engine = TesseractEngine()
        result = engine.extract_text(Path("partial.pdf"))

        # Should contain empty string for failed page and text for successful one
        assert "Page 2 text" in result
        mock_doc.close.assert_called_once()


class TestEasyOCREngine:
    """Testes para EasyOCREngine."""

    def test_name_is_easyocr(self):
        """O nome do motor deve ser 'EasyOCR'."""
        engine = EasyOCREngine()
        assert engine.name == "EasyOCR"

    def test_is_ocr_engine_subclass(self):
        """EasyOCREngine é subclasse de OCREngine."""
        assert issubclass(EasyOCREngine, OCREngine)

    def test_reader_is_lazy_initialized(self):
        """Reader não é criado no __init__ (lazy initialization)."""
        engine = EasyOCREngine()
        assert engine._reader is None

    @patch("src.ocr.easyocr_engine.easyocr")
    @patch("src.ocr.easyocr_engine.fitz")
    def test_extract_text_single_page(self, mock_fitz, mock_easyocr):
        """Extrai texto de PDF com uma página."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)

        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [
            (None, "Linha 1", 0.95),
            (None, "Linha 2", 0.90),
        ]
        mock_easyocr.Reader.return_value = mock_reader

        engine = EasyOCREngine()
        result = engine.extract_text(Path("test.pdf"))

        assert "Linha 1" in result
        assert "Linha 2" in result
        mock_doc.close.assert_called_once()

    @patch("src.ocr.easyocr_engine.easyocr")
    @patch("src.ocr.easyocr_engine.fitz")
    def test_extract_text_multiple_pages(self, mock_fitz, mock_easyocr):
        """Extrai e concatena texto de múltiplas páginas."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)

        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_reader = MagicMock()
        mock_reader.readtext.side_effect = [
            [(None, "Texto pag 1", 0.9)],
            [(None, "Texto pag 2", 0.9)],
        ]
        mock_easyocr.Reader.return_value = mock_reader

        engine = EasyOCREngine()
        result = engine.extract_text(Path("multi.pdf"))

        assert "Texto pag 1" in result
        assert "Texto pag 2" in result
        assert result == "Texto pag 1\n\nTexto pag 2"

    @patch("src.ocr.easyocr_engine.fitz")
    def test_extract_text_returns_empty_on_open_failure(self, mock_fitz):
        """Retorna string vazia se não conseguir abrir o PDF."""
        mock_fitz.open.side_effect = Exception("File not found")

        engine = EasyOCREngine()
        result = engine.extract_text(Path("missing.pdf"))

        assert result == ""

    @patch("src.ocr.easyocr_engine.easyocr")
    @patch("src.ocr.easyocr_engine.fitz")
    def test_extract_text_handles_page_error_gracefully(
        self, mock_fitz, mock_easyocr
    ):
        """Continua processando se uma página falhar."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=2)

        mock_pixmap = MagicMock()
        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b"\x00" * (100 * 100 * 3)

        mock_page1 = MagicMock()
        mock_page1.get_pixmap.side_effect = RuntimeError("Page error")
        mock_page2 = MagicMock()
        mock_page2.get_pixmap.return_value = mock_pixmap

        mock_doc.__getitem__ = MagicMock(side_effect=[mock_page1, mock_page2])
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = [(None, "Recovered text", 0.85)]
        mock_easyocr.Reader.return_value = mock_reader

        engine = EasyOCREngine()
        result = engine.extract_text(Path("partial.pdf"))

        assert "Recovered text" in result
        mock_doc.close.assert_called_once()

    @patch("src.ocr.easyocr_engine.easyocr")
    @patch("src.ocr.easyocr_engine.fitz")
    def test_reader_is_reused_across_calls(self, mock_fitz, mock_easyocr):
        """Reader é reutilizado entre chamadas (lazy singleton)."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_pixmap = MagicMock()
        mock_pixmap.width = 10
        mock_pixmap.height = 10
        mock_pixmap.samples = b"\x00" * (10 * 10 * 3)
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        mock_fitz.open.return_value = mock_doc
        mock_fitz.Matrix = MagicMock()

        mock_reader = MagicMock()
        mock_reader.readtext.return_value = []
        mock_easyocr.Reader.return_value = mock_reader

        engine = EasyOCREngine()
        engine.extract_text(Path("a.pdf"))
        engine.extract_text(Path("b.pdf"))

        # Reader should only be created once
        mock_easyocr.Reader.assert_called_once_with(["pt", "en"], gpu=False)
