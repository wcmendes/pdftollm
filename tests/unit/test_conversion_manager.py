"""Testes unitários para ConversionManager."""

import queue
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.converters.conversion_manager import ConversionManager
from src.models.data_models import (
    ConversionFileResult,
    ConversionResult,
    ConversionStatus,
    ProgressUpdate,
)


@pytest.fixture
def progress_queue():
    """Cria uma fila de progresso para testes."""
    return queue.Queue()


@pytest.fixture
def manager(progress_queue):
    """Cria um ConversionManager com fila de progresso."""
    return ConversionManager(progress_queue)


class TestConversionManagerStart:
    """Testes para o método start()."""

    def test_start_returns_thread(self, manager):
        """start() deve retornar um threading.Thread."""
        import threading

        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("test.pdf"),
                output=Path("test.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start([Path("test.pdf")], Path("/out"), False)
            assert isinstance(thread, threading.Thread)
            thread.join(timeout=5)

    def test_start_creates_daemon_thread(self, manager):
        """start() deve criar uma daemon thread."""
        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("test.pdf"),
                output=Path("test.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start([Path("test.pdf")], Path("/out"), False)
            assert thread.daemon is True
            thread.join(timeout=5)

    def test_start_thread_is_alive(self, manager):
        """start() deve iniciar a thread imediatamente."""
        import threading

        event = threading.Event()

        with patch.object(manager._converter, "convert") as mock_convert:

            def slow_convert(*args, **kwargs):
                event.wait(timeout=5)
                return ConversionFileResult(
                    source=Path("test.pdf"),
                    output=Path("test.md"),
                    status=ConversionStatus.SUCCESS,
                )

            mock_convert.side_effect = slow_convert
            thread = manager.start([Path("test.pdf")], Path("/out"), False)
            assert thread.is_alive()
            event.set()
            thread.join(timeout=5)


class TestConversionManagerWorker:
    """Testes para o método _worker() via resultados na fila."""

    def test_single_file_success(self, manager, progress_queue):
        """Um único arquivo com sucesso produz 1 progress + 1 final."""
        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("doc.pdf"),
                output=Path("/out/doc.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start([Path("doc.pdf")], Path("/out"), False)
            thread.join(timeout=5)

        # Deve ter 2 mensagens: 1 progresso intermediário + 1 final
        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        assert len(messages) == 2

        # Primeira mensagem: progresso intermediário
        prog = messages[0]
        assert isinstance(prog, ProgressUpdate)
        assert prog.current_index == 1
        assert prog.total == 1
        assert prog.current_filename == "doc.pdf"
        assert prog.is_complete is False

        # Segunda mensagem: resultado final
        final = messages[1]
        assert isinstance(final, ProgressUpdate)
        assert final.is_complete is True
        assert final.result is not None
        assert final.result.total == 1
        assert final.result.succeeded == 1
        assert final.result.failed == 0

    def test_multiple_files_progress(self, manager, progress_queue):
        """Múltiplos arquivos emitem progresso para cada um + resultado final."""
        files = [Path("a.pdf"), Path("b.pdf"), Path("c.pdf")]

        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("x.pdf"),
                output=Path("/out/x.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start(files, Path("/out"), True)
            thread.join(timeout=5)

        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        # 3 intermediários + 1 final = 4
        assert len(messages) == 4

        # Verifica índices crescentes
        for i in range(3):
            assert messages[i].current_index == i + 1
            assert messages[i].total == 3
            assert messages[i].is_complete is False

        # Final
        assert messages[3].is_complete is True
        assert messages[3].result.total == 3
        assert messages[3].result.succeeded == 3
        assert messages[3].result.failed == 0

    def test_file_failure_does_not_stop_batch(self, manager, progress_queue):
        """Falha em um arquivo não interrompe o processamento dos demais."""
        files = [Path("good.pdf"), Path("bad.pdf"), Path("also_good.pdf")]

        with patch.object(manager._converter, "convert") as mock_convert:

            def side_effect(source, output_dir, extract_images):
                if source == Path("bad.pdf"):
                    return ConversionFileResult(
                        source=source,
                        output=None,
                        status=ConversionStatus.FAILED_CORRUPTED,
                        error_message="Corrompido",
                    )
                return ConversionFileResult(
                    source=source,
                    output=output_dir / source.with_suffix(".md").name,
                    status=ConversionStatus.SUCCESS,
                )

            mock_convert.side_effect = side_effect
            thread = manager.start(files, Path("/out"), False)
            thread.join(timeout=5)

        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        # Todos os 3 devem ter sido processados + 1 final
        assert len(messages) == 4

        final = messages[3]
        assert final.is_complete is True
        assert final.result.total == 3
        assert final.result.succeeded == 2
        assert final.result.failed == 1

    def test_exception_in_convert_does_not_stop_batch(self, manager, progress_queue):
        """Exceção inesperada no convert() é capturada sem interromper o batch."""
        files = [Path("a.pdf"), Path("crash.pdf"), Path("b.pdf")]

        with patch.object(manager._converter, "convert") as mock_convert:

            def side_effect(source, output_dir, extract_images):
                if source == Path("crash.pdf"):
                    raise RuntimeError("Erro inesperado")
                return ConversionFileResult(
                    source=source,
                    output=output_dir / source.with_suffix(".md").name,
                    status=ConversionStatus.SUCCESS,
                )

            mock_convert.side_effect = side_effect
            thread = manager.start(files, Path("/out"), False)
            thread.join(timeout=5)

        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        assert len(messages) == 4

        final = messages[3]
        assert final.is_complete is True
        assert final.result.total == 3
        assert final.result.succeeded == 2
        assert final.result.failed == 1

        # Verifica que o arquivo com erro tem o status correto
        crash_result = final.result.results[1]
        assert crash_result.source == Path("crash.pdf")
        assert crash_result.status == ConversionStatus.FAILED_IO_ERROR
        assert "Erro inesperado" in crash_result.error_message

    def test_empty_file_list(self, manager, progress_queue):
        """Lista vazia de arquivos emite apenas resultado final."""
        thread = manager.start([], Path("/out"), False)
        thread.join(timeout=5)

        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        # Apenas mensagem final
        assert len(messages) == 1
        final = messages[0]
        assert final.is_complete is True
        assert final.result.total == 0
        assert final.result.succeeded == 0
        assert final.result.failed == 0

    def test_progress_filename_is_file_name_only(self, manager, progress_queue):
        """ProgressUpdate deve conter apenas o nome do arquivo (sem diretório)."""
        files = [Path("/home/user/docs/report.pdf")]

        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("/home/user/docs/report.pdf"),
                output=Path("/out/report.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start(files, Path("/out"), False)
            thread.join(timeout=5)

        messages = []
        while not progress_queue.empty():
            messages.append(progress_queue.get_nowait())

        assert messages[0].current_filename == "report.pdf"

    def test_passes_extract_images_to_converter(self, manager, progress_queue):
        """O parâmetro extract_images é passado corretamente ao converter."""
        with patch.object(manager._converter, "convert") as mock_convert:
            mock_convert.return_value = ConversionFileResult(
                source=Path("doc.pdf"),
                output=Path("/out/doc.md"),
                status=ConversionStatus.SUCCESS,
            )
            thread = manager.start([Path("doc.pdf")], Path("/out"), True)
            thread.join(timeout=5)

            mock_convert.assert_called_once_with(Path("doc.pdf"), Path("/out"), True)
