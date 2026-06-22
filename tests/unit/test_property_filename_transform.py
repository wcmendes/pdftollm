"""Testes de propriedade para transformação de nomes de arquivo PDF → Markdown.

**Validates: Requirements 3.2**

Property 2: Para qualquer caminho de arquivo com extensão `.pdf`, o nome do
Arquivo_Saída gerado SHALL ser idêntico ao nome do Arquivo_Fonte com a extensão
substituída por `.md`.
"""

from pathlib import Path

from hypothesis import given, assume, settings
from hypothesis import strategies as st


# ─── Estratégia de geração de nomes de arquivo ─────────────────────────────────

# Caracteres válidos para nomes de arquivo (exclui caracteres ilegais em Windows/Linux)
_VALID_FILENAME_CHARS = st.characters(
    blacklist_characters='\x00/\\:*?"<>|.',
    blacklist_categories=("Cs",),  # exclui surrogates
)

# Gera um nome base (stem) não-vazio de 1 a 100 caracteres
_filename_stem = st.text(
    alphabet=_VALID_FILENAME_CHARS,
    min_size=1,
    max_size=100,
)


def _pdf_filename_strategy():
    """Gera nomes de arquivo com extensão .pdf."""
    return _filename_stem.map(lambda stem: f"{stem}.pdf")


# ─── Função de transformação sob teste ──────────────────────────────────────────


def transform_pdf_to_md(pdf_filename: str) -> str:
    """Transforma nome de arquivo .pdf para .md usando pathlib.

    Esta é a lógica de transformação de nome que o PDFConverter utilizará.
    """
    return str(Path(pdf_filename).with_suffix(".md"))


# ─── Testes de propriedade ──────────────────────────────────────────────────────


class TestPropertyFilenameTransform:
    """Property 2: Transformação de nome PDF para Markdown.

    **Validates: Requirements 3.2**
    """

    @given(pdf_name=_pdf_filename_strategy())
    @settings(max_examples=200)
    def test_pdf_extension_replaced_by_md(self, pdf_name: str):
        """A extensão .pdf deve ser substituída por .md."""
        result = transform_pdf_to_md(pdf_name)
        assert result.endswith(".md"), (
            f"Resultado '{result}' não termina com .md"
        )

    @given(pdf_name=_pdf_filename_strategy())
    @settings(max_examples=200)
    def test_stem_preserved_after_transform(self, pdf_name: str):
        """O nome base (stem) do arquivo deve permanecer idêntico após a transformação."""
        source_stem = Path(pdf_name).stem
        result_stem = Path(transform_pdf_to_md(pdf_name)).stem

        assert source_stem == result_stem, (
            f"Stem alterado: '{source_stem}' → '{result_stem}'"
        )

    @given(pdf_name=_pdf_filename_strategy())
    @settings(max_examples=200)
    def test_only_extension_differs(self, pdf_name: str):
        """A única diferença entre entrada e saída deve ser a extensão."""
        result = transform_pdf_to_md(pdf_name)

        # Remove extensão de ambos e compara
        source_without_ext = pdf_name[: -len(".pdf")]
        result_without_ext = result[: -len(".md")]

        assert source_without_ext == result_without_ext, (
            f"Parte sem extensão difere: '{source_without_ext}' vs '{result_without_ext}'"
        )

    @given(pdf_name=_pdf_filename_strategy())
    @settings(max_examples=200)
    def test_result_never_ends_with_pdf(self, pdf_name: str):
        """O resultado nunca deve ter extensão .pdf."""
        result = transform_pdf_to_md(pdf_name)
        assert Path(result).suffix == ".md", (
            f"Resultado '{result}' ainda tem extensão .pdf"
        )
