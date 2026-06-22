"""Gerenciador de OCR com fallback entre motores.

Orquestra o processo de reprocessamento de PDFs baseados em imagem
utilizando cadeia de fallback: Tesseract → EasyOCR → preserva original.
"""

import logging
import queue
from pathlib import Path

from src.models.data_models import (
    OCRBatchResult,
    OCRCandidate,
    OCREngineUsed,
    OCRFileResult,
    OCRStatus,
)
from src.ocr.ocr_engine import OCREngine

logger = logging.getLogger(__name__)


class OCRManager:
    """Gerencia o fallback OCR com motores primário e secundário.

    Para cada candidato OCR, tenta o motor primário (Tesseract) primeiro.
    Se o resultado não for legível, tenta o motor secundário (EasyOCR).
    Se ambos falharem, restaura o conteúdo original do arquivo Markdown.
    """

    LEGIBILITY_THRESHOLD = 50  # mínimo de caracteres alfanuméricos por página

    def __init__(
        self,
        primary_engine: OCREngine,
        secondary_engine: OCREngine,
        progress_queue: queue.Queue,
    ) -> None:
        """
        Inicializa o OCRManager.

        Args:
            primary_engine: Motor OCR primário (Tesseract).
            secondary_engine: Motor OCR secundário (EasyOCR).
            progress_queue: Fila para comunicação de progresso com a GUI.
        """
        self._primary_engine = primary_engine
        self._secondary_engine = secondary_engine
        self._progress_queue = progress_queue

    def process_batch(
        self,
        ocr_candidates: list[OCRCandidate],
        output_dir: Path,
    ) -> OCRBatchResult:
        """
        Processa batch de PDFs com OCR fallback.

        Tenta motor primário primeiro; se falhar, tenta secundário.
        Emite mensagem de progresso após cada arquivo processado.

        Args:
            ocr_candidates: Lista de candidatos identificados como PDF_Imagem.
            output_dir: Diretório de saída dos arquivos Markdown.

        Returns:
            OCRBatchResult com totais e lista de resultados individuais.
        """
        total = len(ocr_candidates)
        recovered = 0
        failed = 0
        results: list[OCRFileResult] = []

        for index, candidate in enumerate(ocr_candidates, start=1):
            result = self._process_single(candidate, output_dir)
            results.append(result)

            if result.status == OCRStatus.SUCCESS:
                recovered += 1
            else:
                failed += 1

            # Emite progresso OCR para a GUI
            self._progress_queue.put(
                {
                    "type": "ocr_progress",
                    "current_index": index,
                    "total": total,
                    "filename": candidate.source_pdf.name,
                    "status": result.status.value,
                    "engine_used": result.engine_used.value,
                }
            )

        return OCRBatchResult(
            total=total,
            recovered=recovered,
            failed=failed,
            results=results,
        )

    def _process_single(
        self,
        candidate: OCRCandidate,
        output_dir: Path,
    ) -> OCRFileResult:
        """
        Processa um único arquivo com fallback entre motores.

        Fluxo:
        1. Faz backup do conteúdo original do .md
        2. Tenta motor primário (Tesseract)
        3. Se legível, escreve novo markdown e retorna SUCCESS/TESSERACT
        4. Se não, tenta motor secundário (EasyOCR)
        5. Se legível, escreve novo markdown e retorna SUCCESS/EASYOCR
        6. Se ambos falharem, restaura original e retorna FAILED_ALL_ENGINES/NONE

        Args:
            candidate: OCRCandidate com informações do arquivo.
            output_dir: Diretório de saída (não usado diretamente, pois
                        candidate.output_md já contém o caminho completo).

        Returns:
            OCRFileResult com status, motor utilizado e mensagens de erro.
        """
        # Backup do conteúdo original
        original_content = candidate.output_md.read_bytes()

        # Tenta motor primário (Tesseract)
        try:
            text = self._primary_engine.extract_text(candidate.source_pdf)
            if self._is_legible(text, candidate.page_count):
                self._write_markdown(candidate.output_md, text)
                logger.info(
                    "OCR sucesso com %s para '%s'",
                    self._primary_engine.name,
                    candidate.source_pdf.name,
                )
                return OCRFileResult(
                    source_pdf=candidate.source_pdf,
                    output_md=candidate.output_md,
                    status=OCRStatus.SUCCESS,
                    engine_used=OCREngineUsed.TESSERACT,
                )
        except Exception as e:
            logger.warning(
                "%s falhou em '%s': %s",
                self._primary_engine.name,
                candidate.source_pdf.name,
                e,
            )

        # Tenta motor secundário (EasyOCR)
        try:
            text = self._secondary_engine.extract_text(candidate.source_pdf)
            if self._is_legible(text, candidate.page_count):
                self._write_markdown(candidate.output_md, text)
                logger.info(
                    "OCR sucesso com %s para '%s'",
                    self._secondary_engine.name,
                    candidate.source_pdf.name,
                )
                return OCRFileResult(
                    source_pdf=candidate.source_pdf,
                    output_md=candidate.output_md,
                    status=OCRStatus.SUCCESS,
                    engine_used=OCREngineUsed.EASYOCR,
                )
        except Exception as e:
            logger.warning(
                "%s falhou em '%s': %s",
                self._secondary_engine.name,
                candidate.source_pdf.name,
                e,
            )

        # Ambos falharam — restaura conteúdo original
        candidate.output_md.write_bytes(original_content)
        logger.warning(
            "Todos os motores OCR falharam para '%s'. Conteúdo original restaurado.",
            candidate.source_pdf.name,
        )
        return OCRFileResult(
            source_pdf=candidate.source_pdf,
            output_md=candidate.output_md,
            status=OCRStatus.FAILED_ALL_ENGINES,
            engine_used=OCREngineUsed.NONE,
            error_message="Nenhum motor OCR conseguiu extrair texto legível",
        )

    def _is_legible(self, text: str, page_count: int) -> bool:
        """
        Verifica se o texto extraído é legível.

        Um texto é considerado legível se tiver pelo menos
        LEGIBILITY_THRESHOLD (50) caracteres alfanuméricos por página.

        Args:
            text: Texto extraído pelo motor OCR.
            page_count: Número de páginas do PDF fonte.

        Returns:
            True se o texto for considerado legível.
        """
        if page_count <= 0:
            return False

        alphanumeric_count = sum(1 for ch in text if ch.isalnum())
        avg_per_page = alphanumeric_count / page_count

        return avg_per_page >= self.LEGIBILITY_THRESHOLD

    @staticmethod
    def _write_markdown(output_path: Path, text: str) -> None:
        """
        Escreve o texto extraído como arquivo Markdown.

        Usa codificação UTF-8 e terminadores de linha LF conforme
        requisito 6.4.

        Args:
            output_path: Caminho do arquivo Markdown de saída.
            text: Texto extraído via OCR para ser escrito.
        """
        # Normaliza terminadores de linha para LF
        normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
        output_path.write_text(normalized_text, encoding="utf-8", newline="")
