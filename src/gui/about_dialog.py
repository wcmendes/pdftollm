"""Diálogo Sobre da aplicação PDF to Markdown Converter.

Exibe informações sobre o autor, links relevantes, versão e licenciamento.
Implementa janela modal com integração ao I18nManager para textos traduzíveis.
"""

import tkinter as tk
from tkinter import ttk
import webbrowser

from src.i18n.i18n_manager import I18nManager


class AboutDialog:
    """Diálogo 'Sobre' da aplicação.

    Exibe informações do autor, links para GitHub e Lattes,
    versão atual e ano de publicação como janela modal.
    """

    AUTHOR = "William Mendes"
    GITHUB_URL = "http://github.com/wcmendes"
    LATTES_URL = "https://lattes.cnpq.br/7726054867638395"
    VERSION = "1.0.0"
    YEAR = "2025"

    def __init__(self, parent: tk.Tk, i18n: I18nManager) -> None:
        """Inicializa o diálogo Sobre.

        Args:
            parent: Janela pai (raiz tkinter).
            i18n: Gerenciador de internacionalização para textos da GUI.
        """
        self._parent = parent
        self._i18n = i18n

    def show(self) -> None:
        """Exibe o diálogo Sobre como janela modal."""
        # Criar janela Toplevel
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title(self._i18n.t("about.title"))
        self._dialog.resizable(False, False)
        self._dialog.transient(self._parent)

        # Tornar modal
        self._dialog.grab_set()

        # Configurar tamanho e posição centralizada
        dialog_width = 420
        dialog_height = 320
        parent_x = self._parent.winfo_rootx()
        parent_y = self._parent.winfo_rooty()
        parent_width = self._parent.winfo_width()
        parent_height = self._parent.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        self._dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

        # Frame principal com padding
        main_frame = ttk.Frame(self._dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Nome da aplicação (título)
        app_name_label = ttk.Label(
            main_frame,
            text=self._i18n.t("about.app_name"),
            font=("TkDefaultFont", 14, "bold"),
        )
        app_name_label.pack(pady=(0, 5))

        # Descrição
        desc_label = ttk.Label(
            main_frame,
            text=self._i18n.t("about.description"),
            wraplength=380,
            justify="center",
        )
        desc_label.pack(pady=(0, 10))

        # Versão
        version_text = self._i18n.t("about.version").format(version=self.VERSION)
        version_label = ttk.Label(main_frame, text=version_text)
        version_label.pack(pady=(0, 5))

        # Ano
        year_text = self._i18n.t("about.year").format(year=self.YEAR)
        year_label = ttk.Label(main_frame, text=year_text)
        year_label.pack(pady=(0, 10))

        # Autor
        author_label = ttk.Label(
            main_frame, text=self._i18n.t("about.author")
        )
        author_label.pack(pady=(0, 5))

        # Link GitHub (clicável)
        github_label = ttk.Label(
            main_frame,
            text=self._i18n.t("about.github"),
            foreground="blue",
            cursor="hand2",
        )
        github_label.pack(pady=(0, 5))
        github_label.bind("<Button-1>", lambda e: self._open_link(self.GITHUB_URL))

        # Link Lattes (clicável)
        lattes_label = ttk.Label(
            main_frame,
            text=self._i18n.t("about.lattes"),
            foreground="blue",
            cursor="hand2",
        )
        lattes_label.pack(pady=(0, 5))
        lattes_label.bind("<Button-1>", lambda e: self._open_link(self.LATTES_URL))

        # Licença
        license_label = ttk.Label(
            main_frame, text=self._i18n.t("about.license")
        )
        license_label.pack(pady=(0, 15))

        # Botão Fechar
        close_button = ttk.Button(
            main_frame,
            text=self._i18n.t("buttons.close"),
            command=self._dialog.destroy,
        )
        close_button.pack()

        # Aguardar fechamento do diálogo
        self._dialog.wait_window()

    def _open_link(self, url: str) -> None:
        """Abre URL no navegador padrão do sistema.

        Args:
            url: URL a ser aberta no navegador.
        """
        webbrowser.open(url)
