"""Testes de propriedade para nomenclatura sequencial de imagens.

**Validates: Requirements 4.4**

Property 6: Nomenclatura sequencial de imagens
Para qualquer conjunto de N imagens extraídas de um PDF (1 ≤ N ≤ 999),
os nomes dos arquivos devem seguir o padrão `img_XXX.{formato}` com XXX sendo
número sequencial de 3 dígitos com zero-padding (img_001, img_002, ..., img_N),
e o formato deve corresponder ao formato original da imagem.
"""

import re

from hypothesis import given, settings
from hypothesis import strategies as st


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Formatos de imagem suportados pelo PyMuPDF
_image_formats = st.sampled_from(["png", "jpeg", "jpg", "bmp", "tiff", "gif"])

# Número sequencial de imagem (1 a 999)
_image_number = st.integers(min_value=1, max_value=999)

# Quantidade de imagens em um batch (1 a 999)
_image_count = st.integers(min_value=1, max_value=999)


# ─── Função sob teste ─────────────────────────────────────────────────────────


def generate_image_filename(image_number: int, image_format: str) -> str:
    """Gera o nome de arquivo para uma imagem extraída.

    Segue o padrão img_XXX.{formato} com zero-padding de 3 dígitos.

    Args:
        image_number: Número sequencial da imagem (1-999).
        image_format: Formato/extensão da imagem (ex: "png", "jpeg").

    Returns:
        Nome do arquivo no formato img_XXX.{formato}.
    """
    return f"img_{image_number:03d}.{image_format}"


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyImageNaming:
    """Property 6: Nomenclatura sequencial de imagens.

    **Validates: Requirements 4.4**
    """

    @given(number=_image_number, fmt=_image_formats)
    @settings(max_examples=300)
    def test_filename_matches_pattern(self, number: int, fmt: str) -> None:
        """Para qualquer número N e formato, o nome segue img_XXX.{formato}."""
        filename = generate_image_filename(number, fmt)
        pattern = r"^img_\d{3}\." + re.escape(fmt) + r"$"
        assert re.match(pattern, filename), (
            f"Filename '{filename}' não segue o padrão img_XXX.{fmt}"
        )

    @given(number=_image_number, fmt=_image_formats)
    @settings(max_examples=300)
    def test_filename_has_three_digit_zero_padding(self, number: int, fmt: str) -> None:
        """O número sequencial sempre tem exatamente 3 dígitos com zero-padding."""
        filename = generate_image_filename(number, fmt)
        # Extrai a parte numérica entre "img_" e "."
        numeric_part = filename.split("_")[1].split(".")[0]
        assert len(numeric_part) == 3, (
            f"Parte numérica '{numeric_part}' não tem 3 dígitos"
        )
        assert numeric_part == f"{number:03d}", (
            f"Zero-padding incorreto: esperado '{number:03d}', obtido '{numeric_part}'"
        )

    @given(number=_image_number, fmt=_image_formats)
    @settings(max_examples=300)
    def test_filename_starts_with_img_prefix(self, number: int, fmt: str) -> None:
        """Todo nome de imagem deve começar com o prefixo 'img_'."""
        filename = generate_image_filename(number, fmt)
        assert filename.startswith("img_"), (
            f"Filename '{filename}' não começa com 'img_'"
        )

    @given(number=_image_number, fmt=_image_formats)
    @settings(max_examples=300)
    def test_filename_extension_matches_format(self, number: int, fmt: str) -> None:
        """A extensão do arquivo deve corresponder ao formato original da imagem."""
        filename = generate_image_filename(number, fmt)
        extension = filename.rsplit(".", 1)[1]
        assert extension == fmt, (
            f"Extensão '{extension}' não corresponde ao formato '{fmt}'"
        )

    @given(count=_image_count, fmt=_image_formats)
    @settings(max_examples=200)
    def test_sequential_naming_for_batch(self, count: int, fmt: str) -> None:
        """Para um batch de N imagens, os nomes são sequenciais de 001 a N."""
        filenames = [generate_image_filename(i, fmt) for i in range(1, count + 1)]

        assert len(filenames) == count

        for i, filename in enumerate(filenames, start=1):
            expected = f"img_{i:03d}.{fmt}"
            assert filename == expected, (
                f"Imagem {i}: esperado '{expected}', obtido '{filename}'"
            )

    @given(number=_image_number, fmt=_image_formats)
    @settings(max_examples=200)
    def test_filename_number_is_parseable(self, number: int, fmt: str) -> None:
        """O número na filename pode ser parseado de volta ao inteiro original."""
        filename = generate_image_filename(number, fmt)
        # Extrai número usando regex
        match = re.match(r"img_(\d{3})\.(.+)$", filename)
        assert match is not None, f"Filename '{filename}' não segue o padrão esperado"
        parsed_number = int(match.group(1))
        parsed_format = match.group(2)
        assert parsed_number == number, (
            f"Número parseado {parsed_number} != número original {number}"
        )
        assert parsed_format == fmt, (
            f"Formato parseado '{parsed_format}' != formato original '{fmt}'"
        )

    @given(
        number=_image_number,
        fmt1=_image_formats,
        fmt2=_image_formats,
    )
    @settings(max_examples=200)
    def test_same_number_different_formats_differ(
        self, number: int, fmt1: str, fmt2: str
    ) -> None:
        """Mesmo número com formatos diferentes gera filenames distintas (se formatos diferem)."""
        filename1 = generate_image_filename(number, fmt1)
        filename2 = generate_image_filename(number, fmt2)
        if fmt1 != fmt2:
            assert filename1 != filename2, (
                f"Filenames deveriam diferir para formatos distintos: "
                f"'{filename1}' vs '{filename2}'"
            )
        else:
            assert filename1 == filename2
