"""Testes unitários para a MainWindow.

Valida a criação de todos os widgets, integração com I18nManager
e a atualização ao vivo de textos na troca de idioma.
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path

import pytest

from src.gui.main_window import MainWindow
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
def main_window(root: tk.Tk, i18n: I18nManager) -> MainWindow:
    """Cria instância da MainWindow para testes."""
    return MainWindow(root, i18n)


class TestMainWindowCreation:
    """Testes de criação da MainWindow e seus widgets."""

    def test_window_title_set(self, main_window: MainWindow) -> None:
        """O título da janela deve ser definido via i18n."""
        assert main_window.root.title() == "Conversor PDF para Markdown"

    def test_file_listbox_exists(self, main_window: MainWindow) -> None:
        """A listbox de arquivos deve existir."""
        assert isinstance(main_window._file_listbox, tk.Listbox)

    def test_file_scrollbar_exists(self, main_window: MainWindow) -> None:
        """A scrollbar da lista de arquivos deve existir."""
        assert isinstance(main_window._file_scrollbar, ttk.Scrollbar)

    def test_select_files_button_exists(self, main_window: MainWindow) -> None:
        """O botão de seleção de arquivos deve existir com texto correto."""
        assert isinstance(main_window._select_files_button, ttk.Button)
        assert main_window._select_files_button.cget("text") == "Selecionar Arquivos PDF"

    def test_remove_file_button_exists(self, main_window: MainWindow) -> None:
        """O botão de remoção de arquivo deve existir com texto correto."""
        assert isinstance(main_window._remove_file_button, ttk.Button)
        assert main_window._remove_file_button.cget("text") == "Remover"

    def test_output_folder_entry_exists(self, main_window: MainWindow) -> None:
        """O campo de pasta de destino deve existir."""
        assert isinstance(main_window._output_folder_entry, ttk.Entry)

    def test_select_folder_button_exists(self, main_window: MainWindow) -> None:
        """O botão de seleção de pasta deve existir com texto correto."""
        assert isinstance(main_window._select_folder_button, ttk.Button)
        assert main_window._select_folder_button.cget("text") == "Selecionar Pasta de Destino"

    def test_extract_images_checkbox_exists(self, main_window: MainWindow) -> None:
        """O checkbox de extração de imagens deve existir com texto correto."""
        assert isinstance(main_window._extract_images_check, ttk.Checkbutton)
        assert main_window._extract_images_check.cget("text") == "Extrair imagens e objetos embutidos"

    def test_convert_button_exists(self, main_window: MainWindow) -> None:
        """O botão de converter deve existir com texto correto."""
        assert isinstance(main_window._convert_button, ttk.Button)
        assert main_window._convert_button.cget("text") == "Converter"

    def test_progress_bar_exists(self, main_window: MainWindow) -> None:
        """A barra de progresso deve existir no modo determinado."""
        assert isinstance(main_window._progress_bar, ttk.Progressbar)

    def test_current_file_label_exists(self, main_window: MainWindow) -> None:
        """O label de arquivo atual deve existir."""
        assert isinstance(main_window._current_file_label, ttk.Label)

    def test_language_combo_exists(self, main_window: MainWindow) -> None:
        """O seletor de idioma deve existir."""
        assert isinstance(main_window._language_combo, ttk.Combobox)

    def test_about_button_exists(self, main_window: MainWindow) -> None:
        """O botão Sobre deve existir com texto correto."""
        assert isinstance(main_window._about_button, ttk.Button)
        assert main_window._about_button.cget("text") == "Sobre"

    def test_language_selector_initial_value(self, main_window: MainWindow) -> None:
        """O seletor de idioma deve iniciar com PT_BR selecionado."""
        assert main_window._language_var.get() == "Português (Brasil)"


class TestMainWindowI18nLiveUpdate:
    """Testes de atualização ao vivo dos textos na troca de idioma."""

    def test_texts_update_on_locale_change(
        self, main_window: MainWindow, i18n: I18nManager
    ) -> None:
        """Todos os textos devem atualizar ao mudar o idioma para EN."""
        i18n.set_locale(Locale.EN)

        assert main_window.root.title() == "PDF to Markdown Converter"
        assert main_window._select_files_button.cget("text") == "Select PDF Files"
        assert main_window._remove_file_button.cget("text") == "Remove"
        assert main_window._select_folder_button.cget("text") == "Select Output Folder"
        assert main_window._extract_images_check.cget("text") == "Extract images and embedded objects"
        assert main_window._convert_button.cget("text") == "Convert"
        assert main_window._about_button.cget("text") == "About"
        assert main_window._language_label.cget("text") == "Language:"
        assert main_window._output_folder_label.cget("text") == "Output Folder:"
        assert main_window._file_list_label.cget("text") == "Selected Files"

    def test_language_selector_value_updates(
        self, main_window: MainWindow, i18n: I18nManager
    ) -> None:
        """O valor do seletor de idioma deve atualizar na troca."""
        i18n.set_locale(Locale.EN)
        assert main_window._language_var.get() == "English (US)"

    def test_texts_revert_on_locale_switch_back(
        self, main_window: MainWindow, i18n: I18nManager
    ) -> None:
        """Textos devem voltar ao PT_BR quando o idioma retornar."""
        i18n.set_locale(Locale.EN)
        i18n.set_locale(Locale.PT_BR)

        assert main_window.root.title() == "Conversor PDF para Markdown"
        assert main_window._convert_button.cget("text") == "Converter"
        assert main_window._language_var.get() == "Português (Brasil)"

    def test_listener_registered_on_i18n(
        self, i18n: I18nManager, root: tk.Tk
    ) -> None:
        """A MainWindow deve registrar um listener no I18nManager."""
        initial_listener_count = len(i18n._listeners)
        MainWindow(root, i18n)
        assert len(i18n._listeners) == initial_listener_count + 1
