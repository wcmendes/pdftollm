"""Gerenciador de conversão em batch.

Orquestra o processo de conversão de múltiplos PDFs em uma thread separada,
comunicando progresso e resultado final via queue.Queue para a GUI.
"""

import logging
import queue
import threading
from pathlib import Path

from src.converters.pdf_converter import PDFConverter
from src.models.data_models import (
    ConversionFileResult,
    ConversionResult,
    ConversionStatus,
    ProgressUpdate,
)

logger = logging.getLogger(__name__)


class ConversionManager:
    """Gerencia o ciclo de vida da conversão em batch."""

    def __init__(self, progress_queue: queue.Queue) -> None:
        """
        Inicializa o gerenciador de conversão.

        Args:
            progress_queue: Fila para comunicação de progresso com a GUI thread.
        """
        self._progress_queue = progress_queue
        self._converter = PDFConverter()

    def start(
        self,
        files: list[Path],
        output_dir: Path,
        extract_images: bool,
        confirm_overwrite: bool = False,
    ) -> threading.Thread:
        """
        Inicia a conversão em uma thread separada.

        Cria uma daemon thread que executa _worker() com os parâmetros fornecidos.

        Args:
            files: Lista de caminhos dos arquivos PDF a converter.
            output_dir: Diretório de destino para os arquivos Markdown.
            extract_images: Se True, extrai imagens embutidas dos PDFs.
            confirm_overwrite: Se True, pula arquivos cujo .md já existe.

        Returns:
            A thread criada (já iniciada).
        """
        thread = threading.Thread(
            target=self._worker,
            args=(files, output_dir, extract_images, confirm_overwrite),
            daemon=True,
        )
        thread.start()
        return thread

    def _worker(
        self,
        files: list[Path],
        output_dir: Path,
        extract_images: bool,
        confirm_overwrite: bool = False,
    ) -> None:
        """
        Função executada na thread de trabalho.

        Processa cada arquivo sequencialmente. Erros em arquivos individuais
        são capturados e registrados sem interromper o batch. Envia
        ProgressUpdate via queue a cada arquivo processado e um resultado
        final com is_complete=True ao término.

        Args:
            files: Lista de caminhos dos arquivos PDF a converter.
            output_dir: Diretório de destino para os arquivos Markdown.
            extract_images: Se True, extrai imagens embutidas dos PDFs.
        """
        total = len(files)
        results: list[ConversionFileResult] = []
        succeeded = 0
        failed = 0

        for index, source_file in enumerate(files, start=1):
            try:
                result = self._converter.convert(source_file, output_dir, extract_images, confirm_overwrite)
                results.append(result)

                if result.status == ConversionStatus.SUCCESS:
                    succeeded += 1
                else:
                    failed += 1

            except Exception as e:
                logger.error(
                    "Erro inesperado ao converter '%s': %s", source_file, e
                )
                results.append(
                    ConversionFileResult(
                        source=source_file,
                        output=None,
                        status=ConversionStatus.FAILED_IO_ERROR,
                        error_message=str(e),
                    )
                )
                failed += 1

            # Envia progresso intermediário após cada arquivo
            self._progress_queue.put(
                ProgressUpdate(
                    current_index=index,
                    total=total,
                    current_filename=source_file.name,
                    is_complete=False,
                )
            )

        # Envia resultado final com is_complete=True
        final_result = ConversionResult(
            total=total,
            succeeded=succeeded,
            failed=failed,
            results=results,
        )

        self._progress_queue.put(
            ProgressUpdate(
                current_index=total,
                total=total,
                current_filename="",
                is_complete=True,
                result=final_result,
            )
        )
