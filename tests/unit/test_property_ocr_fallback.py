"""Testes de propriedade para cadeia de fallback OCR.

**Validates: Requirements 8.4, 8.5**

Property 13: Para qualquer PDF_Imagem processado pelo OCRManager, o motor
primário (Tesseract) SHALL ser invocado primeiro. Se o resultado do motor
primário tiver menos de 50 caracteres alfanuméricos por página, o motor
secundário (EasyOCR) SHALL ser invocado. Se o motor primário gerar resultado
legível (≥50 chars/página), o motor secundário SHALL não ser invocado.
"""

import queue
import tempfile
from pathlib import Path
from typing import Optional

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.models.data_models import OCRCandidate, OCREngineUsed, OCRStatus
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager


# ─── FakeEngine Mock ─────────────────────────────────────────────────────────


class FakeEngine(OCREngine):
    """Motor OCR falso com texto de retorno configurável e rastreamento de chamadas."""

    def __init__(self, engine_name: str, text_to_return: str, should_raise: bool = False) -> None:
        self._name = engine_name
        self._text_to_return = text_to_return
        self._should_raise = should_raise
        self.call_count = 0
        self.call_order: list[int] = []

    @property
    def name(self) -> str:
        return self._name

    def extract_text(self, pdf_path: Path) -> str:
        self.call_count += 1
        if self._should_raise:
            raise RuntimeError(f"{self._name} engine failure")
        return self._text_to_return


# ─── Estratégia: gerador de texto com densidade alfanumérica controlada ──────


def _build_text_with_alnum_density(alnum_count: int, padding: int = 10) -> str:
    """Constrói texto com exatamente alnum_count chars alfanuméricos."""
    return "a" * alnum_count + " " * padding


# Estratégias
_page_count = st.integers(min_value=1, max_value=20)
_legible_alnum_per_page = st.integers(min_value=50, max_value=200)
_illegible_alnum_per_page = st.integers(min_value=0, max_value=49)


# ─── Testes de propriedade ──────────────────────────────────────────────────────


