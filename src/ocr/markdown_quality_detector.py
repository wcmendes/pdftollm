"""Detector de qualidade do Markdown gerado.

Identifica Arquivos_Saída com conteúdo ilegível (PDFs baseados em imagem)
que são candidatos a reprocessamento via OCR.
"""

import logging
from pathlib import Path

import fitz  # PyMuPDF

from src.models.data_models import ConversionFileResult, ConversionStatus, OCRCandidate

logger = logging.getLogger(__name__)


class MarkdownQualityDetector:
    """Detecta Arquivos_Saída que produziram Markdown ilegível."""

    CHARS_PER_PAGE_THRESHOLD = 50

    @staticmethod
    def is_illegible(markdown_content: str, page_count: int) -> bool:
        """
        Verifica se o conteúdo Markdown é ilegível.

        Retorna True se o conteúdo tiver menos de 50 caracteres
        alfanuméricos por página em média.

        Args:
            markdown_content: Conteúdo do arquivo Markdown.
            page_count: Número de páginas do PDF fonte.

        Returns:
            True se o conteúdo for considerado ilegível.
        """
        if page_count <= 0:
            return True

        alphanumeric_count = sum(1 for ch in markdown_content if ch.isalnum())
        avg_per_page = alphanumeric_count / page_count

        return avg_per_page < MarkdownQualityDetector.CHARS_PER_PAGE_THRESHOLD

    def detect_ocr_candidates(
        self,
        results: list[ConversionFileResult],
    ) -> list[OCRCandidate]:
        """
        Analisa resultados da conversão e identifica candidatos a OCR.

        Para cada resultado com status SUCCESS, lê o arquivo .md gerado,
        conta caracteres alfanuméricos, obtém contagem de páginas do PDF
        fonte e verifica legibilidade.

        Args:
            results: Lista de resultados da conversão em batch.

        Returns:
            Lista de OCRCandidate para arquivos com Markdown ilegível.
        """
        candidates: list[OCRCandidate] = []

        for result in results:
            if result.status != ConversionStatus.SUCCESS:
                continue

            if result.output is None:
                continue

            try:
                candidate = self._evaluate_result(result)
                if candidate is not None:
                    candidates.append(candidate)
            except Exception as e:
                logger.warning(
                    "Erro ao avaliar qualidade de '%s': %s",
                    result.output,
                    e,
                )
                continue

        return candidates

    def _evaluate_result(self, result: ConversionFileResult) -> OCRCandidate | None:
        """
        Avalia um resultado individual e retorna OCRCandidate se ilegível.

        Args:
            result: Resultado da conversão de um arquivo.

        Returns:
            OCRCandidate se o Markdown for ilegível, None caso contrário.
        """
        output_path = Path(result.output)  # type: ignore[arg-type]
        source_path = Path(result.source)

        # Lê o conteúdo do arquivo Markdown gerado
        if not output_path.exists():
            logger.warning("Arquivo de saída não encontrado: %s", output_path)
            return None

        markdown_content = output_path.read_text(encoding="utf-8")

        # Obtém contagem de páginas do PDF fonte
        page_count = self._get_page_count(source_path)
        if page_count <= 0:
            logger.warning(
                "Não foi possível obter contagem de páginas de '%s'", source_path
            )
            return None

        # Calcula caracteres alfanuméricos
        alphanumeric_count = sum(1 for ch in markdown_content if ch.isalnum())

        # Verifica legibilidade
        if self.is_illegible(markdown_content, page_count):
            return OCRCandidate(
                source_pdf=source_path,
                output_md=output_path,
                page_count=page_count,
                alphanumeric_count=alphanumeric_count,
            )

        return None

    @staticmethod
    def _get_page_count(pdf_path: Path) -> int:
        """
        Obtém o número de páginas de um arquivo PDF.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Número de páginas ou 0 em caso de erro.
        """
        try:
            doc = fitz.open(str(pdf_path))
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            logger.warning("Erro ao abrir PDF '%s': %s", pdf_path, e)
            return 0
