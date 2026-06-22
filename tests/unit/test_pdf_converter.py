"""Testes unitários para o PDFConverter.

Testa a conversão de PDF para Markdown incluindo:
- Conversão básica de texto
- Extração de imagens com nomes sequenciais
- Referências de imagem no Markdown
- Comportamento sem extração de imagens
- Tratamento de erros (corrompido, protegido por senha)
- Codificação UTF-8 e terminadores LF
"""

import struct
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from src.converters.pdf_converter import PDFConverter
from src.models.data_models import ConversionFileResult, ConversionStatus, ImageInfo


# ─── Helpers para criação de PDFs de teste ────────────────────────────────────


def create_simple_pdf(path: Path, text: str = "Hello World") -> None:
    """Cria um PDF simples com texto."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def create_pdf_with_image(path: Path, num_images: int = 1) -> None:
    """Cria um PDF com imagens embutidas (simples PNG de 2x2 pixels)."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Document with images")

    for i in range(num_images):
        # Cria um PNG mínimo (1x1 pixel vermelho)
        png_data = _create_minimal_png(r=255, g=i % 256, b=0)
        rect = fitz.Rect(72, 100 + i * 60, 172, 150 + i * 60)
        page.insert_image(rect, stream=png_data)

    doc.save(str(path))
    doc.close()


def create_password_protected_pdf(path: Path) -> None:
    """Cria um PDF protegido por senha."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Secret content")
    doc.save(str(path), encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="password")
    doc.close()


def _create_minimal_png(r: int = 255, g: int = 0, b: int = 0) -> bytes:
    """Cria um PNG mínimo de 1x1 pixel."""
    import zlib

    # PNG header
    signature = b"\x89PNG\r\n\x1a\n"

    # IHDR chunk: width=1, height=1, bit_depth=8, color_type=2 (RGB)
    ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    ihdr_crc = zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF
    ihdr_chunk = struct.pack(">I", 13) + b"IHDR" + ihdr_data + struct.pack(">I", ihdr_crc)

    # IDAT chunk: raw pixel data (filter byte 0 + RGB)
    raw_data = bytes([0, r, g, b])  # filter=None + 1 pixel RGB
    compressed = zlib.compress(raw_data)
    idat_crc = zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF
    idat_chunk = struct.pack(">I", len(compressed)) + b"IDAT" + compressed + struct.pack(">I", idat_crc)

    # IEND chunk
    iend_crc = zlib.crc32(b"IEND") & 0xFFFFFFFF
    iend_chunk = struct.pack(">I", 0) + b"IEND" + struct.pack(">I", iend_crc)

    return signature + ihdr_chunk + idat_chunk + iend_chunk


# ─── Testes ───────────────────────────────────────────────────────────────────


class TestPDFConverterBasicConversion:
    """Testa conversão básica de PDF para Markdown."""

    def test_convert_simple_pdf_returns_success(self, tmp_path: Path):
        """Conversão de PDF simples retorna status SUCCESS."""
        pdf_path = tmp_path / "test.pdf"
        create_simple_pdf(pdf_path, "Hello World")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.status == ConversionStatus.SUCCESS
        assert result.output is not None
        assert result.output.exists()

    def test_output_filename_matches_source_with_md_extension(self, tmp_path: Path):
        """Arquivo de saída tem mesmo nome com extensão .md."""
        pdf_path = tmp_path / "document.pdf"
        create_simple_pdf(pdf_path)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.output is not None
        assert result.output.name == "document.md"

    def test_output_contains_text_content(self, tmp_path: Path):
        """Arquivo de saída contém o texto extraído."""
        pdf_path = tmp_path / "test.pdf"
        create_simple_pdf(pdf_path, "Test content here")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.output is not None
        content = result.output.read_text(encoding="utf-8")
        assert "Test content here" in content


class TestPDFConverterUTF8AndLF:
    """Testa codificação UTF-8 e terminadores LF."""

    def test_output_is_utf8_encoded(self, tmp_path: Path):
        """Arquivo de saída é codificado em UTF-8."""
        pdf_path = tmp_path / "test.pdf"
        create_simple_pdf(pdf_path, "Olá mundo com acentuação")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.output is not None
        # Deve ser legível como UTF-8
        content = result.output.read_text(encoding="utf-8")
        assert "mundo" in content

    def test_output_uses_lf_line_endings(self, tmp_path: Path):
        """Arquivo de saída usa apenas terminadores LF."""
        pdf_path = tmp_path / "test.pdf"
        create_simple_pdf(pdf_path, "Line one")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.output is not None
        raw_bytes = result.output.read_bytes()
        # Não deve conter \r\n (CRLF) nem \r isolado
        assert b"\r\n" not in raw_bytes
        assert b"\r" not in raw_bytes


class TestPDFConverterImageExtraction:
    """Testa extração de imagens."""

    def test_extract_images_creates_assets_folder(self, tmp_path: Path):
        """Com extração habilitada e imagens, cria pasta de assets."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=1)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=True)

        assert result.status == ConversionStatus.SUCCESS
        assets_dir = tmp_path / "doc_assets"
        assert assets_dir.exists()
        assert assets_dir.is_dir()

    def test_image_filenames_are_sequential_with_zero_padding(self, tmp_path: Path):
        """Imagens são nomeadas img_001, img_002, etc."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=3)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=True)

        assets_dir = tmp_path / "doc_assets"
        image_files = sorted(assets_dir.iterdir())
        names = [f.name for f in image_files]

        assert len(names) == 3
        assert names[0].startswith("img_001.")
        assert names[1].startswith("img_002.")
        assert names[2].startswith("img_003.")

    def test_images_extracted_count(self, tmp_path: Path):
        """Resultado reporta quantidade correta de imagens extraídas."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=2)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=True)

        assert result.images_extracted == 2

    def test_markdown_contains_image_references(self, tmp_path: Path):
        """Markdown contém referências de imagem no formato esperado."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=2)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=True)

        assert result.output is not None
        content = result.output.read_text(encoding="utf-8")

        assert "![image1](doc_assets/img_001." in content
        assert "![image2](doc_assets/img_002." in content

    def test_no_assets_folder_when_extract_disabled(self, tmp_path: Path):
        """Com extração desabilitada, não cria pasta de assets."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=2)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assets_dir = tmp_path / "doc_assets"
        assert not assets_dir.exists()

    def test_no_image_references_when_extract_disabled(self, tmp_path: Path):
        """Com extração desabilitada, não insere referências de imagem."""
        pdf_path = tmp_path / "doc.pdf"
        create_pdf_with_image(pdf_path, num_images=2)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.output is not None
        content = result.output.read_text(encoding="utf-8")
        assert "![image" not in content
        assert "_assets/" not in content

    def test_no_assets_folder_for_pdf_without_images(self, tmp_path: Path):
        """Para PDF sem imagens, não cria pasta de assets mesmo com extração habilitada."""
        pdf_path = tmp_path / "text_only.pdf"
        create_simple_pdf(pdf_path, "Just text, no images")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=True)

        assets_dir = tmp_path / "text_only_assets"
        assert not assets_dir.exists()
        assert result.images_extracted == 0


