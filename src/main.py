"""Ponto de entrada da aplicação PDF to Markdown Converter.

Inicializa a janela principal do tkinter, configura o I18nManager
para internacionalização e instancia a MainWindow com todos os
widgets da interface gráfica.
"""

import logging
import sys
import tkinter as tk
from pathlib import Path

from src.gui.main_window import MainWindow
from src.i18n.i18n_manager import I18nManager

logger = logging.getLogger(__name__)

# Configurações da janela principal
MIN_WIDTH = 700
MIN_HEIGHT = 550
APP_ICON_NAME = "icon.png"


def _configure_logging() -> None:
    """Configura o logging básico da aplicação."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _set_icon(root: tk.Tk) -> None:
    """Configura o ícone da janela principal, se disponível.

    Procura o arquivo de ícone no diretório assets/ na raiz do projeto.
    Se o arquivo não existir, a aplicação continua sem ícone.

    Args:
        root: Instância raiz do tkinter.
    """
    # Diretório raiz do projeto (src/main.py -> src -> project_root)
    project_root = Path(__file__).parent.parent
    icon_path = project_root / "assets" / APP_ICON_NAME

    if icon_path.exists():
        try:
            icon_image = tk.PhotoImage(file=str(icon_path))
            root.iconphoto(True, icon_image)
        except tk.TclError:
            logger.warning("Não foi possível carregar o ícone: %s", icon_path)
    else:
        logger.debug("Arquivo de ícone não encontrado: %s", icon_path)


def main() -> None:
    """Função principal da aplicação.

    Inicializa o tkinter, o gerenciador de i18n, a janela principal
    e inicia o loop de eventos.
    """
    _configure_logging()
    logger.info("Iniciando PDF2LLM Converter")

    # Criar instância raiz do tkinter (com suporte a drag-and-drop se disponível)
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
    except ImportError:
        root = tk.Tk()

    # Configurar tamanho mínimo da janela
    root.minsize(MIN_WIDTH, MIN_HEIGHT)

    # Inicializar gerenciador de internacionalização
    i18n = I18nManager()

    # Configurar título da janela via i18n
    root.title(i18n.t("window.title"))

    # Configurar ícone (se disponível)
    _set_icon(root)

    # Instanciar a janela principal com todos os widgets
    _app = MainWindow(root, i18n)  # noqa: F841

    logger.info("Aplicação pronta, iniciando mainloop")

    # Iniciar loop de eventos do tkinter
    root.mainloop()


if __name__ == "__main__":
    sys.exit(main() or 0)
