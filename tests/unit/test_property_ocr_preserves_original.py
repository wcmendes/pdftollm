"""Testes de propriedade para preservação do original quando OCR falha.

**Validates: Requirements 8.6**

Property 14: Para qualquer PDF_Imagem onde todos os motores OCR falharem
(ambos produzem < 50 chars alfanuméricos por página), o Arquivo_Saída
original SHALL permanecer inalterado no sistema de arquivos (mesmo
conteúdo byte a byte).
"""

import queue
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.data_models import OCRCandidate, OCRStatus, OCREngineUsed
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager


# ─── Motor OCR fake que retorna texto ilegível ──────────────────────────────────


class FailingOCREngine(OCREngine):
    """Motor OCR que sempre retorna texto ilegível (poucos chars alfanuméricos)."""

    def __init__(self, engine_name: str, text_to_return: str) -> None:
        self._name = engine_name
        self._text_to_return = text_to_return

    @property
    def name(self) -> str:
        return self._name

    def extract_text(self, pdf_path: Path) -> str:
        return self._text_to_return


class ExceptionOCREngine(OCREngine):
    """Motor OCR que sempre lança exceção."""

    def __init__(self, engine_name: str) -> None:
        self._name = engine_name

    @property
    def name(self) -> str:
        return self._name

    def extract_text(self, pdf_path: Path) -> str:
        raise RuntimeError(f"{self._name} engine unavailable")


# ─── Estratégias de geração ─────────────────────────────────────────────────────

# Conteúdo original aleatório (bytes arbitrários para simular qualquer .md)
_original_content = st.binary(min_size=1, max_size=2000)

# Contagem de páginas válida (≥ 1)
_page_count = st.integers(min_value=1, max_value=50)

# Texto ilegível: poucos caracteres alfanuméricos (< 50 por página garantido)
# Gera texto com no máximo 10 chars alfanuméricos (sempre abaixo do threshold)
_illegible_alnum = st.integers(min_value=0, max_value=10)

# Padding não-alfanumérico para tornar o texto mais realista
_non_alnum_padding = st.text(
    alphabet=" \t\n!@#$%^&*()[]{}|;:',.<>?/~",
    min_size=0,
    max_size=100,
)


# ─── Testes de propriedade ──────────────────────────────────────────────────────


