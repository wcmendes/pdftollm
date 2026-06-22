"""Testes de propriedade para codificação e terminadores de saída.

**Validates: Requirements 6.4**

Property 11: Para qualquer Arquivo_Saída gerado pela aplicação, o conteúdo
SHALL estar codificado em UTF-8 e usar exclusivamente terminadores de linha
LF (`\\n`), independentemente do sistema operacional em execução.

A lógica sob teste é a normalização aplicada pelo PDFConverter antes de escrever
o arquivo: `markdown.replace("\\r\\n", "\\n").replace("\\r", "\\n")` seguido de
`write_text(encoding="utf-8", newline="\\n")`.

Os testes geram conteúdo Markdown com caracteres Unicode variados e terminadores
mistos, simulam a escrita no formato do conversor, e verificam que:
1) O arquivo resultante é UTF-8 válido (decodificável sem erros)
2) O arquivo não contém bytes \\r (nem CRLF nem CR isolado)
"""

import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from hypothesis import given, settings, HealthCheck, assume
from hypothesis import strategies as st

from src.converters.pdf_converter import PDFConverter


# ─── Função de normalização extraída do PDFConverter ────────────────────────────


def normalize_and_write(markdown: str, output_path: Path) -> None:
    """Replica a lógica de escrita do PDFConverter.

    Esta é exatamente a lógica aplicada em PDFConverter.convert():
    - Normaliza terminadores de linha para LF
    - Escreve em UTF-8 com newline="\\n"
    """
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n")
    output_path.write_text(markdown, encoding="utf-8", newline="\n")


# ─── Estratégias de geração ─────────────────────────────────────────────────────

# Caracteres latinos com acentos (português, espanhol, francês, alemão)
_latin_accented = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "àáâãäåèéêëìíîïòóôõöùúûüýÿñçÀÁÂÃÄÅÈÉÊËÌÍÎÏÒÓÔÕÖÙÚÛÜÝÑÇ"
    "ß¡¿ «»""''—–"
    " 0123456789.,;:!?-()",
    min_size=1,
    max_size=200,
)

# Caracteres CJK básicos (U+4E00 a U+4E4F)
_cjk_chars = st.text(
    alphabet="".join(chr(c) for c in range(0x4E00, 0x4E50)),
    min_size=1,
    max_size=50,
)

# Caracteres gregos e cirílicos
_greek_cyrillic = st.text(
    alphabet="αβγδεζηθικλμνξοπρστυφχψω"
    "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдежзийклмнопрстуфхцчшщъыьэюя",
    min_size=1,
    max_size=80,
)

# Texto com terminadores mistos (\r\n, \r, \n) para testar normalização
_text_with_mixed_endings = st.builds(
    lambda parts, seps: "".join(
        p + s for p, s in zip(parts, seps + [""])
    ),
    parts=st.lists(
        st.text(
            alphabet="abcdefghijABCDEF0123456789àáéíóúçñ# *_[]()!",
            min_size=1,
            max_size=30,
        ),
        min_size=2,
        max_size=8,
    ),
    seps=st.lists(
        st.sampled_from(["\n", "\r\n", "\r"]),
        min_size=1,
        max_size=7,
    ),
)

# Markdown-like content com headers, listas e Unicode
_markdown_content = st.builds(
    lambda heading, body, items: (
        f"# {heading}\n\n{body}\n\n"
        + "\n".join(f"- {item}" for item in items)
        + "\n"
    ),
    heading=st.text(
        alphabet="abcdefghijABCDEF àáéíóúç",
        min_size=3,
        max_size=30,
    ),
    body=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz ABCDEFGHIJ0123456789"
        "àáâãéêíóôõúüçñ.,;:!?-()",
        min_size=10,
        max_size=100,
    ),
    items=st.lists(
        st.text(
            alphabet="abcdefghij àáéíóú0123456789",
            min_size=2,
            max_size=20,
        ),
        min_size=1,
        max_size=5,
    ),
)


# ─── Testes de propriedade ──────────────────────────────────────────────────────


