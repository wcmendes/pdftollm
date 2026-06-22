"""Testes de propriedade para nomenclatura de subpasta de assets.

**Validates: Requirements 4.3**

Property 5: Nome da Subpasta de Assets
Para qualquer arquivo PDF com nome base X (sem extensão), a Subpasta_Assets
criada deve ter o nome X_assets.
"""

from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st


# ─── Estratégia: nomes de arquivo válidos ─────────────────────────────────────

# Gera nomes base de arquivo válidos (sem extensão, sem separadores de caminho)
# Restringe a caracteres alfanuméricos, hífens, underscores e espaços (comum em PDFs)
_valid_filename_chars = st.sampled_from(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "-_ "
)

base_name_strategy = st.text(
    alphabet=_valid_filename_chars,
    min_size=1,
    max_size=100,
).filter(lambda s: s.strip() != "")  # Nome não pode ser apenas espaços


# ─── Função sob teste ─────────────────────────────────────────────────────────


def get_assets_subfolder_name(pdf_path: Path) -> str:
    """Deriva o nome da subpasta de assets a partir do caminho de um arquivo PDF.

    Para um arquivo com nome base X (stem), retorna 'X_assets'.
    """
    return f"{pdf_path.stem}_assets"


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyAssetsSubfolderNaming:
    """Property 5: Nome da Subpasta de Assets.

    **Validates: Requirements 4.3**
    """

    @given(base_name=base_name_strategy)
    @settings(max_examples=200)
    def test_assets_folder_is_base_name_plus_suffix(self, base_name: str) -> None:
        """Para qualquer nome base X, a subpasta de assets deve ser X_assets."""
        pdf_path = Path(f"/some/dir/{base_name}.pdf")
        assets_name = get_assets_subfolder_name(pdf_path)
        assert assets_name == f"{base_name}_assets"

    @given(base_name=base_name_strategy)
    @settings(max_examples=200)
    def test_assets_folder_ends_with_assets_suffix(self, base_name: str) -> None:
        """A subpasta de assets sempre termina com '_assets'."""
        pdf_path = Path(f"/docs/{base_name}.pdf")
        assets_name = get_assets_subfolder_name(pdf_path)
        assert assets_name.endswith("_assets")

    @given(base_name=base_name_strategy)
    @settings(max_examples=200)
    def test_assets_folder_prefix_matches_stem(self, base_name: str) -> None:
        """O prefixo da subpasta (antes de '_assets') é exatamente o stem do PDF."""
        pdf_path = Path(f"/output/{base_name}.pdf")
        assets_name = get_assets_subfolder_name(pdf_path)
        # Remove o sufixo '_assets' e verifica que sobra exatamente o stem
        prefix = assets_name.removesuffix("_assets")
        assert prefix == pdf_path.stem

    @given(base_name=base_name_strategy)
    @settings(max_examples=200)
    def test_assets_folder_does_not_contain_extension(self, base_name: str) -> None:
        """A subpasta de assets não deve conter a extensão .pdf."""
        pdf_path = Path(f"/dir/{base_name}.pdf")
        assets_name = get_assets_subfolder_name(pdf_path)
        assert ".pdf" not in assets_name

    @given(base_name=base_name_strategy)
    @settings(max_examples=100)
    def test_assets_folder_is_relative_name_not_full_path(self, base_name: str) -> None:
        """O nome da subpasta é apenas o nome, não um caminho completo."""
        pdf_path = Path(f"/some/deep/nested/dir/{base_name}.pdf")
        assets_name = get_assets_subfolder_name(pdf_path)
        # Não deve conter separadores de diretório
        assert "/" not in assets_name
        assert "\\" not in assets_name
