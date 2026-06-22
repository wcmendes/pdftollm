"""Testes de propriedade para subpasta não criada em PDFs sem imagens.

**Validates: Requirements 4.8**

Property 9: Subpasta não criada para PDFs sem imagens
Para qualquer PDF que não contém objetos embutidos extraíveis, mesmo com extração
habilitada, a conversão deve gerar o Arquivo_Saída normalmente sem criar a
Subpasta_Assets.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import fitz  # PyMuPDF
from hypothesis import given, settings
from hypothesis import strategies as st

from src.converters.pdf_converter import PDFConverter


# ─── Estratégia: conteúdo textual aleatório para PDFs ─────────────────────────

# Caracteres seguros para inserção em PDF (sem null bytes ou chars de controle)
_text_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    " .,;:!?-_()"
    "áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ"
)

# Gera texto aleatório para inserir nas páginas do PDF (apenas texto, sem imagens)
text_content_strategy = st.text(
    alphabet=_text_chars,
    min_size=10,
    max_size=500,
)

# Gera número de páginas (1 a 5 para manter testes rápidos)
page_count_strategy = st.integers(min_value=1, max_value=5)

# Gera nomes de arquivo válidos para o PDF
_filename_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_"
)

filename_strategy = st.text(
    alphabet=_filename_chars,
    min_size=1,
    max_size=30,
).filter(lambda s: s.strip() != "")


# ─── Helpers ──────────────────────────────────────────────────────────────────


def create_text_only_pdf(path: Path, pages_text: list[str]) -> None:
    """Cria um PDF contendo apenas texto (sem imagens embutidas).

    Usa PyMuPDF para gerar um PDF com N páginas, cada uma contendo
    apenas o texto fornecido.
    """
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        # Insere texto na página (posição fixa, fonte padrão)
        text_point = fitz.Point(72, 72)  # margem de 1 polegada
        page.insert_text(text_point, text, fontsize=12)
    doc.save(str(path))
    doc.close()


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyNoSubfolderWithoutImages:
    """Property 9: Subpasta não criada para PDFs sem imagens.

    **Validates: Requirements 4.8**
    """

    @given(
        text_content=text_content_strategy,
        num_pages=page_count_strategy,
        filename=filename_strategy,
    )
    @settings(max_examples=50, deadline=30000)
    def test_no_assets_folder_created_for_text_only_pdf(
        self, text_content: str, num_pages: int, filename: str
    ) -> None:
        """PDFs sem imagens com extração habilitada não devem criar Subpasta_Assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Cria PDF apenas com texto (sem imagens)
            pdf_path = tmp_path / f"{filename}.pdf"
            pages = [text_content] * num_pages
            create_text_only_pdf(pdf_path, pages)

            # Converte com extract_images=True
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            converter = PDFConverter()
            # Mock _extract_markdown para evitar chamada lenta do pymupdf4llm
            with patch.object(
                converter, "_extract_markdown", return_value=text_content
            ):
                result = converter.convert(pdf_path, output_dir, extract_images=True)

            # Verifica que a conversão foi bem sucedida
            assert result.status.value == "success"
            assert result.output is not None
            assert result.output.exists()

            # Verifica que nenhuma subpasta _assets foi criada
            expected_assets_dir = output_dir / f"{filename}_assets"
            assert not expected_assets_dir.exists(), (
                f"Subpasta_Assets '{expected_assets_dir.name}' não deveria existir "
                f"para PDF sem imagens"
            )

            # Verifica que nenhuma pasta _assets existe no output_dir
            assets_dirs = [
                d for d in output_dir.iterdir()
                if d.is_dir() and d.name.endswith("_assets")
            ]
            assert len(assets_dirs) == 0, (
                f"Nenhuma subpasta *_assets deveria existir, mas encontrou: "
                f"{[d.name for d in assets_dirs]}"
            )

    @given(
        text_content=text_content_strategy,
        num_pages=page_count_strategy,
        filename=filename_strategy,
    )
    @settings(max_examples=50, deadline=30000)
    def test_images_extracted_is_zero_for_text_only_pdf(
        self, text_content: str, num_pages: int, filename: str
    ) -> None:
        """PDFs sem imagens devem ter images_extracted == 0 no resultado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Cria PDF apenas com texto
            pdf_path = tmp_path / f"{filename}.pdf"
            pages = [text_content] * num_pages
            create_text_only_pdf(pdf_path, pages)

            # Converte com extract_images=True
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            converter = PDFConverter()
            # Mock _extract_markdown para evitar chamada lenta do pymupdf4llm
            with patch.object(
                converter, "_extract_markdown", return_value=text_content
            ):
                result = converter.convert(pdf_path, output_dir, extract_images=True)

            # Verifica que a conversão foi bem sucedida
            assert result.status.value == "success"

            # Verifica que images_extracted é 0
            assert result.images_extracted == 0, (
                f"images_extracted deveria ser 0 para PDF sem imagens, "
                f"mas foi {result.images_extracted}"
            )

    @given(
        text_content=text_content_strategy,
        filename=filename_strategy,
    )
    @settings(max_examples=30, deadline=30000)
    def test_output_file_generated_normally_without_assets(
        self, text_content: str, filename: str
    ) -> None:
        """O Arquivo_Saída deve ser gerado normalmente mesmo sem criar Subpasta_Assets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)

            # Cria PDF de página única com texto
            pdf_path = tmp_path / f"{filename}.pdf"
            create_text_only_pdf(pdf_path, [text_content])

            # Converte com extract_images=True
            output_dir = tmp_path / "output"
            output_dir.mkdir()

            converter = PDFConverter()
            # Mock _extract_markdown para evitar chamada lenta do pymupdf4llm
            with patch.object(
                converter, "_extract_markdown", return_value=text_content
            ):
                result = converter.convert(pdf_path, output_dir, extract_images=True)

            # Verifica que a conversão foi bem sucedida
            assert result.status.value == "success"
            assert result.output is not None

            # Verifica que o arquivo .md foi gerado com o nome correto
            expected_output = output_dir / f"{filename}.md"
            assert result.output == expected_output
            assert expected_output.exists()

            # Verifica que o conteúdo do .md não está vazio
            content = expected_output.read_text(encoding="utf-8")
            assert len(content) > 0, "O Arquivo_Saída não deveria estar vazio"
