"""Testes de propriedade para persistência de preferência de idioma (round-trip).

**Validates: Requirements 10.4**

Property 19: Persistência de preferência de idioma (round-trip)
Para qualquer locale suportado, salvar a preferência via set_locale e em seguida
criar uma nova instância de I18nManager com o mesmo config_dir deve restaurar
o locale salvo.
"""

import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from src.i18n.i18n_manager import I18nManager
from src.models.data_models import Locale


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Estratégia para gerar um locale aleatório dentre os suportados
locale_strategy = st.sampled_from([Locale.PT_BR, Locale.EN])

# Estratégia para gerar sequências de locales (simula múltiplas trocas)
locale_sequence_strategy = st.lists(
    st.sampled_from([Locale.PT_BR, Locale.EN]),
    min_size=2,
    max_size=20,
)


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyI18nPersistence:
    """Property 19: Persistência de preferência de idioma (round-trip).

    **Validates: Requirements 10.4**
    """

    @given(locale=locale_strategy)
    @settings(max_examples=200)
    def test_save_and_reload_restores_locale(self, locale: Locale) -> None:
        """Salvar locale e criar nova instância com mesmo config_dir restaura o locale."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Cria instância e salva preferência
            manager1 = I18nManager(config_dir=config_dir)
            manager1.set_locale(locale)

            # Cria nova instância com o MESMO config_dir
            manager2 = I18nManager(config_dir=config_dir)

            # A nova instância deve ter o locale persistido
            assert manager2.current_locale == locale, (
                f"Após salvar locale '{locale.value}' e criar nova instância, "
                f"current_locale é '{manager2.current_locale.value}' "
                f"mas esperado '{locale.value}'"
            )

    @given(locale_sequence=locale_sequence_strategy)
    @settings(max_examples=200)
    def test_sequence_of_saves_last_locale_persisted(
        self, locale_sequence: list[Locale]
    ) -> None:
        """Salvar múltiplos locales em sequência, nova instância tem o ÚLTIMO locale."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_dir = Path(tmp_dir) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)

            # Cria instância e faz múltiplas trocas de locale
            manager1 = I18nManager(config_dir=config_dir)
            for locale in locale_sequence:
                manager1.set_locale(locale)

            # Cria nova instância com o MESMO config_dir
            manager2 = I18nManager(config_dir=config_dir)

            # A nova instância deve ter o ÚLTIMO locale da sequência
            expected_locale = locale_sequence[-1]
            assert manager2.current_locale == expected_locale, (
                f"Após sequência de trocas terminando em '{expected_locale.value}', "
                f"nova instância tem current_locale '{manager2.current_locale.value}' "
                f"mas esperado '{expected_locale.value}'"
            )
