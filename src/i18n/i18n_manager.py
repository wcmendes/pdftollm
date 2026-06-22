"""Gerenciador de internacionalização (i18n) da aplicação.

Carrega catálogos de tradução em JSON, permite troca ao vivo de idioma,
notifica listeners registrados e persiste preferência de idioma do usuário.
"""

import json
import logging
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src.models.data_models import Locale

logger = logging.getLogger(__name__)


class I18nManager:
    """Gerencia traduções e preferência de idioma."""

    DEFAULT_LOCALE = Locale.PT_BR

    def __init__(self, config_dir: Path | None = None) -> None:
        """Inicializa o gerenciador de i18n.

        Carrega catálogos de tradução e restaura preferência salva.
        Se nenhuma preferência existir, usa PT_BR como padrão.

        Args:
            config_dir: Diretório para persistência de preferências.
                        Se None, usa o padrão da plataforma.
        """
        self._config_dir = config_dir or self._get_default_config_dir()
        self._listeners: list[Callable[[], None]] = []
        self._catalogs: dict[Locale, dict[str, str]] = self._load_catalogs()

        saved_locale = self._load_preference()
        self._current_locale: Locale = saved_locale if saved_locale else self.DEFAULT_LOCALE

    @property
    def current_locale(self) -> Locale:
        """Retorna o idioma atualmente ativo."""
        return self._current_locale

    def set_locale(self, locale: Locale) -> None:
        """Altera o idioma e persiste a preferência.

        Notifica listeners registrados para atualizar a GUI.

        Args:
            locale: O novo idioma a ser ativado.
        """
        self._current_locale = locale
        self._save_preference(locale)
        for listener in self._listeners:
            try:
                listener()
            except Exception:
                logger.exception("Erro ao notificar listener de troca de idioma")

    def t(self, key: str) -> str:
        """Traduz uma chave para o idioma atual.

        Retorna a string traduzida ou a própria chave se não encontrada.

        Args:
            key: Chave de tradução (ex: "buttons.convert").

        Returns:
            String traduzida ou a própria chave como fallback.
        """
        catalog = self._catalogs.get(self._current_locale, {})
        translation = catalog.get(key)
        if translation is None:
            logger.warning(
                "Chave de tradução não encontrada: '%s' para locale '%s'",
                key,
                self._current_locale.value,
            )
            return key
        return translation

    def register_listener(self, callback: Callable[[], None]) -> None:
        """Registra callback para ser notificado na troca de idioma.

        Args:
            callback: Função sem argumentos chamada quando o idioma muda.
        """
        self._listeners.append(callback)

    def _load_catalogs(self) -> dict[Locale, dict[str, str]]:
        """Carrega catálogos JSON de tradução do diretório de recursos.

        Procura arquivos JSON no diretório locales/ na raiz do projeto.

        Returns:
            Dicionário mapeando cada Locale ao seu catálogo de traduções.
        """
        catalogs: dict[Locale, dict[str, str]] = {}
        locales_dir = self._get_locales_dir()

        for locale in Locale:
            json_path = locales_dir / f"{locale.value}.json"
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    catalogs[locale] = json.load(f)
            except FileNotFoundError:
                logger.warning(
                    "Arquivo de tradução não encontrado: %s", json_path
                )
                catalogs[locale] = {}
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(
                    "Erro ao carregar catálogo de tradução '%s': %s",
                    json_path,
                    e,
                )
                catalogs[locale] = {}

        return catalogs

    def _save_preference(self, locale: Locale) -> None:
        """Persiste preferência de idioma no diretório de configuração.

        Args:
            locale: O idioma a ser salvo como preferência.
        """
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            preference = {
                "locale": locale.value,
                "saved_at": datetime.now(timezone.utc).isoformat(),
            }
            pref_file = self._config_dir / "preferences.json"
            with open(pref_file, "w", encoding="utf-8") as f:
                json.dump(preference, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.warning("Erro ao salvar preferência de idioma: %s", e)

    def _load_preference(self) -> Locale | None:
        """Carrega preferência de idioma salva.

        Returns:
            O Locale salvo, ou None se não existir ou for inválido.
        """
        pref_file = self._config_dir / "preferences.json"
        try:
            with open(pref_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            locale_value = data.get("locale")
            if locale_value:
                return Locale(locale_value)
        except FileNotFoundError:
            pass
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning("Erro ao carregar preferência de idioma: %s", e)
        return None

    @staticmethod
    def _get_default_config_dir() -> Path:
        """Retorna o diretório padrão de configuração da plataforma.

        Windows: %APPDATA%/pdfconverter/
        Linux/macOS: ~/.config/pdfconverter/
        """
        if platform.system() == "Windows":
            appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
            return appdata / "pdfconverter"
        else:
            return Path.home() / ".config" / "pdfconverter"

    @staticmethod
    def _get_locales_dir() -> Path:
        """Retorna o caminho do diretório de locales.

        Busca o diretório locales/ na raiz do projeto.
        """
        # Navigate from src/i18n/i18n_manager.py -> src/i18n -> src -> project_root
        return Path(__file__).parent.parent.parent / "locales"
