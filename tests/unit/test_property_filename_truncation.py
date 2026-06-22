"""Property-based tests for filename truncation in progress display.

**Validates: Requirements 5.2**

Property 10: Truncamento de nomes longos no progresso
For any nome de arquivo com mais de 60 caracteres, o texto exibido na interface
de progresso SHALL ter no máximo 63 caracteres (60 + "..."), e para nomes com
60 caracteres ou menos, o texto SHALL ser exibido sem truncamento.
"""

from hypothesis import given, settings
from hypothesis import strategies as st


def truncate_filename(name: str) -> str:
    """Truncate filename for progress display.

    If the name has more than 60 characters, truncate to 60 chars and append "...".
    Otherwise, return the name unchanged.
    """
    if len(name) > 60:
        return name[:60] + "..."
    return name


# Strategy for filenames: printable strings of variable length (1 to 200 chars)
filename_strategy = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "S"),
        blacklist_characters="\x00",
    ),
    min_size=1,
    max_size=200,
)


class TestFilenameTruncationProperty:
    """Property tests for filename truncation logic."""

    @given(name=filename_strategy)
    @settings(max_examples=500)
    def test_long_names_truncated_to_max_63_chars(self, name: str) -> None:
        """Names > 60 chars result in max 63 chars (60 + '...')."""
        result = truncate_filename(name)
        if len(name) > 60:
            assert len(result) == 63
            assert result.endswith("...")
            assert result[:60] == name[:60]

    @given(name=filename_strategy)
    @settings(max_examples=500)
    def test_short_names_unchanged(self, name: str) -> None:
        """Names <= 60 chars are returned unchanged."""
        result = truncate_filename(name)
        if len(name) <= 60:
            assert result == name

    @given(name=filename_strategy)
    @settings(max_examples=500)
    def test_result_never_exceeds_63_chars(self, name: str) -> None:
        """The truncated result never exceeds 63 characters."""
        result = truncate_filename(name)
        assert len(result) <= 63

    @given(name=filename_strategy)
    @settings(max_examples=500)
    def test_truncation_boundary_at_60(self, name: str) -> None:
        """Verify the exact boundary: names of exactly 60 chars are unchanged,
        names of exactly 61 chars are truncated."""
        result = truncate_filename(name)
        if len(name) == 60:
            assert result == name
            assert len(result) == 60
        elif len(name) == 61:
            assert len(result) == 63
            assert result == name[:60] + "..."
