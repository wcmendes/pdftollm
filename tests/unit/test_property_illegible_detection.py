"""Testes de propriedade para detecção de Markdown ilegível.

**Validates: Requirements 8.1**

Property 12: Para qualquer conteúdo Markdown e contagem de páginas, o
MarkdownQualityDetector SHALL classificar como ilegível se e somente se
o conteúdo tiver menos de 50 caracteres alfanuméricos por página em média.
Conteúdos com 50 ou mais caracteres alfanuméricos por página SHALL ser
classificados como legíveis.
"""

from hypothesis import given, settings, assume
from hypothesis import strategies as st

from src.ocr.markdown_quality_detector import MarkdownQualityDetector


# ─── Estratégias de geração ─────────────────────────────────────────────────────

# Caracteres alfanuméricos (contam para o threshold)
_alphanumeric_chars = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
)

# Caracteres não-alfanuméricos (não contam para o threshold)
_non_alphanumeric_chars = " \t\n\r!@#$%^&*()-_=+[]{}|;:',.<>?/~`\"\\—–·•"

# Estratégia para gerar contagem de páginas válida (≥ 1)
_page_count = st.integers(min_value=1, max_value=100)


# ─── Testes de propriedade ──────────────────────────────────────────────────────


class TestPropertyIllegibleDetection:
    """Property 12: Detecção de Markdown ilegível.

    **Validates: Requirements 8.1**
    """

    @given(
        alnum_count=st.integers(min_value=0, max_value=5000),
        non_alnum_count=st.integers(min_value=0, max_value=200),
        page_count=_page_count,
    )
    @settings(max_examples=500, deadline=None)
    def test_illegible_when_avg_below_threshold(
        self, alnum_count: int, non_alnum_count: int, page_count: int
    ):
        """Conteúdo com < 50 chars alfanuméricos por página é classificado como ilegível."""
        # Filtrar para garantir que estamos abaixo do threshold
        assume(alnum_count / page_count < 50)

        # Construir conteúdo com número exato de chars alfanuméricos
        content = "a" * alnum_count + " " * non_alnum_count

        result = MarkdownQualityDetector.is_illegible(content, page_count)
        assert result is True, (
            f"Deveria ser ilegível: {alnum_count} chars alnum / {page_count} páginas "
            f"= {alnum_count / page_count:.2f} chars/página (< 50)"
        )

    @given(
        alnum_count=st.integers(min_value=50, max_value=5000),
        non_alnum_count=st.integers(min_value=0, max_value=200),
        page_count=_page_count,
    )
    @settings(max_examples=500, deadline=None)
    def test_legible_when_avg_at_or_above_threshold(
        self, alnum_count: int, non_alnum_count: int, page_count: int
    ):
        """Conteúdo com ≥ 50 chars alfanuméricos por página é classificado como legível."""
        # Filtrar para garantir que estamos no threshold ou acima
        assume(alnum_count / page_count >= 50)

        # Construir conteúdo com número exato de chars alfanuméricos
        content = "a" * alnum_count + " " * non_alnum_count

        result = MarkdownQualityDetector.is_illegible(content, page_count)
        assert result is False, (
            f"Deveria ser legível: {alnum_count} chars alnum / {page_count} páginas "
            f"= {alnum_count / page_count:.2f} chars/página (≥ 50)"
        )

    @given(
        alnum_text=st.text(alphabet=_alphanumeric_chars, min_size=0, max_size=500),
        non_alnum_text=st.text(
            alphabet=_non_alphanumeric_chars, min_size=0, max_size=200
        ),
        page_count=_page_count,
    )
    @settings(max_examples=500, deadline=None)
    def test_classification_matches_formula(
        self, alnum_text: str, non_alnum_text: str, page_count: int
    ):
        """A classificação corresponde à fórmula: ilegível ⟺ alnum_count / page_count < 50."""
        # Mistura os textos (chars alfanuméricos e não-alfanuméricos)
        content = alnum_text + non_alnum_text

        # Calcular a expectativa manualmente
        actual_alnum_count = sum(1 for ch in content if ch.isalnum())
        avg_per_page = actual_alnum_count / page_count
        expected_illegible = avg_per_page < 50

        result = MarkdownQualityDetector.is_illegible(content, page_count)
        assert result == expected_illegible, (
            f"Classificação incorreta: {actual_alnum_count} chars alnum / "
            f"{page_count} páginas = {avg_per_page:.2f} chars/página. "
            f"Esperado ilegível={expected_illegible}, obteve={result}"
        )

    @given(
        content=st.text(min_size=0, max_size=300),
    )
    @settings(max_examples=200, deadline=None)
    def test_zero_pages_always_illegible(self, content: str):
        """Com page_count ≤ 0, o conteúdo é sempre classificado como ilegível."""
        assert MarkdownQualityDetector.is_illegible(content, 0) is True
        assert MarkdownQualityDetector.is_illegible(content, -1) is True

    @given(
        page_count=_page_count,
        non_alnum_text=st.text(
            alphabet=_non_alphanumeric_chars, min_size=0, max_size=300
        ),
    )
    @settings(max_examples=200, deadline=None)
    def test_only_non_alphanumeric_always_illegible(
        self, page_count: int, non_alnum_text: str
    ):
        """Conteúdo sem nenhum caractere alfanumérico é sempre ilegível."""
        # Verificar que o texto gerado realmente não tem chars alfanuméricos
        assume(sum(1 for ch in non_alnum_text if ch.isalnum()) == 0)

        result = MarkdownQualityDetector.is_illegible(non_alnum_text, page_count)
        assert result is True, (
            "Conteúdo sem chars alfanuméricos deveria sempre ser ilegível"
        )

    @given(
        page_count=_page_count,
    )
    @settings(max_examples=200, deadline=None)
    def test_exactly_at_boundary(self, page_count: int):
        """Conteúdo com exatamente 50 * page_count chars alfanuméricos é legível (boundary)."""
        exact_count = 50 * page_count
        content = "x" * exact_count

        result = MarkdownQualityDetector.is_illegible(content, page_count)
        assert result is False, (
            f"Exatamente 50 chars/página (={exact_count}/{page_count}) "
            f"deveria ser legível (≥ 50)"
        )

    @given(
        page_count=_page_count,
    )
    @settings(max_examples=200, deadline=None)
    def test_one_below_boundary(self, page_count: int):
        """Conteúdo com (50 * page_count - 1) chars alfanuméricos é ilegível (boundary)."""
        just_below = 50 * page_count - 1
        assume(just_below >= 0)
        content = "x" * just_below

        result = MarkdownQualityDetector.is_illegible(content, page_count)
        assert result is True, (
            f"Um abaixo do limiar ({just_below}/{page_count} = "
            f"{just_below / page_count:.4f} chars/página) deveria ser ilegível (< 50)"
        )
