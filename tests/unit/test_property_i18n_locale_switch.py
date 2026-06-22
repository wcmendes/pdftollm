"""Testes de propriedade para consistência da troca de idioma ao vivo.

**Validates: Requirements 10.3**

Property 18: Consistência da troca de idioma ao vivo
Para qualquer sequência de trocas de locale, chamar t(key) após a última troca
deve sempre retornar o texto correspondente ao locale atualmente ativo, e nunca
texto de um locale anterior.
"""

import json
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.i18n.i18n_manager import I18nManager
from src.models.data_models import Locale


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Estratégia para gerar sequências de trocas de locale
locale_sequence_strategy = st.lists(
    st.sampled_from([Locale.PT_BR, Locale.EN]),
    min_size=1,
    max_size=20,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _load_catalog(locale: Locale) -> dict[str, str]:
    """Carrega catálogo de tradução diretamente do JSON para comparação."""
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    json_path = locales_dir / f"{locale.value}.json"
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Pré-carrega catálogos para evitar I/O repetida dentro dos testes
_CATALOGS: dict[Locale, dict[str, str]] = {
    Locale.PT_BR: _load_catalog(Locale.PT_BR),
    Locale.EN: _load_catalog(Locale.EN),
}

# Todas as chaves de tradução presentes em ambos os catálogos
_ALL_KEYS: list[str] = sorted(
    set(_CATALOGS[Locale.PT_BR].keys()) & set(_CATALOGS[Locale.EN].keys())
)


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyI18nLocaleSwitch:
    """Property 18: Consistência da troca de idioma ao vivo.

    **Validates: Requirements 10.3**
    """

    @given(locale_sequence=locale_sequence_strategy)
    @settings(max_examples=200)
    def test_t_returns_active_locale_text_after_switches(
        self, locale_sequence: list[Locale]
    ) -> None:
        """Após qualquer sequência de trocas, t(key) retorna texto do locale ativo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            manager = I18nManager(config_dir=config_dir)

            # Aplica toda a sequência de trocas de locale
            for locale in locale_sequence:
                manager.set_locale(locale)

            # O locale ativo é o último da sequência
            active_locale = locale_sequence[-1]

            # Verifica que TODAS as chaves retornam texto do locale ativo
            for key in _ALL_KEYS:
                expected = _CATALOGS[active_locale][key]
                actual = manager.t(key)
                assert actual == expected, (
                    f"Após sequência de trocas terminando em {active_locale.value}, "
                    f"t('{key}') retornou '{actual}' mas esperado '{expected}'"
                )

    @given(locale_sequence=locale_sequence_strategy)
    @settings(max_examples=200)
    def test_current_locale_matches_last_set(
        self, locale_sequence: list[Locale]
    ) -> None:
        """Após sequência de trocas, current_locale é o último locale definido."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            manager = I18nManager(config_dir=config_dir)

            for locale in locale_sequence:
                manager.set_locale(locale)

            assert manager.current_locale == locale_sequence[-1]

    @given(locale_sequence=locale_sequence_strategy)
    @settings(max_examples=200)
    def test_no_key_returns_previous_locale_text(
        self, locale_sequence: list[Locale]
    ) -> None:
        """Nenhuma chave retorna texto de locale anterior ao ativo."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            manager = I18nManager(config_dir=config_dir)

            for locale in locale_sequence:
                manager.set_locale(locale)

            active_locale = locale_sequence[-1]
            # Determina o "outro" locale
            other_locale = Locale.EN if active_locale == Locale.PT_BR else Locale.PT_BR

            for key in _ALL_KEYS:
                actual = manager.t(key)
                other_value = _CATALOGS[other_locale][key]
                # Se os dois catálogos têm valores diferentes para esta chave,
                # o resultado NÃO deve ser igual ao valor do outro locale
                if _CATALOGS[active_locale][key] != other_value:
                    assert actual != other_value, (
                        f"Após sequência terminando em {active_locale.value}, "
                        f"t('{key}') retornou texto do locale {other_locale.value}: '{actual}'"
                    )