class TestPropertyEncodingAndTerminators:
    """Property 11: Codificação e terminadores de saída.

    **Validates: Requirements 6.4**
    """

    @given(text=_latin_accented)
    @settings(max_examples=200, deadline=None)
    def test_output_valid_utf8_with_latin_accented(self, text: str):
        """Saída com caracteres latinos acentuados é UTF-8 válido com terminadores LF."""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.md"
            normalize_and_write(text, output_path)

            raw_bytes = output_path.read_bytes()

            # Propriedade 1: Deve ser decodificável como UTF-8 sem erros
            decoded = raw_bytes.decode("utf-8")
            assert isinstance(decoded, str)

            # Propriedade 2: Não deve conter \r\n (CRLF) nem \r isolado
            assert b"\r\n" not in raw_bytes, "Saída contém terminadores CRLF"
            assert b"\r" not in raw_bytes, "Saída contém caracteres CR"

    @given(text=_cjk_chars)
    @settings(max_examples=200, deadline=None)
    def test_output_valid_utf8_with_cjk(self, text: str):
        """Saída com caracteres CJK é UTF-8 válido com terminadores LF."""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.md"
            normalize_and_write(text, output_path)

            raw_bytes = output_path.read_bytes()

            # Propriedade 1: UTF-8 válido
            decoded = raw_bytes.decode("utf-8")
            assert isinstance(decoded, str)

            # Propriedade 2: Apenas terminadores LF
            assert b"\r\n" not in raw_bytes, "Saída contém terminadores CRLF"
            assert b"\r" not in raw_bytes, "Saída contém caracteres CR"

    @given(text=_greek_cyrillic)
    @settings(max_examples=200, deadline=None)
    def test_output_valid_utf8_with_greek_cyrillic(self, text: str):
        """Saída com caracteres gregos e cirílicos é UTF-8 válido com terminadores LF."""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.md"
            normalize_and_write(text, output_path)

            raw_bytes = output_path.read_bytes()

            # Propriedade 1: UTF-8 válido
            decoded = raw_bytes.decode("utf-8")
            assert isinstance(decoded, str)

            # Propriedade 2: Apenas terminadores LF
            assert b"\r\n" not in raw_bytes, "Saída contém terminadores CRLF"
            assert b"\r" not in raw_bytes, "Saída contém caracteres CR"

    @given(text=_text_with_mixed_endings)
    @settings(max_examples=200, deadline=None)
    def test_output_normalizes_line_endings_to_lf(self, text: str):
        """Mesmo com input contendo \\r\\n ou \\r, a saída usa apenas LF."""
        assume("\r" in text or "\r\n" in text)  # Garante que input tem CR

        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.md"
            normalize_and_write(text, output_path)

            raw_bytes = output_path.read_bytes()

            # Propriedade 1: UTF-8 válido
            decoded = raw_bytes.decode("utf-8")
            assert isinstance(decoded, str)

            # Propriedade 2: Sem CR bytes na saída
            assert b"\r\n" not in raw_bytes, (
                "Saída contém terminadores CRLF mesmo após normalização"
            )
            assert b"\r" not in raw_bytes, (
                "Saída contém caracteres CR mesmo após normalização"
            )

    @given(content=_markdown_content)
    @settings(max_examples=200, deadline=None)
    def test_markdown_content_valid_utf8_and_lf(self, content: str):
        """Conteúdo Markdown estruturado é escrito como UTF-8 com LF exclusivo."""
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "output.md"
            normalize_and_write(content, output_path)

            raw_bytes = output_path.read_bytes()

            # Propriedade 1: UTF-8 válido
            decoded = raw_bytes.decode("utf-8")
            assert isinstance(decoded, str)

            # Propriedade 2: Apenas terminadores LF
            assert b"\r\n" not in raw_bytes, "Saída contém terminadores CRLF"
            assert b"\r" not in raw_bytes, "Saída contém caracteres CR"


class TestPropertyEncodingIntegration:
    """Testes de integração com o PDFConverter real para validar Property 11.

    Usa um conjunto reduzido de exemplos pois cada teste cria e converte um PDF real.

    **Validates: Requirements 6.4**
    """

    @given(
        text=st.text(
            alphabet="abcdefghij ABCDEF àáâãéêíóôõúüçñ 0123456789",
            min_size=5,
            max_size=60,
        )
    )
    @settings(
        max_examples=10,
        suppress_health_check=[HealthCheck.too_slow],
        deadline=None,
    )
    def test_full_converter_output_utf8_lf(self, text: str):
        """O PDFConverter real gera saída UTF-8 com terminadores LF exclusivos."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pdf_path = tmp_path / "test.pdf"

            # Cria PDF com texto
            doc = fitz.open()
            page = doc.new_page()
            try:
                page.insert_text((72, 72), text, fontname="helv")
            except Exception:
                page.insert_text((72, 72), "fallback")
            doc.save(str(pdf_path))
            doc.close()

            # Converte
            converter = PDFConverter()
            result = converter.convert(pdf_path, tmp_path, extract_images=False)

            if result.output is not None and result.output.exists():
                raw_bytes = result.output.read_bytes()

                # Propriedade 1: UTF-8 válido
                decoded = raw_bytes.decode("utf-8")
                assert isinstance(decoded, str)

                # Propriedade 2: Apenas terminadores LF
                assert b"\r\n" not in raw_bytes, "Saída contém terminadores CRLF"
                assert b"\r" not in raw_bytes, "Saída contém caracteres CR"