class TestPropertyOCRPreservesOriginal:
    """Property 14: Falha total de OCR preserva original.

    **Validates: Requirements 8.6**
    """

    @given(
        original_content=_original_content,
        page_count=_page_count,
        primary_alnum=_illegible_alnum,
        secondary_alnum=_illegible_alnum,
        primary_padding=_non_alnum_padding,
        secondary_padding=_non_alnum_padding,
    )
    @settings(max_examples=300, deadline=None)
    def test_both_engines_illegible_preserves_original_bytes(
        self,
        original_content: bytes,
        page_count: int,
        primary_alnum: int,
        secondary_alnum: int,
        primary_padding: str,
        secondary_padding: str,
        tmp_path_factory,
    ):
        """Quando ambos motores retornam texto ilegível, o arquivo .md
        permanece idêntico ao original (byte a byte)."""
        tmp_path = tmp_path_factory.mktemp("ocr_preserve")

        # Criar arquivo .md com conteúdo original
        md_file = tmp_path / "output" / "documento.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_bytes(original_content)

        # Criar PDF fake
        pdf_file = tmp_path / "documento.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        # Garantir que texto retornado é ilegível (< 50 chars alnum por página)
        primary_text = "a" * primary_alnum + primary_padding
        secondary_text = "b" * secondary_alnum + secondary_padding

        # Motores que retornam texto ilegível
        primary = FailingOCREngine("Tesseract", primary_text)
        secondary = FailingOCREngine("EasyOCR", secondary_text)

        progress_queue = queue.Queue()
        manager = OCRManager(primary, secondary, progress_queue)

        candidate = OCRCandidate(
            source_pdf=pdf_file,
            output_md=md_file,
            page_count=page_count,
            alphanumeric_count=5,
        )

        result = manager._process_single(candidate, tmp_path / "output")

        # Verificar que o status é FAILED_ALL_ENGINES
        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE

        # Verificar que o conteúdo é byte-a-byte idêntico ao original
        preserved_content = md_file.read_bytes()
        assert preserved_content == original_content, (
            f"Conteúdo do arquivo alterado após falha de OCR. "
            f"Original: {len(original_content)} bytes, "
            f"Atual: {len(preserved_content)} bytes"
        )

    @given(
        original_content=_original_content,
        page_count=_page_count,
    )
    @settings(max_examples=200, deadline=None)
    def test_both_engines_exception_preserves_original_bytes(
        self,
        original_content: bytes,
        page_count: int,
        tmp_path_factory,
    ):
        """Quando ambos motores lançam exceção, o arquivo .md
        permanece idêntico ao original (byte a byte)."""
        tmp_path = tmp_path_factory.mktemp("ocr_exception")

        # Criar arquivo .md com conteúdo original
        md_file = tmp_path / "output" / "documento.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_bytes(original_content)

        # Criar PDF fake
        pdf_file = tmp_path / "documento.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        # Motores que lançam exceção
        primary = ExceptionOCREngine("Tesseract")
        secondary = ExceptionOCREngine("EasyOCR")

        progress_queue = queue.Queue()
        manager = OCRManager(primary, secondary, progress_queue)

        candidate = OCRCandidate(
            source_pdf=pdf_file,
            output_md=md_file,
            page_count=page_count,
            alphanumeric_count=5,
        )

        result = manager._process_single(candidate, tmp_path / "output")

        # Verificar que o status é FAILED_ALL_ENGINES
        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE

        # Verificar que o conteúdo é byte-a-byte idêntico ao original
        preserved_content = md_file.read_bytes()
        assert preserved_content == original_content, (
            f"Conteúdo do arquivo alterado após exceção de OCR. "
            f"Original: {len(original_content)} bytes, "
            f"Atual: {len(preserved_content)} bytes"
        )

    @given(
        original_content=_original_content,
        page_count=_page_count,
        primary_alnum=_illegible_alnum,
        primary_padding=_non_alnum_padding,
    )
    @settings(max_examples=200, deadline=None)
    def test_primary_illegible_secondary_exception_preserves_original(
        self,
        original_content: bytes,
        page_count: int,
        primary_alnum: int,
        primary_padding: str,
        tmp_path_factory,
    ):
        """Quando motor primário retorna ilegível e secundário lança exceção,
        o arquivo .md permanece idêntico ao original (byte a byte)."""
        tmp_path = tmp_path_factory.mktemp("ocr_mixed_fail")

        # Criar arquivo .md com conteúdo original
        md_file = tmp_path / "output" / "documento.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_bytes(original_content)

        # Criar PDF fake
        pdf_file = tmp_path / "documento.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        # Primário retorna ilegível, secundário lança exceção
        primary_text = "a" * primary_alnum + primary_padding
        primary = FailingOCREngine("Tesseract", primary_text)
        secondary = ExceptionOCREngine("EasyOCR")

        progress_queue = queue.Queue()
        manager = OCRManager(primary, secondary, progress_queue)

        candidate = OCRCandidate(
            source_pdf=pdf_file,
            output_md=md_file,
            page_count=page_count,
            alphanumeric_count=5,
        )

        result = manager._process_single(candidate, tmp_path / "output")

        # Verificar que o status é FAILED_ALL_ENGINES
        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE

        # Verificar que o conteúdo é byte-a-byte idêntico ao original
        preserved_content = md_file.read_bytes()
        assert preserved_content == original_content, (
            f"Conteúdo do arquivo alterado após falha mista de OCR. "
            f"Original: {len(original_content)} bytes, "
            f"Atual: {len(preserved_content)} bytes"
        )

    @given(
        original_content=_original_content,
        page_count=_page_count,
        secondary_alnum=_illegible_alnum,
        secondary_padding=_non_alnum_padding,
    )
    @settings(max_examples=200, deadline=None)
    def test_primary_exception_secondary_illegible_preserves_original(
        self,
        original_content: bytes,
        page_count: int,
        secondary_alnum: int,
        secondary_padding: str,
        tmp_path_factory,
    ):
        """Quando motor primário lança exceção e secundário retorna ilegível,
        o arquivo .md permanece idêntico ao original (byte a byte)."""
        tmp_path = tmp_path_factory.mktemp("ocr_mixed_fail2")

        # Criar arquivo .md com conteúdo original
        md_file = tmp_path / "output" / "documento.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_bytes(original_content)

        # Criar PDF fake
        pdf_file = tmp_path / "documento.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")

        # Primário lança exceção, secundário retorna ilegível
        primary = ExceptionOCREngine("Tesseract")
        secondary_text = "b" * secondary_alnum + secondary_padding
        secondary = FailingOCREngine("EasyOCR", secondary_text)

        progress_queue = queue.Queue()
        manager = OCRManager(primary, secondary, progress_queue)

        candidate = OCRCandidate(
            source_pdf=pdf_file,
            output_md=md_file,
            page_count=page_count,
            alphanumeric_count=5,
        )

        result = manager._process_single(candidate, tmp_path / "output")

        # Verificar que o status é FAILED_ALL_ENGINES
        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE

        # Verificar que o conteúdo é byte-a-byte idêntico ao original
        preserved_content = md_file.read_bytes()
        assert preserved_content == original_content, (
            f"Conteúdo do arquivo alterado após falha mista de OCR. "
            f"Original: {len(original_content)} bytes, "
            f"Atual: {len(preserved_content)} bytes"
        )
