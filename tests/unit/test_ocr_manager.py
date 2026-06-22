"""Testes unitários para OCRManager."""

import queue
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models.data_models import (
    OCRBatchResult,
    OCRCandidate,
    OCREngineUsed,
    OCRFileResult,
    OCRStatus,
)
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager


class FakeEngine(OCREngine):
    """Motor OCR fake para testes."""

    def __init__(self, engine_name: str, text_to_return: str = "") -> None:
        self._name = engine_name
        self._text_to_return = text_to_return
        self._called = False
        self._raise_on_call = False

    @property
    def name(self) -> str:
        return self._name

    def extract_text(self, pdf_path: Path) -> str:
        self._called = True
        if self._raise_on_call:
            raise RuntimeError(f"{self._name} engine error")
        return self._text_to_return


@pytest.fixture
def progress_queue():
    """Fila de progresso para testes."""
    return queue.Queue()


@pytest.fixture
def tmp_md_file(tmp_path):
    """Cria um arquivo .md temporário com conteúdo original."""
    md_file = tmp_path / "output" / "test_doc.md"
    md_file.parent.mkdir(parents=True, exist_ok=True)
    md_file.write_text("conteúdo original ilegível", encoding="utf-8")
    return md_file


@pytest.fixture
def sample_candidate(tmp_path, tmp_md_file):
    """Cria um OCRCandidate de exemplo."""
    pdf_file = tmp_path / "test_doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake content")
    return OCRCandidate(
        source_pdf=pdf_file,
        output_md=tmp_md_file,
        page_count=2,
        alphanumeric_count=10,
    )


class TestOCRManagerInit:
    """Testes de inicialização do OCRManager."""

    def test_init_sets_engines_and_queue(self, progress_queue):
        """OCRManager armazena motores e fila corretamente."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")

        manager = OCRManager(primary, secondary, progress_queue)

        assert manager._primary_engine is primary
        assert manager._secondary_engine is secondary
        assert manager._progress_queue is progress_queue

    def test_legibility_threshold_is_50(self):
        """Threshold de legibilidade deve ser 50."""
        assert OCRManager.LEGIBILITY_THRESHOLD == 50


class TestOCRManagerIsLegible:
    """Testes para o método _is_legible."""

    def test_legible_text_above_threshold(self, progress_queue):
        """Texto com >= 50 chars alfanuméricos por página é legível."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        # 100 alphanumeric chars, 2 pages = 50 per page
        text = "a" * 100
        assert manager._is_legible(text, 2) is True

    def test_illegible_text_below_threshold(self, progress_queue):
        """Texto com < 50 chars alfanuméricos por página é ilegível."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        # 49 alphanumeric chars, 1 page = 49 per page
        text = "a" * 49
        assert manager._is_legible(text, 1) is False

    def test_exactly_at_threshold_is_legible(self, progress_queue):
        """Texto com exatamente 50 chars por página é legível."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        text = "a" * 50
        assert manager._is_legible(text, 1) is True

    def test_zero_pages_is_illegible(self, progress_queue):
        """Zero páginas sempre retorna ilegível."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        assert manager._is_legible("some text", 0) is False

    def test_non_alphanumeric_not_counted(self, progress_queue):
        """Apenas caracteres alfanuméricos são contados."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        # Lots of non-alphanumeric + only 10 alphanumeric
        text = "!@#$%^&*() " * 50 + "a" * 10
        assert manager._is_legible(text, 1) is False


