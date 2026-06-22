"""Testes de propriedade para completude do resumo OCR.

**Validates: Requirements 8.8**

Property 16: Completude do resumo OCR
Para qualquer OCRBatchResult gerado pelo OCRManager, o resultado deve satisfazer
`recovered + failed == total`, e cada OCRFileResult deve conter um engine_used
válido (TESSERACT, EASYOCR ou NONE para falhas).
"""

import queue
import tempfile
from pathlib import Path

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.models.data_models import (
    OCRBatchResult,
    OCRCandidate,
    OCREngineUsed,
    OCRFileResult,
    OCRStatus,
)
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager


# ─── Motores OCR fake para testes ─────────────────────────────────────────────


class FakeTesseractEngine(OCREngine):
    """Motor OCR fake que simula Tesseract com resultado configurável."""

    def __init__(self, results: dict[str, str] | None = None) -> None:
        self._results = results or {}

    @property
    def name(self) -> str:
        return "Tesseract"

    def extract_text(self, pdf_path: Path) -> str:
        return self._results.get(str(pdf_path), "")


class FakeEasyOCREngine(OCREngine):
    """Motor OCR fake que simula EasyOCR com resultado configurável."""

    def __init__(self, results: dict[str, str] | None = None) -> None:
        self._results = results or {}

    @property
    def name(self) -> str:
        return "EasyOCR"

    def extract_text(self, pdf_path: Path) -> str:
        return self._results.get(str(pdf_path), "")


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Resultado de cada arquivo: sucesso com tesseract, sucesso com easyocr, ou falha
_outcome = st.sampled_from(["tesseract_success", "easyocr_success", "both_fail"])

# Nomes de arquivo PDF aleatórios (garantindo unicidade via filtro)
_pdf_filename = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=20,
).map(lambda name: f"{name}.pdf")

