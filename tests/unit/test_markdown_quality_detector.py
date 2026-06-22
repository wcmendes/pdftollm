"""Testes unitários para MarkdownQualityDetector."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.data_models import ConversionFileResult, ConversionStatus, OCRCandidate
from src.ocr.markdown_quality_detector import MarkdownQualityDetector


class TestIsIllegible:
    """Testes para o método is_illegible."""

    def test_empty_content_is_illegible(self):
        """Conteúdo vazio deve ser considerado ilegível."""
        assert MarkdownQualityDetector.is_illegible("", 1) is True

    def test_content_below_threshold_is_illegible(self):
        """Conteúdo com menos de 50 chars alfanuméricos por página é ilegível."""
        # 49 alphanumeric chars, 1 page -> 49 per page < 50
        content = "a" * 49
        assert MarkdownQualityDetector.is_illegible(content, 1) is True

    def test_content_at_threshold_is_legible(self):
        """Conteúdo com exatamente 50 chars alfanuméricos por página é legível."""
        content = "a" * 50
        assert MarkdownQualityDetector.is_illegible(content, 1) is False

    def test_content_above_threshold_is_legible(self):
        """Conteúdo com mais de 50 chars alfanuméricos por página é legível."""
        content = "a" * 200
        assert MarkdownQualityDetector.is_illegible(content, 1) is False

    def test_multipage_average_below_threshold(self):
        """Média por página abaixo do limiar é ilegível."""
        # 90 alphanumeric chars, 2 pages -> 45 per page < 50
        content = "x" * 90
        assert MarkdownQualityDetector.is_illegible(content, 2) is True

    def test_multipage_average_at_threshold(self):
        """Média por página exatamente no limiar é legível."""
        # 100 alphanumeric chars, 2 pages -> 50 per page == 50
        content = "x" * 100
        assert MarkdownQualityDetector.is_illegible(content, 2) is False

    def test_non_alphanumeric_not_counted(self):
        """Caracteres não-alfanuméricos não são contados."""
        # Only spaces and punctuation - 0 alphanumeric chars
        content = "   ---  !!!  ???  ...  "
        assert MarkdownQualityDetector.is_illegible(content, 1) is True

    def test_mixed_content_counts_only_alphanumeric(self):
        """Apenas caracteres alfanuméricos são contados na avaliação."""
        # 50 alphanumeric + lots of markdown syntax
        content = "# " + "a" * 50 + "\n\n---\n\n"
        assert MarkdownQualityDetector.is_illegible(content, 1) is False

    def test_zero_pages_is_illegible(self):
        """Zero páginas retorna ilegível (caso defensivo)."""
        assert MarkdownQualityDetector.is_illegible("some content", 0) is True

    def test_negative_pages_is_illegible(self):
        """Páginas negativas retorna ilegível (caso defensivo)."""
        assert MarkdownQualityDetector.is_illegible("some content", -1) is True


class TestDetectOCRCandidates:
    """Testes para o método detect_ocr_candidates."""

    def setup_method(self):
        self.detector = MarkdownQualityDetector()

    def test_empty_results_returns_empty_list(self):
        """Lista vazia de resultados retorna lista vazia de candidatos."""
        candidates = self.detector.detect_ocr_candidates([])
        assert candidates == []

    def test_skips_failed_results(self):
        """Resultados com status diferente de SUCCESS são ignorados."""
        results = [
            ConversionFileResult(
                source=Path("test.pdf"),
                output=None,
                status=ConversionStatus.FAILED_CORRUPTED,
            ),
            ConversionFileResult(
                source=Path("test2.pdf"),
                output=None,
                status=ConversionStatus.FAILED_PASSWORD,
            ),
        ]
        candidates = self.detector.detect_ocr_candidates(results)
        assert candidates == []

    def test_skips_result_with_none_output(self):
        """Resultados SUCCESS sem output são ignorados."""
        results = [
            ConversionFileResult(
                source=Path("test.pdf"),
                output=None,
                status=ConversionStatus.SUCCESS,
            ),
        ]
        candidates = self.detector.detect_ocr_candidates(results)
        assert candidates == []

    def test_detects_illegible_file(self, tmp_path):
        """Detecta arquivo com conteúdo ilegível como candidato OCR."""
        # Create a minimal PDF with 1 page
        pdf_path = tmp_path / "scanned.pdf"
        md_path = tmp_path / "scanned.md"

        # Write markdown with very few alphanumeric chars
        md_path.write_text("---\n...\n", encoding="utf-8")

        # Mock _get_page_count to return 1
        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=1
        ):
            results = [
                ConversionFileResult(
                    source=pdf_path,
                    output=md_path,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        assert len(candidates) == 1
        assert candidates[0].source_pdf == pdf_path
        assert candidates[0].output_md == md_path
        assert candidates[0].page_count == 1

    def test_does_not_flag_legible_file(self, tmp_path):
        """Não identifica arquivo legível como candidato."""
        pdf_path = tmp_path / "normal.pdf"
        md_path = tmp_path / "normal.md"

        # Write markdown with plenty of alphanumeric content
        md_path.write_text("a" * 200, encoding="utf-8")

        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=1
        ):
            results = [
                ConversionFileResult(
                    source=pdf_path,
                    output=md_path,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        assert candidates == []

    def test_handles_missing_output_file_gracefully(self, tmp_path):
        """Arquivo de saída inexistente é tratado sem erro."""
        pdf_path = tmp_path / "source.pdf"
        md_path = tmp_path / "nonexistent.md"  # Does not exist

        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=1
        ):
            results = [
                ConversionFileResult(
                    source=pdf_path,
                    output=md_path,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        assert candidates == []

    def test_handles_pdf_open_failure_gracefully(self, tmp_path):
        """Falha ao abrir PDF é tratada sem erro."""
        pdf_path = tmp_path / "broken.pdf"
        md_path = tmp_path / "broken.md"
        md_path.write_text("short", encoding="utf-8")

        # _get_page_count returns 0 when it can't open the PDF
        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=0
        ):
            results = [
                ConversionFileResult(
                    source=pdf_path,
                    output=md_path,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        assert candidates == []

    def test_alphanumeric_count_in_candidate(self, tmp_path):
        """O OCRCandidate contém a contagem correta de chars alfanuméricos."""
        pdf_path = tmp_path / "scan.pdf"
        md_path = tmp_path / "scan.md"

        # 10 alphanumeric chars + some markdown
        md_path.write_text("# abc\n---\ndefghij", encoding="utf-8")
        # alphanumeric: a, b, c, d, e, f, g, h, i, j = 10

        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=1
        ):
            results = [
                ConversionFileResult(
                    source=pdf_path,
                    output=md_path,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        assert len(candidates) == 1
        assert candidates[0].alphanumeric_count == 10

    def test_mixed_success_and_failure_results(self, tmp_path):
        """Processa apenas resultados SUCCESS em lista mista."""
        pdf1 = tmp_path / "scan1.pdf"
        md1 = tmp_path / "scan1.md"
        md1.write_text("x" * 10, encoding="utf-8")

        pdf2 = tmp_path / "normal.pdf"
        md2 = tmp_path / "normal.md"
        md2.write_text("y" * 200, encoding="utf-8")

        with patch.object(
            MarkdownQualityDetector, "_get_page_count", return_value=1
        ):
            results = [
                ConversionFileResult(
                    source=pdf1,
                    output=md1,
                    status=ConversionStatus.SUCCESS,
                ),
                ConversionFileResult(
                    source=Path("failed.pdf"),
                    output=None,
                    status=ConversionStatus.FAILED_CORRUPTED,
                ),
                ConversionFileResult(
                    source=pdf2,
                    output=md2,
                    status=ConversionStatus.SUCCESS,
                ),
            ]
            candidates = self.detector.detect_ocr_candidates(results)

        # Only scan1 should be flagged (10 chars < 50 threshold)
        assert len(candidates) == 1
        assert candidates[0].source_pdf == pdf1