class TestOCRManagerProcessSingle:
    """Testes para _process_single."""

    def test_primary_engine_success(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """Retorna SUCCESS/TESSERACT quando motor primário gera texto legível."""
        # 200 alphanumeric chars, 2 pages = 100 per page (legible)
        primary = FakeEngine("Tesseract", "a" * 200)
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager._process_single(sample_candidate, tmp_path / "output")

        assert result.status == OCRStatus.SUCCESS
        assert result.engine_used == OCREngineUsed.TESSERACT
        assert result.source_pdf == sample_candidate.source_pdf
        assert result.output_md == sample_candidate.output_md
        # Secondary should not have been called
        assert secondary._called is False

    def test_primary_fails_secondary_success(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """Fallback para EasyOCR quando Tesseract gera texto ilegível."""
        # Primary returns illegible (too few chars)
        primary = FakeEngine("Tesseract", "a" * 10)
        # Secondary returns legible
        secondary = FakeEngine("EasyOCR", "b" * 200)
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager._process_single(sample_candidate, tmp_path / "output")

        assert result.status == OCRStatus.SUCCESS
        assert result.engine_used == OCREngineUsed.EASYOCR
        assert secondary._called is True

    def test_both_engines_fail_restores_original(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """Restaura conteúdo original quando ambos motores falham."""
        original_content = sample_candidate.output_md.read_bytes()

        # Both return illegible text
        primary = FakeEngine("Tesseract", "a" * 10)
        secondary = FakeEngine("EasyOCR", "b" * 10)
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager._process_single(sample_candidate, tmp_path / "output")

        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE
        assert result.error_message != ""
        # Original content should be restored
        assert sample_candidate.output_md.read_bytes() == original_content

    def test_primary_exception_falls_through_to_secondary(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """Se motor primário lança exceção, tenta secundário."""
        primary = FakeEngine("Tesseract")
        primary._raise_on_call = True
        secondary = FakeEngine("EasyOCR", "b" * 200)
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager._process_single(sample_candidate, tmp_path / "output")

        assert result.status == OCRStatus.SUCCESS
        assert result.engine_used == OCREngineUsed.EASYOCR

    def test_both_engines_exception_restores_original(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """Se ambos motores lançam exceção, restaura original."""
        original_content = sample_candidate.output_md.read_bytes()

        primary = FakeEngine("Tesseract")
        primary._raise_on_call = True
        secondary = FakeEngine("EasyOCR")
        secondary._raise_on_call = True
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager._process_single(sample_candidate, tmp_path / "output")

        assert result.status == OCRStatus.FAILED_ALL_ENGINES
        assert result.engine_used == OCREngineUsed.NONE
        assert sample_candidate.output_md.read_bytes() == original_content

    def test_successful_ocr_writes_new_markdown(
        self, progress_queue, sample_candidate, tmp_path
    ):
        """OCR bem-sucedido escreve novo conteúdo no arquivo .md."""
        ocr_text = "Texto extraído via OCR com muitos caracteres " + "x" * 200
        primary = FakeEngine("Tesseract", ocr_text)
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        manager._process_single(sample_candidate, tmp_path / "output")

        new_content = sample_candidate.output_md.read_text(encoding="utf-8")
        assert new_content == ocr_text


class TestOCRManagerProcessBatch:
    """Testes para process_batch."""

    def test_empty_batch_returns_zeros(self, progress_queue, tmp_path):
        """Batch vazio retorna resultados zerados."""
        primary = FakeEngine("Tesseract")
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        result = manager.process_batch([], tmp_path)

        assert result.total == 0
        assert result.recovered == 0
        assert result.failed == 0
        assert result.results == []

    def test_all_success_counts(self, progress_queue, tmp_path):
        """Batch onde todos são recuperados atualiza contadores corretamente."""
        primary = FakeEngine("Tesseract", "a" * 200)
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        # Create 3 candidates
        candidates = []
        for i in range(3):
            md_file = tmp_path / "output" / f"doc{i}.md"
            md_file.parent.mkdir(parents=True, exist_ok=True)
            md_file.write_text("original", encoding="utf-8")
            pdf_file = tmp_path / f"doc{i}.pdf"
            pdf_file.write_bytes(b"%PDF")
            candidates.append(
                OCRCandidate(
                    source_pdf=pdf_file,
                    output_md=md_file,
                    page_count=2,
                    alphanumeric_count=5,
                )
            )

        result = manager.process_batch(candidates, tmp_path / "output")

        assert result.total == 3
        assert result.recovered == 3
        assert result.failed == 0
        assert len(result.results) == 3

    def test_all_failed_counts(self, progress_queue, tmp_path):
        """Batch onde todos falham atualiza contadores corretamente."""
        primary = FakeEngine("Tesseract", "a" * 5)  # illegible
        secondary = FakeEngine("EasyOCR", "b" * 5)  # illegible
        manager = OCRManager(primary, secondary, progress_queue)

        candidates = []
        for i in range(2):
            md_file = tmp_path / "output" / f"doc{i}.md"
            md_file.parent.mkdir(parents=True, exist_ok=True)
            md_file.write_text("original", encoding="utf-8")
            pdf_file = tmp_path / f"doc{i}.pdf"
            pdf_file.write_bytes(b"%PDF")
            candidates.append(
                OCRCandidate(
                    source_pdf=pdf_file,
                    output_md=md_file,
                    page_count=2,
                    alphanumeric_count=5,
                )
            )

        result = manager.process_batch(candidates, tmp_path / "output")

        assert result.total == 2
        assert result.recovered == 0
        assert result.failed == 2

    def test_mixed_results_counts(self, progress_queue, tmp_path):
        """Batch misto (sucesso + falha) contabiliza corretamente."""
        # Primary will return legible text based on page count
        # We'll use different candidates with different page counts
        primary = FakeEngine("Tesseract", "a" * 100)  # 100 chars
        secondary = FakeEngine("EasyOCR", "b" * 5)  # illegible
        manager = OCRManager(primary, secondary, progress_queue)

        # Candidate 1: page_count=1 → 100/1=100 >= 50 → legible
        md1 = tmp_path / "output" / "doc_legible.md"
        md1.parent.mkdir(parents=True, exist_ok=True)
        md1.write_text("original1", encoding="utf-8")
        pdf1 = tmp_path / "doc_legible.pdf"
        pdf1.write_bytes(b"%PDF")
        c1 = OCRCandidate(
            source_pdf=pdf1, output_md=md1, page_count=1, alphanumeric_count=5
        )

        # Candidate 2: page_count=3 → 100/3=33 < 50 → illegible from both
        md2 = tmp_path / "output" / "doc_illegible.md"
        md2.write_text("original2", encoding="utf-8")
        pdf2 = tmp_path / "doc_illegible.pdf"
        pdf2.write_bytes(b"%PDF")
        c2 = OCRCandidate(
            source_pdf=pdf2, output_md=md2, page_count=3, alphanumeric_count=5
        )

        result = manager.process_batch([c1, c2], tmp_path / "output")

        assert result.total == 2
        assert result.recovered == 1
        assert result.failed == 1
        assert result.recovered + result.failed == result.total

    def test_progress_messages_emitted(self, progress_queue, tmp_path):
        """Emite uma mensagem de progresso para cada arquivo processado."""
        primary = FakeEngine("Tesseract", "a" * 200)
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        candidates = []
        for i in range(3):
            md_file = tmp_path / "output" / f"doc{i}.md"
            md_file.parent.mkdir(parents=True, exist_ok=True)
            md_file.write_text("original", encoding="utf-8")
            pdf_file = tmp_path / f"doc{i}.pdf"
            pdf_file.write_bytes(b"%PDF")
            candidates.append(
                OCRCandidate(
                    source_pdf=pdf_file,
                    output_md=md_file,
                    page_count=2,
                    alphanumeric_count=5,
                )
            )

        manager.process_batch(candidates, tmp_path / "output")

        # Should have 3 progress messages in the queue
        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        assert len(messages) == 3
        # Verify monotonically increasing index
        for i, msg in enumerate(messages, start=1):
            assert msg["type"] == "ocr_progress"
            assert msg["current_index"] == i
            assert msg["total"] == 3

    def test_progress_messages_contain_file_info(self, progress_queue, tmp_path):
        """Mensagens de progresso contêm informações do arquivo."""
        primary = FakeEngine("Tesseract", "a" * 200)
        secondary = FakeEngine("EasyOCR")
        manager = OCRManager(primary, secondary, progress_queue)

        md_file = tmp_path / "output" / "meu_doc.md"
        md_file.parent.mkdir(parents=True, exist_ok=True)
        md_file.write_text("original", encoding="utf-8")
        pdf_file = tmp_path / "meu_doc.pdf"
        pdf_file.write_bytes(b"%PDF")
        candidate = OCRCandidate(
            source_pdf=pdf_file,
            output_md=md_file,
            page_count=2,
            alphanumeric_count=5,
        )

        manager.process_batch([candidate], tmp_path / "output")

        msg = progress_queue.get_nowait()
        assert msg["filename"] == "meu_doc.pdf"
        assert msg["status"] == "success"
        assert msg["engine_used"] == "tesseract"


class TestOCRManagerWriteMarkdown:
    """Testes para _write_markdown."""

    def test_writes_utf8_with_lf(self, tmp_path):
        """Escreve arquivo com codificação UTF-8 e terminadores LF."""
        md_file = tmp_path / "output.md"
        text = "Olá mundo\r\nSegunda linha\rTerceira linha\nQuarta"

        OCRManager._write_markdown(md_file, text)

        content = md_file.read_bytes()
        # Should not contain \r\n or lone \r
        assert b"\r\n" not in content
        assert b"\r" not in content
        # Should contain LF
        assert b"\n" in content
        # Verify text content
        text_content = content.decode("utf-8")
        assert "Olá mundo" in text_content
        assert "Segunda linha" in text_content

    def test_writes_unicode_correctly(self, tmp_path):
        """Escreve caracteres Unicode corretamente."""
        md_file = tmp_path / "unicode.md"
        text = "Acentuação: ã é ç ü ñ — 中文 日本語"

        OCRManager._write_markdown(md_file, text)

        content = md_file.read_text(encoding="utf-8")
        assert content == text
