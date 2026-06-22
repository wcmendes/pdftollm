"""Testes de propriedade para consistência de progresso OCR.

**Validates: Requirements 8.7**

Property 15: Consistência de progresso OCR
Para qualquer batch de N PDFs_Imagem processados pelo OCRManager, o sistema deve
emitir exatamente N mensagens de progresso OCR, com índice (current_index)
monotonicamente crescente de 1 a N.
"""

import queue
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.data_models import OCRCandidate
from src.ocr.ocr_engine import OCREngine
from src.ocr.ocr_manager import OCRManager


# ─── Motor OCR fake para testes ───────────────────────────────────────────────


class _FakeOCREngine(OCREngine):
    """Motor OCR fake que retorna texto configurável."""

    def __init__(self, engine_name: str, text: str = "") -> None:
        self._name = engine_name
        self._text = text

    @property
    def name(self) -> str:
        return self._name

    def extract_text(self, pdf_path: Path) -> str:
        return self._text


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Tamanho do batch OCR: de 1 a 20
_batch_size = st.integers(min_value=1, max_value=20)


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyOCRProgressConsistency:
    """Property 15: Consistência de progresso OCR.

    **Validates: Requirements 8.7**
    """

    @given(n=_batch_size)
    @settings(max_examples=100)
    def test_exactly_n_progress_messages(self, n: int) -> None:
        """Para um batch de N candidatos OCR, devem ser emitidas exatamente N mensagens de progresso."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            progress_queue: queue.Queue = queue.Queue()

            # Motor primário retorna texto legível (>= 50 chars/página)
            primary = _FakeOCREngine("Tesseract", "a" * 200)
            secondary = _FakeOCREngine("EasyOCR", "b" * 200)
            manager = OCRManager(primary, secondary, progress_queue)

            # Cria N candidatos OCR
            candidates = _create_candidates(n, tmp_path)

            manager.process_batch(candidates, tmp_path / "output")

            # Coleta todas as mensagens da fila
            messages = _drain_queue(progress_queue)

            assert len(messages) == n, (
                f"Esperadas {n} mensagens de progresso OCR, obtidas {len(messages)}"
            )

    @given(n=_batch_size)
    @settings(max_examples=100)
    def test_current_index_from_1_to_n(self, n: int) -> None:
        """current_index das mensagens de progresso OCR deve ir de 1 a N sequencialmente."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            progress_queue: queue.Queue = queue.Queue()

            primary = _FakeOCREngine("Tesseract", "a" * 200)
            secondary = _FakeOCREngine("EasyOCR", "b" * 200)
            manager = OCRManager(primary, secondary, progress_queue)

            candidates = _create_candidates(n, tmp_path)

            manager.process_batch(candidates, tmp_path / "output")

            messages = _drain_queue(progress_queue)
            indices = [msg["current_index"] for msg in messages]
            expected = list(range(1, n + 1))

            assert indices == expected, (
                f"Índices esperados {expected}, obtidos {indices}"
            )

    @given(n=_batch_size)
    @settings(max_examples=100)
    def test_progress_messages_with_mixed_results(self, n: int) -> None:
        """Mesmo com motores falhando, emite exatamente N mensagens com índice de 1 a N."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            progress_queue: queue.Queue = queue.Queue()

            # Ambos motores retornam texto ilegível (< 50 chars por página)
            primary = _FakeOCREngine("Tesseract", "x" * 10)
            secondary = _FakeOCREngine("EasyOCR", "y" * 10)
            manager = OCRManager(primary, secondary, progress_queue)

            candidates = _create_candidates(n, tmp_path)

            manager.process_batch(candidates, tmp_path / "output")

            messages = _drain_queue(progress_queue)

            # Verifica quantidade exata
            assert len(messages) == n, (
                f"Esperadas {n} mensagens, obtidas {len(messages)}"
            )

            # Verifica índices sequenciais de 1 a N
            indices = [msg["current_index"] for msg in messages]
            expected = list(range(1, n + 1))
            assert indices == expected, (
                f"Índices esperados {expected}, obtidos {indices}"
            )


# ─── Funções auxiliares ───────────────────────────────────────────────────────


def _create_candidates(n: int, tmp_path: Path) -> list[OCRCandidate]:
    """Cria N candidatos OCR com arquivos temporários."""
    candidates = []
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n):
        pdf_file = tmp_path / f"doc_{i}.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
        md_file = output_dir / f"doc_{i}.md"
        md_file.write_text("conteudo original ilegivel", encoding="utf-8")
        candidates.append(
            OCRCandidate(
                source_pdf=pdf_file,
                output_md=md_file,
                page_count=2,
                alphanumeric_count=10,
            )
        )
    return candidates


def _drain_queue(q: queue.Queue) -> list[dict]:
    """Drena todas as mensagens de uma fila e retorna como lista."""
    messages = []
    while not q.empty():
        messages.append(q.get_nowait())
    return messages