class TestPDFConverterErrorHandling:
    """Testa tratamento de erros."""

    def test_corrupted_pdf_returns_failed_corrupted(self, tmp_path: Path):
        """PDF corrompido retorna FAILED_CORRUPTED."""
        pdf_path = tmp_path / "bad.pdf"
        pdf_path.write_bytes(b"this is not a valid PDF file content")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.status == ConversionStatus.FAILED_CORRUPTED
        assert result.output is None

    def test_password_protected_returns_failed_password(self, tmp_path: Path):
        """PDF protegido por senha retorna FAILED_PASSWORD."""
        pdf_path = tmp_path / "secret.pdf"
        create_password_protected_pdf(pdf_path)

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.status == ConversionStatus.FAILED_PASSWORD
        assert result.output is None

    def test_error_message_on_failure(self, tmp_path: Path):
        """Falha inclui mensagem de erro descritiva."""
        pdf_path = tmp_path / "bad.pdf"
        pdf_path.write_bytes(b"not a pdf")

        converter = PDFConverter()
        result = converter.convert(pdf_path, tmp_path, extract_images=False)

        assert result.error_message != ""


class TestPDFConverterInsertImageReferences:
    """Testa _insert_image_references diretamente."""

    def test_inserts_correct_number_of_references(self):
        """Insere exatamente N referências para N imagens."""
        converter = PDFConverter()
        images = [
            ImageInfo(filename="img_001.png", format="png", page_number=1, position_index=1),
            ImageInfo(filename="img_002.jpeg", format="jpeg", page_number=1, position_index=2),
        ]

        result = converter._insert_image_references("# Title\n\nText\n", images, "doc_assets")

        assert "![image1](doc_assets/img_001.png)" in result
        assert "![image2](doc_assets/img_002.jpeg)" in result

    def test_failed_image_inserts_marker(self):
        """Imagem com falha insere marcador de erro."""
        converter = PDFConverter()
        images = [
            ImageInfo(filename="img_001.png", format="png", page_number=1, position_index=1),
            ImageInfo(filename="__FAILED__", format="", page_number=1, position_index=2),
        ]

        result = converter._insert_image_references("# Title\n", images, "doc_assets")

        assert "![image1](doc_assets/img_001.png)" in result
        assert "[Falha na extração da imagem]" in result

    def test_empty_images_returns_unchanged_markdown(self):
        """Lista vazia de imagens retorna markdown inalterado."""
        converter = PDFConverter()
        markdown = "# Title\n\nSome text\n"

        result = converter._insert_image_references(markdown, [], "assets")

        assert result == markdown