# Gera batches de candidatos com outcomes associados
_batch = st.integers(min_value=1, max_value=20).flatmap(
    lambda n: st.lists(
        st.tuples(_pdf_filename, _outcome, st.integers(min_value=1, max_value=10)),
        min_size=n,
        max_size=n,
    )
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _build_test_scenario(
    batch: list[tuple[str, str, int]],
    tmp_dir: Path,
) -> tuple[list[OCRCandidate], FakeTesseractEngine, FakeEasyOCREngine]:
    """Constrói candidatos OCR e motores fake com base nos outcomes gerados.

    Args:
        batch: Lista de (nome_arquivo, outcome, page_count).
        tmp_dir: Diretório temporário para os arquivos .md.

    Returns:
        Tupla com candidatos, motor tesseract fake e motor easyocr fake.
    """
    candidates: list[OCRCandidate] = []
    tesseract_results: dict[str, str] = {}
    easyocr_results: dict[str, str] = {}

    for filename, outcome, page_count in batch:
        source_pdf = tmp_dir / filename
        output_md = tmp_dir / filename.replace(".pdf", ".md")

        # Cria arquivo .md com conteúdo original mínimo
        output_md.write_text("original content", encoding="utf-8")

        candidate = OCRCandidate(
            source_pdf=source_pdf,
            output_md=output_md,
            page_count=page_count,
            alphanumeric_count=5,  # abaixo do threshold para ser candidato OCR
        )
        candidates.append(candidate)

        # Limiar: 50 chars alfanuméricos por página
        legible_text = "a" * (50 * page_count)
        illegible_text = "a" * (50 * page_count - 1) if page_count > 0 else ""

        pdf_key = str(source_pdf)

        if outcome == "tesseract_success":
            tesseract_results[pdf_key] = legible_text
            easyocr_results[pdf_key] = illegible_text
        elif outcome == "easyocr_success":
            tesseract_results[pdf_key] = illegible_text
            easyocr_results[pdf_key] = legible_text
        else:  # both_fail
            tesseract_results[pdf_key] = illegible_text
            easyocr_results[pdf_key] = illegible_text

    tesseract_engine = FakeTesseractEngine(results=tesseract_results)
    easyocr_engine = FakeEasyOCREngine(results=easyocr_results)

    return candidates, tesseract_engine, easyocr_engine


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyOCRSummaryCompleteness:
    """Property 16: Completude do resumo OCR.

    **Validates: Requirements 8.8**
    """

    @given(batch=_batch)
    @settings(max_examples=100)
    def test_recovered_plus_failed_equals_total(
        self, batch: list[tuple[str, str, int]]
    ) -> None:
        """recovered + failed == total para qualquer batch processado."""
        # Garante nomes únicos no batch
        filenames = [item[0] for item in batch]
        assume(len(set(filenames)) == len(filenames))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidates, tesseract_engine, easyocr_engine = _build_test_scenario(batch, tmp_path)
            progress_queue: queue.Queue = queue.Queue()

            manager = OCRManager(
                primary_engine=tesseract_engine,
                secondary_engine=easyocr_engine,
                progress_queue=progress_queue,
            )

            result: OCRBatchResult = manager.process_batch(candidates, tmp_path)

            assert result.recovered + result.failed == result.total, (
                f"recovered ({result.recovered}) + failed ({result.failed}) "
                f"!= total ({result.total})"
            )

    @given(batch=_batch)
    @settings(max_examples=100)
    def test_total_equals_batch_size(
        self, batch: list[tuple[str, str, int]]
    ) -> None:
        """total deve ser igual ao número de candidatos no batch."""
        filenames = [item[0] for item in batch]
        assume(len(set(filenames)) == len(filenames))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidates, tesseract_engine, easyocr_engine = _build_test_scenario(batch, tmp_path)
            progress_queue: queue.Queue = queue.Queue()

            manager = OCRManager(
                primary_engine=tesseract_engine,
                secondary_engine=easyocr_engine,
                progress_queue=progress_queue,
            )

            result: OCRBatchResult = manager.process_batch(candidates, tmp_path)

            assert result.total == len(batch), (
                f"total ({result.total}) != len(batch) ({len(batch)})"
            )

    @given(batch=_batch)
    @settings(max_examples=100)
    def test_each_result_has_valid_engine_used(
        self, batch: list[tuple[str, str, int]]
    ) -> None:
        """Cada OCRFileResult deve ter engine_used válido (TESSERACT, EASYOCR ou NONE)."""
        filenames = [item[0] for item in batch]
        assume(len(set(filenames)) == len(filenames))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidates, tesseract_engine, easyocr_engine = _build_test_scenario(batch, tmp_path)
            progress_queue: queue.Queue = queue.Queue()

            manager = OCRManager(
                primary_engine=tesseract_engine,
                secondary_engine=easyocr_engine,
                progress_queue=progress_queue,
            )

            result: OCRBatchResult = manager.process_batch(candidates, tmp_path)
            valid_engines = {OCREngineUsed.TESSERACT, OCREngineUsed.EASYOCR, OCREngineUsed.NONE}

            for file_result in result.results:
                assert file_result.engine_used in valid_engines, (
                    f"engine_used inválido: {file_result.engine_used} "
                    f"para {file_result.source_pdf}"
                )

    @given(batch=_batch)
    @settings(max_examples=100)
    def test_engine_used_matches_status(
        self, batch: list[tuple[str, str, int]]
    ) -> None:
        """engine_used NONE somente quando status é FAILED_ALL_ENGINES; caso contrário TESSERACT ou EASYOCR."""
        filenames = [item[0] for item in batch]
        assume(len(set(filenames)) == len(filenames))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidates, tesseract_engine, easyocr_engine = _build_test_scenario(batch, tmp_path)
            progress_queue: queue.Queue = queue.Queue()

            manager = OCRManager(
                primary_engine=tesseract_engine,
                secondary_engine=easyocr_engine,
                progress_queue=progress_queue,
            )

            result: OCRBatchResult = manager.process_batch(candidates, tmp_path)

            for file_result in result.results:
                if file_result.status == OCRStatus.SUCCESS:
                    assert file_result.engine_used in {OCREngineUsed.TESSERACT, OCREngineUsed.EASYOCR}, (
                        f"Arquivo com status SUCCESS deve ter engine_used TESSERACT ou EASYOCR, "
                        f"obtido: {file_result.engine_used}"
                    )
                elif file_result.status == OCRStatus.FAILED_ALL_ENGINES:
                    assert file_result.engine_used == OCREngineUsed.NONE, (
                        f"Arquivo com status FAILED_ALL_ENGINES deve ter engine_used NONE, "
                        f"obtido: {file_result.engine_used}"
                    )

    @given(batch=_batch)
    @settings(max_examples=100)
    def test_results_list_length_equals_total(
        self, batch: list[tuple[str, str, int]]
    ) -> None:
        """A lista de results deve ter exatamente 'total' elementos."""
        filenames = [item[0] for item in batch]
        assume(len(set(filenames)) == len(filenames))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            candidates, tesseract_engine, easyocr_engine = _build_test_scenario(batch, tmp_path)
            progress_queue: queue.Queue = queue.Queue()

            manager = OCRManager(
                primary_engine=tesseract_engine,
                secondary_engine=easyocr_engine,
                progress_queue=progress_queue,
            )

            result: OCRBatchResult = manager.process_batch(candidates, tmp_path)

            assert len(result.results) == result.total, (
                f"len(results) ({len(result.results)}) != total ({result.total})"
            )
