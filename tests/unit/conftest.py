"""Configurações compartilhadas para testes unitários.

Fornece uma fixture de root tk.Tk() session-scoped para evitar problemas
de reinicialização do Tcl/Tk em Python 3.14.
"""

import tkinter as tk

import pytest


@pytest.fixture(scope="session")
def tk_root():
    """Cria instância raiz do tkinter compartilhada entre todos os testes.

    Session-scoped para evitar problemas de reinicialização do Tcl/Tk
    em Python 3.14 onde tk.Tk() falha após destroy() de uma instância anterior.
    """
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()
