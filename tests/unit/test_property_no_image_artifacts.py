"""Testes de propriedade para ausência de artefatos de imagem quando extração desabilitada.

**Validates: Requirements 4.6**

Property 8: Sem artefatos de imagem quando extração desabilitada
Para qualquer PDF convertido com extração de imagens desabilitada, o Markdown gerado
não deve conter referências de imagem no formato ![...](..._assets/...) e nenhuma
Subpasta_Assets deve ser criada no sistema de arquivos.
"""

import re
import struct
import tempfile
import zlib
from pathlib import Path
from unittest.mock import patch

import fitz  # PyMuPDF
from hypothesis import given, settings
from hypothesis import strategies as st

from src.converters.pdf_converter import PDFConverter


# ─── Helpers para criação de PDFs de teste ────────────────────────────────────


def _create_minimal_png(r: int = 255, g: int = 0, b: int = 0) -> bytes:
    """Cria um PNG mínimo de 1x1 pixel."""
    signature = b"\x89PNG\r\n\x1a\n"

    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr_chunk = (
        struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)
    )

    raw_data = bytes([0, r, g, b])
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    idat_chunk = (
        struct.pack(">I", len(compressed))
        + b"IDAT"
        + compressed
        + struct.pack(">I", idat_crc)
    )

    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return signature + ihdr_chunk + idat_chunk + iend_chunk


def create_pdf_with_images(path: Path, name: str, num_images: int = 2) -> None:
    """Cria um PDF com imagens embutidas usando o nome fornecido."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), f"Document: {name}")

    for i in range(num_images):
        png_data = _create_minimal_png(r=100 + i, g=50, b=200)
        rect = fitz.Rect(72, 100 + i * 60, 172, 150 + i * 60)
        page.insert_image(rect, stream=png_data)

    doc.save(str(path))
    doc.close()


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Gera nomes de arquivo válidos para PDFs (sem extensão)
_valid_filename_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_"
)

pdf_base_name_strategy = st.text(
    alphabet=_valid_filename_chars,
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")

# Gera quantidades de imagens para o PDF (1 a 5)
num_images_strategy = st.integers(min_value=1, max_value=5)


# ─── Regex para detecção de referências de imagem ─────────────────────────────

# Padrão que detecta referências ![...](..._assets/...)
IMAGE_REF_PATTERN = re.compile(r"!\[.*?\]\(.*?_assets/.*?\)")


# ─── Mock para pymupdf4llm (evita OCR lento nos testes) ──────────────────────


def _mock_to_markdown(doc):
    """Retorna markdown simples sem disparar OCR."""
    return "# Document Title\n\nSome text content in the document.\n"


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyNoImageArtifacts:
    """Property 8: Sem artefatos de imagem quando extração desabilitada.

    **Validates: Requirements 4.6**
    """

    @given(base_name=pdf_base_name_strategy, num_images=num_images_strategy)
    @settings(max_examples=50, deadline=30000)
    def test_no_image_references_in_markdown(
        self, base_name: str, num_images: int
    ) -> None:
        """Com extração desabilitada, o Markdown não contém referências ![...](..._assets/...)."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_name = f"{base_name}.pdf"
            pdf_path = tmp_path / pdf_name
            output_dir = tmp_path / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Cria PDF com imagens
            create_pdf_with_images(pdf_path, base_name, num_images)

            # Converte com extração DESABILITADA (mock pymupdf4llm para evitar OCR)
            converter = PDFConverter()
            with patch("pymupdf4llm.to_markdown", side_effect=_mock_to_markdown):
                result = converter.convert(pdf_path, output_dir, extract_images=False)

            # Verifica que o markdown não contém referências de imagem _assets
            assert result.output is not None
            content = result.output.read_text(encoding="utf-8")
            assert not IMAGE_REF_PATTERN.search(content), (
                f"Markdown contém referência de imagem _assets com extração desabilitada: "
                f"{IMAGE_REF_PATTERN.findall(content)}"
            )

    @given(base_name=pdf_base_name_strategy, num_images=num_images_strategy)
    @settings(max_examples=50, deadline=30000)
    def test_no_assets_folder_created(
        self, base_name: str, num_images: int
    ) -> None:
        """Com extração desabilitada, nenhuma subpasta _assets é criada."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_name = f"{base_name}.pdf"
            pdf_path = tmp_path / pdf_name
            output_dir = tmp_path / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Cria PDF com imagens
            create_pdf_with_images(pdf_path, base_name, num_images)

            # Converte com extração DESABILITADA
            converter = PDFConverter()
            with patch("pymupdf4llm.to_markdown", side_effect=_mock_to_markdown):
                converter.convert(pdf_path, output_dir, extract_images=False)

            # Verifica que nenhuma subpasta terminando em _assets existe no output_dir
            assets_folders = [
                d
                for d in output_dir.iterdir()
                if d.is_dir() and d.name.endswith("_assets")
            ]
            assert len(assets_folders) == 0, (
                f"Subpasta(s) _assets criada(s) com extração desabilitada: "
                f"{[f.name for f in assets_folders]}"
            )

    @given(base_name=pdf_base_name_strategy, num_images=num_images_strategy)
    @settings(max_examples=50, deadline=30000)
    def test_no_markdown_image_syntax_at_all(
        self, base_name: str, num_images: int
    ) -> None:
        """Com extração desabilitada, o Markdown não contém sintaxe ![ de imagem."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            pdf_name = f"{base_name}.pdf"
            pdf_path = tmp_path / pdf_name
            output_dir = tmp_path / "output"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Cria PDF com imagens
            create_pdf_with_images(pdf_path, base_name, num_images)

            # Converte com extração DESABILITADA
            converter = PDFConverter()
            with patch("pymupdf4llm.to_markdown", side_effect=_mock_to_markdown):
                result = converter.convert(pdf_path, output_dir, extract_images=False)

            # Verifica que não há nenhuma referência ![
            assert result.output is not None
            content = result.output.read_text(encoding="utf-8")
            assert "![" not in content, (
                f"Markdown contém '![' com extração desabilitada. "
                f"Conteúdo parcial: {content[:500]}"
            )
