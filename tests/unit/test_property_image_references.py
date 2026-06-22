"""Testes de propriedade para referências de imagem no Markdown.

**Validates: Requirements 4.5**

Property 7: Referências de imagem no Markdown
Para qualquer PDF com N imagens extraídas com extração habilitada, o Markdown
gerado deve conter exatamente N referências no formato ![imageN](caminho_relativo)
onde cada caminho aponta para o arquivo correspondente na Subpasta_Assets.
"""

import re

from hypothesis import given, settings
from hypothesis import strategies as st

from src.converters.pdf_converter import PDFConverter
from src.models.data_models import ImageInfo


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Formatos de imagem válidos suportados pelo extrator
_image_formats = st.sampled_from(["png", "jpeg", "jpg", "bmp", "tiff", "gif"])

# Gera número sequencial de imagem (1-20 para manter testes razoáveis)
_image_number = st.integers(min_value=1, max_value=999)


def _make_image_info(index: int, fmt: str, page: int, position: int) -> ImageInfo:
    """Cria um ImageInfo com nome sequencial válido."""
    filename = f"img_{index:03d}.{fmt}"
    return ImageInfo(
        filename=filename,
        format=fmt,
        page_number=page,
        position_index=position,
    )


# Estratégia para gerar listas de ImageInfo válidos (1-20 itens)
@st.composite
def image_info_list_strategy(draw: st.DrawFn) -> list[ImageInfo]:
    """Gera lista de ImageInfo com filenames e formatos válidos."""
    count = draw(st.integers(min_value=1, max_value=20))
    images: list[ImageInfo] = []
    for i in range(1, count + 1):
        fmt = draw(_image_formats)
        page = draw(st.integers(min_value=1, max_value=50))
        position = draw(st.integers(min_value=1, max_value=10))
        images.append(_make_image_info(i, fmt, page, position))
    return images


# Estratégia para gerar markdown de entrada (conteúdo simples)
_sample_markdown = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="\n#*- ",
    ),
    min_size=10,
    max_size=500,
)

# Estratégia para nomes de pasta de assets válidos
_assets_dir_name = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyz0123456789_-",
    min_size=1,
    max_size=50,
).map(lambda s: f"{s}_assets")


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyImageReferences:
    """Property 7: Referências de imagem no Markdown.

    **Validates: Requirements 4.5**
    """

    @given(
        images=image_info_list_strategy(),
        markdown=_sample_markdown,
        assets_dir=_assets_dir_name,
    )
    @settings(max_examples=200)
    def test_exactly_n_image_references(
        self, images: list[ImageInfo], markdown: str, assets_dir: str
    ) -> None:
        """O Markdown gerado contém exatamente N referências ![imageN](...)."""
        converter = PDFConverter()
        result = converter._insert_image_references(markdown, images, assets_dir)

        # Conta referências no formato ![imageN](...)
        pattern = r"!\[image\d+\]\([^)]+\)"
        references = re.findall(pattern, result)

        assert len(references) == len(images)

    @given(
        images=image_info_list_strategy(),
        markdown=_sample_markdown,
        assets_dir=_assets_dir_name,
    )
    @settings(max_examples=200)
    def test_references_have_sequential_numbering(
        self, images: list[ImageInfo], markdown: str, assets_dir: str
    ) -> None:
        """Cada referência tem numeração sequencial de 1 a N."""
        converter = PDFConverter()
        result = converter._insert_image_references(markdown, images, assets_dir)

        # Extrai números das referências
        pattern = r"!\[image(\d+)\]\([^)]+\)"
        numbers = [int(m) for m in re.findall(pattern, result)]

        expected = list(range(1, len(images) + 1))
        assert numbers == expected

    @given(
        images=image_info_list_strategy(),
        markdown=_sample_markdown,
        assets_dir=_assets_dir_name,
    )
    @settings(max_examples=200)
    def test_references_point_to_correct_assets_dir(
        self, images: list[ImageInfo], markdown: str, assets_dir: str
    ) -> None:
        """Cada referência aponta para o caminho correto na Subpasta_Assets."""
        converter = PDFConverter()
        result = converter._insert_image_references(markdown, images, assets_dir)

        # Extrai caminhos das referências
        pattern = r"!\[image\d+\]\(([^)]+)\)"
        paths = re.findall(pattern, result)

        assert len(paths) == len(images)
        for path, img in zip(paths, images):
            expected_path = f"{assets_dir}/{img.filename}"
            assert path == expected_path

    @given(
        images=image_info_list_strategy(),
        markdown=_sample_markdown,
        assets_dir=_assets_dir_name,
    )
    @settings(max_examples=200)
    def test_original_markdown_is_preserved(
        self, images: list[ImageInfo], markdown: str, assets_dir: str
    ) -> None:
        """O conteúdo Markdown original é preservado na saída."""
        converter = PDFConverter()
        result = converter._insert_image_references(markdown, images, assets_dir)

        # O markdown original deve estar contido no resultado
        assert markdown.rstrip() in result or markdown in result

    @given(
        markdown=_sample_markdown,
        assets_dir=_assets_dir_name,
    )
    @settings(max_examples=100)
    def test_empty_image_list_returns_unchanged_markdown(
        self, markdown: str, assets_dir: str
    ) -> None:
        """Com lista de imagens vazia, o markdown é retornado sem alteração."""
        converter = PDFConverter()
        result = converter._insert_image_references(markdown, [], assets_dir)

        assert result == markdown