class TestPropertyOCRFallback:
    """Property 13: Cadeia de fallback OCR.

    **Validates: Requirements 8.4, 8.5**
    """

    @given(
        page_count=_page_count,
        alnum_per_page=_legible_alnum_per_page,
    )
    @settings(max_examples=300, deadline=None)
    def test_primary_legible_secondary_not_called(
        self, page_count: int, alnum_per_page: int
    ):
        """Se o motor primário produz texto legível (≥50 chars/página),
        o motor secundário NÃO deve ser invocado."""
        total_alnum = alnum_per_page * page_count
        primary_text = _build_text_with_alnum_density(total_alnum)
        secondary_text = "anything"

        primary = FakeEngine("Tesseract", primary_text)
        secondary = FakeEngine("EasyOCR", secondary_text)
        progress_queue: queue.Queue = queue.Queue()

        manager = OCRManager(primary, secondary, progress_queue)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            # Criar arquivos mock
            source_pdf = tmp_path / "test.pdf"
            source_pdf.write_bytes(b"%PDF-mock")
            output_md = tmp_path / "test.md"
            output_md.write_text("original content", encoding="utf-8")

            candidate = OCRCandidate(
                source_pdf=source_pdf,
                output_md=output_md,
                page_count=page_count,
                alphanumeric_count=10,  # Valor baixo (é candidato OCR)
            )

            result = manager.process_batch([candidate], tmp_path)

        # Verificações
        assert primary.call_count == 1, (
            f"Motor primário deveria ser chamado exatamente 1 vez, foi chamado {primary.call_count}"
        )
        assert secondary.call_count == 0, (
            f"Motor secundário NÃO deveria ser chamado quando primário é legível, "
            f"mas foi chamado {secondary.call_count} vez(es)"
        )
        assert result.results[0].engine_used == OCREngineUsed.TESSERACT
        assert result.results[0].status == OCRStatus.SUCCESS

    @given(
        page_count=_page_count,
        primary_alnum_per_page=_illegible_alnum_per_page,
        secondary_alnum_per_page=_legible_alnum_per_page,
    )
    @settings(max_examples=300, deadline=None)
    def test_primary_illegible_secondary_called(
        self,
        page_count: int,
        primary_alnum_per_page: int,
        secondary_alnum_per_page: int,
    ):
        """Se o motor primário produz texto ilegível (<50 chars/página),
        o motor secundário DEVE ser invocado."""
        primary_total = primary_alnum_per_page * page_count
        secondary_total = secondary_alnum_per_page * page_count

        primary_text = _build_text_with_alnum_density(primary_total)
        secondary_text = _build_text_with_alnum_density(secondary_total)

        primary = FakeEngine("Tesseract", primary_text)
        secondary = FakeEngine("EasyOCR", secondary_text)
        progress_queue: queue.Queue = queue.Queue()

        manager = OCRManager(primary, secondary, progress_queue)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_pdf = tmp_path / "test.pdf"
            source_pdf.write_bytes(b"%PDF-mock")
            output_md = tmp_path / "test.md"
            output_md.write_text("original content", encoding="utf-8")

            candidate = OCRCandidate(
                source_pdf=source_pdf,
                output_md=output_md,
                page_count=page_count,
                alphanumeric_count=10,
            )

            result = manager.process_batch([candidate], tmp_path)

        # Verificações
        assert primary.call_count == 1, (
            f"Motor primário deveria ser chamado exatamente 1 vez, foi chamado {primary.call_count}"
        )
        assert secondary.call_count == 1, (
            f"Motor secundário deveria ser chamado quando primário é ilegível, "
            f"mas foi chamado {secondary.call_count} vez(es)"
        )
        assert result.results[0].engine_used == OCREngineUsed.EASYOCR
        assert result.results[0].status == OCRStatus.SUCCESS

    @given(
        page_count=_page_count,
        primary_alnum_per_page=_illegible_alnum_per_page,
        secondary_alnum_per_page=_illegible_alnum_per_page,
    )
    @settings(max_examples=300, deadline=None)
    def test_both_illegible_secondary_still_called(
        self,
        page_count: int,
        primary_alnum_per_page: int,
        secondary_alnum_per_page: int,
    ):
        """Se ambos os motores produzem texto ilegível, o secundário DEVE
        ser invocado (tentativa de fallback) e o status final é FAILED_ALL_ENGINES."""
        primary_total = primary_alnum_per_page * page_count
        secondary_total = secondary_alnum_per_page * page_count

        primary_text = _build_text_with_alnum_density(primary_total)
        secondary_text = _build_text_with_alnum_density(secondary_total)

        primary = FakeEngine("Tesseract", primary_text)
        secondary = FakeEngine("EasyOCR", secondary_text)
        progress_queue: queue.Queue = queue.Queue()

        manager = OCRManager(primary, secondary, progress_queue)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_pdf = tmp_path / "test.pdf"
            source_pdf.write_bytes(b"%PDF-mock")
            output_md = tmp_path / "test.md"
            output_md.write_text("original content", encoding="utf-8")

            candidate = OCRCandidate(
                source_pdf=source_pdf,
                output_md=output_md,
                page_count=page_count,
                alphanumeric_count=10,
            )

            result = manager.process_batch([candidate], tmp_path)

        # Ambos devem ser chamados
        assert primary.call_count == 1, (
            f"Motor primário deveria ser chamado 1 vez, foi chamado {primary.call_count}"
        )
        assert secondary.call_count == 1, (
            f"Motor secundário deveria ser chamado 1 vez quando primário ilegível, "
            f"foi chamado {secondary.call_count}"
        )
        assert result.results[0].status == OCRStatus.FAILED_ALL_ENGINES
        assert result.results[0].engine_used == OCREngineUsed.NONE

    @given(
        page_count=_page_count,
        secondary_alnum_per_page=_legible_alnum_per_page,
    )
    @settings(max_examples=200, deadline=None)
    def test_primary_raises_exception_secondary_called(
        self,
        page_count: int,
        secondary_alnum_per_page: int,
    ):
        """Se o motor primário lança exceção, o secundário DEVE ser invocado."""
        secondary_total = secondary_alnum_per_page * page_count
        secondary_text = _build_text_with_alnum_density(secondary_total)

        primary = FakeEngine("Tesseract", "", should_raise=True)
        secondary = FakeEngine("EasyOCR", secondary_text)
        progress_queue: queue.Queue = queue.Queue()

        manager = OCRManager(primary, secondary, progress_queue)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            source_pdf = tmp_path / "test.pdf"
            source_pdf.write_bytes(b"%PDF-mock")
            output_md = tmp_path / "test.md"
            output_md.write_text("original content", encoding="utf-8")

            candidate = OCRCandidate(
                source_pdf=source_pdf,
                output_md=output_md,
                page_count=page_count,
                alphanumeric_count=10,
            )

            result = manager.process_batch([candidate], tmp_path)

        # Primário chamado (e falhou com exceção), secundário chamado
        assert primary.call_count == 1, "Primário deveria ser tentado primeiro"
        assert secondary.call_count == 1, (
            "Secundário deveria ser chamado quando primário lança exceção"
        )
        assert result.results[0].engine_used == OCREngineUsed.EASYOCR
        assert result.results[0].status == OCRStatus.SUCCESS

    @given(
        page_count=_page_count,
        num_candidates=st.integers(min_value=1, max_value=5),
        primary_legible=st.lists(st.booleans(), min_size=1, max_size=5),
    )
    @settings(max_examples=200, deadline=None)
    def test_primary_always_called_first_for_every_candidate(
        self,
        page_count: int,
        num_candidates: int,
        primary_legible: list[bool],
    ):
        """Para CADA candidato em um batch, o motor primário é SEMPRE invocado primeiro."""
        # Ajustar lista para ter exatamente num_candidates itens
        legible_flags = primary_legible[:num_candidates]
        while len(legible_flags) < num_candidates:
            legible_flags.append(True)

        # Usamos um FakeEngine com rastreamento de ordem global
        call_log: list[str] = []

        class OrderTrackingEngine(OCREngine):
            def __init__(self, engine_name: str, texts: list[str]) -> None:
                self._name = engine_name
                self._texts = texts
                self._call_idx = 0

            @property
            def name(self) -> str:
                return self._name

            def extract_text(self, pdf_path: Path) -> str:
                call_log.append(self._name)
                text = self._texts[self._call_idx] if self._call_idx < len(self._texts) else ""
                self._call_idx += 1
                return text

        # Preparar textos para cada candidato
        primary_texts = []
        secondary_texts = []
        for is_legible in legible_flags:
            if is_legible:
                primary_texts.append("a" * (50 * page_count + 10))
            else:
                primary_texts.append("a" * (10))  # Ilegível
            secondary_texts.append("a" * (50 * page_count + 10))  # Secundário sempre legível

        primary = OrderTrackingEngine("Tesseract", primary_texts)
        secondary = OrderTrackingEngine("EasyOCR", secondary_texts)
        progress_queue: queue.Queue = queue.Queue()

        manager = OCRManager(primary, secondary, progress_queue)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            candidates = []
            for i in range(num_candidates):
                source_pdf = tmp_path / f"test_{i}.pdf"
                source_pdf.write_bytes(b"%PDF-mock")
                output_md = tmp_path / f"test_{i}.md"
                output_md.write_text("original content", encoding="utf-8")
                candidates.append(
                    OCRCandidate(
                        source_pdf=source_pdf,
                        output_md=output_md,
                        page_count=page_count,
                        alphanumeric_count=10,
                    )
                )

            manager.process_batch(candidates, tmp_path)

        # Verificar que para cada candidato, Tesseract é chamado antes de EasyOCR
        # O log deve ter padrão: Tesseract [EasyOCR]? Tesseract [EasyOCR]? ...
        idx = 0
        for i, is_legible in enumerate(legible_flags):
            assert idx < len(call_log), f"Faltam chamadas no log para candidato {i}"
            assert call_log[idx] == "Tesseract", (
                f"Para candidato {i}, esperava Tesseract primeiro mas obteve {call_log[idx]}. "
                f"Log completo: {call_log}"
            )
            idx += 1
            if not is_legible:
                assert idx < len(call_log), f"Faltam chamadas secundárias no log para candidato {i}"
                assert call_log[idx] == "EasyOCR", (
                    f"Para candidato {i} (primário ilegível), esperava EasyOCR mas obteve {call_log[idx]}. "
                    f"Log completo: {call_log}"
                )
                idx += 1
