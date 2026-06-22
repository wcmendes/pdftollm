"""Testes de propriedade para consistência de progresso do ConversionManager.

**Validates: Requirements 3.1, 5.1**

Property 4: Consistência de progresso
Para qualquer batch de N arquivos, o ConversionManager deve emitir exatamente N
mensagens de ProgressUpdate intermediárias, onde cada mensagem tem `current_index`
monotonicamente crescente de 1 a N, e a última mensagem (final) tem
`is_complete == True`.
"""

import queue
from pathlib import Path
from unittest.mock import patch, MagicMock

from hypothesis import given, settings
from hypothesis import strategies as st

from src.converters.conversion_manager import ConversionManager
from src.models.data_models import (
    ConversionFileResult,
    ConversionStatus,
    ProgressUpdate,
)


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Tamanho do batch: de 1 a 30 arquivos
_batch_size = st.integers(min_value=1, max_value=30)

# Gera nomes de arquivo PDF aleatórios
_pdf_filename = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "Pd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
).map(lambda name: Path(f"{name}.pdf"))

# Gera listas de arquivos PDF com tamanho variável (1 a 30)
_file_list = st.integers(min_value=1, max_value=30).flatmap(
    lambda n: st.lists(_pdf_filename, min_size=n, max_size=n)
)

