"""Testes unitários para o AboutDialog.

Valida a criação do diálogo Sobre, exibição de informações do autor,
links clicáveis e integração com I18nManager.
"""

import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest

from src.gui.about_dialog import AboutDialog
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


@pytest.fixture(scope="module")
def root(tk_root):
    """Reutiliza a instância session-scoped do tkinter."""
    # Limpa filhos restantes de testes anteriores
    for child in tk_root.winfo_children():
        try:
            child.destroy()
        except tk.TclError:
            pass
    return tk_root


@pytest.fixture
def about_dialog(root: tk.Tk, i18n: I18nManager) -> AboutDialog:
    """Cria instância do AboutDialog para testes."""
    return AboutDialog(root, i18n)


class TestAboutDialogConstants:
    """Testes das constantes da classe AboutDialog."""

    def test_author_constant(self) -> None:
        """O autor deve ser William Mendes."""
        assert AboutDialog.AUTHOR == "William Mendes"

    def test_github_url_constant(self) -> None:
        """A URL do GitHub deve estar correta."""
        assert AboutDialog.GITHUB_URL == "https://github.com/wcmendes/pdftollm"

    def test_lattes_url_constant(self) -> None:
        """A URL do Lattes deve estar correta."""
        assert AboutDialog.LATTES_URL == "https://lattes.cnpq.br/7726054867638395"

    def test_version_constant(self) -> None:
        """A versão deve estar definida."""
        assert AboutDialog.VERSION == "0.1.0-beta"

    def test_year_constant(self) -> None:
        """O ano deve estar definido."""
        assert AboutDialog.YEAR == "2026"


class TestAboutDialogShow:
    """Testes de exibição do diálogo Sobre."""

    def test_show_creates_modal_toplevel_with_correct_title(
        self, root: tk.Tk, i18n: I18nManager
    ) -> None:
        """show() deve criar uma janela Toplevel modal com título traduzido.
        Testa tanto PT_BR quanto EN na mesma instância root."""
        # Teste em PT_BR (default)
        about = AboutDialog(root, i18n)

        dialog_title = None
        dialog_was_modal = False

        def check_and_close():
            nonlocal dialog_title, dialog_was_modal
            dialog_title = about._dialog.title()
            grab_status = about._dialog.grab_status()
            dialog_was_modal = grab_status == "local"
            about._dialog.destroy()

        root.after(50, check_and_close)
        about.show()

        assert dialog_title == "Sobre"
        assert dialog_was_modal

        # Teste em EN (mesma root)
        i18n.set_locale(Locale.EN)
        about_en = AboutDialog(root, i18n)

        en_title = None

        def check_and_close_en():
            nonlocal en_title
            en_title = about_en._dialog.title()
            about_en._dialog.destroy()

        root.after(50, check_and_close_en)
        about_en.show()

        assert en_title == "About"


class TestAboutDialogOpenLink:
    """Testes do método _open_link."""

    def test_open_link_calls_webbrowser(
        self, about_dialog: AboutDialog
    ) -> None:
        """_open_link deve chamar webbrowser.open com a URL fornecida."""
        with patch("src.gui.about_dialog.webbrowser.open") as mock_open:
            about_dialog._open_link("http://example.com")
            mock_open.assert_called_once_with("http://example.com")

    def test_open_github_link(self, about_dialog: AboutDialog) -> None:
        """_open_link deve abrir o link do GitHub corretamente."""
        with patch("src.gui.about_dialog.webbrowser.open") as mock_open:
            about_dialog._open_link(AboutDialog.GITHUB_URL)
            mock_open.assert_called_once_with("https://github.com/wcmendes/pdftollm")

    def test_open_lattes_link(self, about_dialog: AboutDialog) -> None:
        """_open_link deve abrir o link do Lattes corretamente."""
        with patch("src.gui.about_dialog.webbrowser.open") as mock_open:
            about_dialog._open_link(AboutDialog.LATTES_URL)
            mock_open.assert_called_once_with(
                "https://lattes.cnpq.br/7726054867638395"
            )


class TestAboutDialogIntegration:
    """Testes de integração do AboutDialog com MainWindow."""

    def test_main_window_about_button_has_command(
        self, root: tk.Tk, i18n: I18nManager
    ) -> None:
        """O botão Sobre na MainWindow deve ter comando configurado."""
        from src.gui.main_window import MainWindow

        mw = MainWindow(root, i18n)
        # O botão deve ter um comando (não vazio)
        command = mw._about_button.cget("command")
        assert command != ""
