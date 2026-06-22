"""Testes de propriedade para completude do catálogo de traduções.

**Validates: Requirements 10.1, 10.6**

Property 17: Completude do catálogo de traduções
Para qualquer chave de tradução registrada no catálogo da aplicação e para qualquer
locale suportado (PT_BR, EN), a tradução deve existir e ser uma string não-vazia.
"""

import json
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.data_models import Locale


# ─── Carregamento dos catálogos ───────────────────────────────────────────────

LOCALES_DIR = Path(__file__).parent.parent.parent / "locales"

SUPPORTED_LOCALES = list(Locale)

CATALOGS: dict[Locale, dict[str, str]] = {}
for _locale in SUPPORTED_LOCALES:
    _json_path = LOCALES_DIR / f"{_locale.value}.json"
    with open(_json_path, "r", encoding="utf-8") as _f:
        CATALOGS[_locale] = json.load(_f)

# União de todas as chaves presentes em qualquer catálogo
ALL_KEYS = sorted(
    set().union(*(catalog.keys() for catalog in CATALOGS.values()))
)


# ─── Estratégias ──────────────────────────────────────────────────────────────

key_strategy = st.sampled_from(ALL_KEYS)
locale_strategy = st.sampled_from(SUPPORTED_LOCALES)


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyI18nCatalogCompleteness:
    """Property 17: Completude do catálogo de traduções.

    **Validates: Requirements 10.1, 10.6**
    """

    @given(key=key_strategy, locale=locale_strategy)
    @settings(max_examples=500)
    def test_every_key_exists_in_every_locale(self, key: str, locale: Locale) -> None:
        """Para qualquer chave e qualquer locale, a tradução deve existir."""
        catalog = CATALOGS[locale]
        assert key in catalog, (
            f"Chave '{key}' ausente no catálogo '{locale.value}'"
        )

    @given(key=key_strategy, locale=locale_strategy)
    @settings(max_examples=500)
    def test_every_translation_is_non_empty_string(self, key: str, locale: Locale) -> None:
        """Para qualquer chave e qualquer locale, a tradução deve ser string não-vazia."""
        catalog = CATALOGS[locale]
        if key in catalog:
            value = catalog[key]
            assert isinstance(value, str), (
                f"Tradução para '{key}' em '{locale.value}' não é string: {type(value)}"
            )
            assert value.strip() != "", (
                f"Tradução para '{key}' em '{locale.value}' é vazia ou apenas espaços"
            )

    def test_both_catalogs_have_identical_key_sets(self) -> None:
        """Ambos os catálogos devem ter exatamente o mesmo conjunto de chaves."""
        pt_br_keys = set(CATALOGS[Locale.PT_BR].keys())
        en_keys = set(CATALOGS[Locale.EN].keys())

        missing_in_en = pt_br_keys - en_keys
        missing_in_pt_br = en_keys - pt_br_keys

        assert not missing_in_en, (
            f"Chaves presentes em pt-br mas ausentes em en: {sorted(missing_in_en)}"
        )
        assert not missing_in_pt_br, (
            f"Chaves presentes em en mas ausentes em pt-br: {sorted(missing_in_pt_br)}"
        )

    def test_all_locales_have_catalogs(self) -> None:
        """Todos os locales suportados devem ter um catálogo carregado."""
        for locale in SUPPORTED_LOCALES:
            assert locale in CATALOGS, f"Catálogo ausente para locale '{locale.value}'"
            assert len(CATALOGS[locale]) > 0, (
                f"Catálogo vazio para locale '{locale.value}'"
            )