# Status possíveis para cada conversão individual (sucesso ou falha)
_conversion_status = st.sampled_from([
    ConversionStatus.SUCCESS,
    ConversionStatus.FAILED_CORRUPTED,
    ConversionStatus.FAILED_PASSWORD,
    ConversionStatus.FAILED_IO_ERROR,
])


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyProgressConsistency:
    """Property 4: Consistência de progresso.

    **Validates: Requirements 3.1, 5.1**
    """

    @given(files=_file_list, statuses=st.data())
    @settings(max_examples=100)
    def test_exactly_n_intermediate_messages(self, files: list[Path], statuses: st.DataObject) -> None:
        """Para um batch de N arquivos, devem ser emitidas exatamente N mensagens intermediárias."""
        n = len(files)
        progress_queue: queue.Queue = queue.Queue()
        manager = ConversionManager(progress_queue)

        # Gera um status para cada arquivo
        file_statuses = [statuses.draw(_conversion_status) for _ in files]

        def mock_convert(source, output_dir, extract_images):
            idx = files.index(source)
            status = file_statuses[idx]
            output = output_dir / source.with_suffix(".md").name if status == ConversionStatus.SUCCESS else None
            return ConversionFileResult(
                source=source,
                output=output,
                status=status,
            )

        with patch.object(manager._converter, "convert", side_effect=mock_convert):
            thread = manager.start(files, Path("/output"), False)
            thread.join(timeout=30)

        # Coleta todas as mensagens
        messages: list[ProgressUpdate] = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        # Separa intermediárias e finais
        intermediate = [m for m in messages if not m.is_complete]
        final = [m for m in messages if m.is_complete]

        assert len(intermediate) == n, (
            f"Esperadas {n} mensagens intermediárias, obtidas {len(intermediate)}"
        )

    @given(files=_file_list, statuses=st.data())
    @settings(max_examples=100)
    def test_current_index_monotonically_increasing(self, files: list[Path], statuses: st.DataObject) -> None:
        """current_index das mensagens intermediárias é monotonicamente crescente de 1 a N."""
        n = len(files)
        progress_queue: queue.Queue = queue.Queue()
        manager = ConversionManager(progress_queue)

        file_statuses = [statuses.draw(_conversion_status) for _ in files]

        def mock_convert(source, output_dir, extract_images):
            idx = files.index(source)
            status = file_statuses[idx]
            output = output_dir / source.with_suffix(".md").name if status == ConversionStatus.SUCCESS else None
            return ConversionFileResult(
                source=source,
                output=output,
                status=status,
            )

        with patch.object(manager._converter, "convert", side_effect=mock_convert):
            thread = manager.start(files, Path("/output"), False)
            thread.join(timeout=30)

        messages: list[ProgressUpdate] = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        intermediate = [m for m in messages if not m.is_complete]

        # Verifica que current_index vai de 1 a N sequencialmente
        indices = [m.current_index for m in intermediate]
        expected_indices = list(range(1, n + 1))
        assert indices == expected_indices, (
            f"Índices esperados {expected_indices}, obtidos {indices}"
        )

    @given(files=_file_list, statuses=st.data())
    @settings(max_examples=100)
    def test_last_message_is_complete(self, files: list[Path], statuses: st.DataObject) -> None:
        """A última mensagem emitida deve ter is_complete == True."""
        n = len(files)
        progress_queue: queue.Queue = queue.Queue()
        manager = ConversionManager(progress_queue)

        file_statuses = [statuses.draw(_conversion_status) for _ in files]

        def mock_convert(source, output_dir, extract_images):
            idx = files.index(source)
            status = file_statuses[idx]
            output = output_dir / source.with_suffix(".md").name if status == ConversionStatus.SUCCESS else None
            return ConversionFileResult(
                source=source,
                output=output,
                status=status,
            )

        with patch.object(manager._converter, "convert", side_effect=mock_convert):
            thread = manager.start(files, Path("/output"), False)
            thread.join(timeout=30)

        messages: list[ProgressUpdate] = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        # A última mensagem deve ser a final
        assert len(messages) > 0, "Nenhuma mensagem emitida"
        last_message = messages[-1]
        assert last_message.is_complete is True, (
            f"Última mensagem deveria ter is_complete=True, mas tem is_complete={last_message.is_complete}"
        )

    @given(files=_file_list, statuses=st.data())
    @settings(max_examples=100)
    def test_exactly_one_final_message(self, files: list[Path], statuses: st.DataObject) -> None:
        """Deve existir exatamente 1 mensagem final com is_complete == True."""
        n = len(files)
        progress_queue: queue.Queue = queue.Queue()
        manager = ConversionManager(progress_queue)

        file_statuses = [statuses.draw(_conversion_status) for _ in files]

        def mock_convert(source, output_dir, extract_images):
            idx = files.index(source)
            status = file_statuses[idx]
            output = output_dir / source.with_suffix(".md").name if status == ConversionStatus.SUCCESS else None
            return ConversionFileResult(
                source=source,
                output=output,
                status=status,
            )

        with patch.object(manager._converter, "convert", side_effect=mock_convert):
            thread = manager.start(files, Path("/output"), False)
            thread.join(timeout=30)

        messages: list[ProgressUpdate] = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        final_messages = [m for m in messages if m.is_complete]
        assert len(final_messages) == 1, (
            f"Esperada exatamente 1 mensagem final, obtidas {len(final_messages)}"
        )

    @given(files=_file_list, statuses=st.data())
    @settings(max_examples=100)
    def test_total_messages_count_is_n_plus_one(self, files: list[Path], statuses: st.DataObject) -> None:
        """O total de mensagens emitidas deve ser N intermediárias + 1 final = N+1."""
        n = len(files)
        progress_queue: queue.Queue = queue.Queue()
        manager = ConversionManager(progress_queue)

        file_statuses = [statuses.draw(_conversion_status) for _ in files]

        def mock_convert(source, output_dir, extract_images):
            idx = files.index(source)
            status = file_statuses[idx]
            output = output_dir / source.with_suffix(".md").name if status == ConversionStatus.SUCCESS else None
            return ConversionFileResult(
                source=source,
                output=output,
                status=status,
            )

        with patch.object(manager._converter, "convert", side_effect=mock_convert):
            thread = manager.start(files, Path("/output"), False)
            thread.join(timeout=30)

        messages: list[ProgressUpdate] = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        assert len(messages) == n + 1, (
            f"Esperadas {n + 1} mensagens totais (N={n} intermediárias + 1 final), obtidas {len(messages)}"
        )
