"""Testes unitários para o I18nManager.

Valida o comportamento do I18nManager em cenários:
- Carregamento de catálogos de tradução
- Tradução de chaves existentes e inexistentes
- Troca de idioma com notificação de listeners
- Persistência de preferência de idioma (round-trip)
- Uso de PT_BR como padrão quando sem preferência
- Comportamento em diretório de config inexistente
"""

import json
from pathlib import Path

import pytest

from src.i18n.i18n_manager import I18nManager
from src.models.data_models import Locale


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Cria diretório temporário para persistência de configurações."""
    config = tmp_path / "config"
    config.mkdir()
    return config


@pytest.fixture
def i18n(config_dir: Path) -> I18nManager:
    """Cria instância do I18nManager com diretório de config temporário."""
    return I18nManager(config_dir=config_dir)


class TestI18nManagerInitialization:
    """Testes de inicialização do I18nManager."""

    def test_default_locale_is_pt_br(self, config_dir: Path) -> None:
        """Sem preferência salva, o idioma padrão deve ser PT_BR."""
        manager = I18nManager(config_dir=config_dir)
        assert manager.current_locale == Locale.PT_BR

    def test_restores_saved_preference(self, config_dir: Path) -> None:
        """Se existe preferência salva, deve restaurar na inicialização."""
        # Salva preferência manualmente
        pref_file = config_dir / "preferences.json"
        pref_file.write_text(
            json.dumps({"locale": "en", "saved_at": "2024-01-01T12:00:00"}),
            encoding="utf-8",
        )
        manager = I18nManager(config_dir=config_dir)
        assert manager.current_locale == Locale.EN

    def test_invalid_preference_falls_back_to_default(
        self, config_dir: Path
    ) -> None:
        """Se preferência é inválida, usa padrão PT_BR."""
        pref_file = config_dir / "preferences.json"
        pref_file.write_text("not valid json", encoding="utf-8")
        manager = I18nManager(config_dir=config_dir)
        assert manager.current_locale == Locale.PT_BR

    def test_unknown_locale_in_preference_falls_back(
        self, config_dir: Path
    ) -> None:
        """Se locale salvo é desconhecido, usa padrão PT_BR."""
        pref_file = config_dir / "preferences.json"
        pref_file.write_text(
            json.dumps({"locale": "fr", "saved_at": "2024-01-01T12:00:00"}),
            encoding="utf-8",
        )
        manager = I18nManager(config_dir=config_dir)
        assert manager.current_locale == Locale.PT_BR


class TestI18nManagerCatalogs:
    """Testes de carregamento de catálogos."""

    def test_catalogs_loaded_for_all_locales(self, i18n: I18nManager) -> None:
        """Deve carregar catálogos para todos os locales definidos."""
        # Verifica que ambos os catálogos foram carregados (não vazios)
        i18n.set_locale(Locale.PT_BR)
        assert i18n.t("window.title") == "Conversor PDF para Markdown"

        i18n.set_locale(Locale.EN)
        assert i18n.t("window.title") == "PDF to Markdown Converter"


class TestI18nManagerTranslation:
    """Testes da função de tradução t()."""

    def test_translate_existing_key_pt_br(self, i18n: I18nManager) -> None:
        """Traduz chave existente para PT_BR."""
        i18n.set_locale(Locale.PT_BR)
        assert i18n.t("buttons.convert") == "Converter"

    def test_translate_existing_key_en(self, i18n: I18nManager) -> None:
        """Traduz chave existente para EN."""
        i18n.set_locale(Locale.EN)
        assert i18n.t("buttons.convert") == "Convert"

    def test_missing_key_returns_key_itself(self, i18n: I18nManager) -> None:
        """Chave inexistente retorna a própria chave como fallback."""
        result = i18n.t("nonexistent.key.here")
        assert result == "nonexistent.key.here"

    def test_translate_after_locale_switch(self, i18n: I18nManager) -> None:
        """Após troca de idioma, t() retorna texto no novo idioma."""
        i18n.set_locale(Locale.PT_BR)
        assert i18n.t("buttons.about") == "Sobre"

        i18n.set_locale(Locale.EN)
        assert i18n.t("buttons.about") == "About"


class TestI18nManagerSetLocale:
    """Testes da troca de idioma."""

    def test_set_locale_updates_current_locale(self, i18n: I18nManager) -> None:
        """set_locale deve atualizar o idioma ativo."""
        i18n.set_locale(Locale.EN)
        assert i18n.current_locale == Locale.EN

        i18n.set_locale(Locale.PT_BR)
        assert i18n.current_locale == Locale.PT_BR

    def test_set_locale_notifies_listeners(self, i18n: I18nManager) -> None:
        """set_locale deve notificar todos os listeners registrados."""
        called: list[bool] = []
        i18n.register_listener(lambda: called.append(True))
        i18n.set_locale(Locale.EN)
        assert len(called) == 1

    def test_set_locale_notifies_multiple_listeners(
        self, i18n: I18nManager
    ) -> None:
        """set_locale notifica múltiplos listeners."""
        call_count = [0]

        def listener1() -> None:
            call_count[0] += 1

        def listener2() -> None:
            call_count[0] += 1

        i18n.register_listener(listener1)
        i18n.register_listener(listener2)
        i18n.set_locale(Locale.EN)
        assert call_count[0] == 2

    def test_listener_error_does_not_prevent_other_listeners(
        self, i18n: I18nManager
    ) -> None:
        """Erro em um listener não impede notificação dos demais."""
        called: list[str] = []

        def failing_listener() -> None:
            raise RuntimeError("Listener error")

        def good_listener() -> None:
            called.append("ok")

        i18n.register_listener(failing_listener)
        i18n.register_listener(good_listener)
        i18n.set_locale(Locale.EN)
        assert "ok" in called


class TestI18nManagerPersistence:
    """Testes de persistência de preferência."""

    def test_save_and_load_preference_round_trip(
        self, config_dir: Path
    ) -> None:
        """Salvar e carregar preferência deve retornar o mesmo locale."""
        manager = I18nManager(config_dir=config_dir)
        manager.set_locale(Locale.EN)

        # Cria nova instância para verificar persistência
        manager2 = I18nManager(config_dir=config_dir)
        assert manager2.current_locale == Locale.EN

    def test_persistence_file_format(self, config_dir: Path) -> None:
        """O arquivo de preferência deve conter locale e saved_at."""
        manager = I18nManager(config_dir=config_dir)
        manager.set_locale(Locale.EN)

        pref_file = config_dir / "preferences.json"
        assert pref_file.exists()
        data = json.loads(pref_file.read_text(encoding="utf-8"))
        assert data["locale"] == "en"
        assert "saved_at" in data

    def test_persistence_creates_directory_if_not_exists(
        self, tmp_path: Path
    ) -> None:
        """Se diretório de config não existe, deve ser criado."""
        new_config_dir = tmp_path / "nonexistent" / "deeply" / "nested"
        manager = I18nManager(config_dir=new_config_dir)
        manager.set_locale(Locale.EN)
        assert new_config_dir.exists()
        assert (new_config_dir / "preferences.json").exists()


class TestI18nManagerRegisterListener:
    """Testes de registro de listeners."""

    def test_register_single_listener(self, i18n: I18nManager) -> None:
        """Deve aceitar registro de um listener."""
        called = [False]
        i18n.register_listener(lambda: called.__setitem__(0, True))
        i18n.set_locale(Locale.EN)
        assert called[0] is True

    def test_register_multiple_listeners(self, i18n: I18nManager) -> None:
        """Deve aceitar múltiplos listeners."""
        results: list[int] = []
        i18n.register_listener(lambda: results.append(1))
        i18n.register_listener(lambda: results.append(2))
        i18n.set_locale(Locale.EN)
        assert results == [1, 2]
