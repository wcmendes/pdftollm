"""Verificador de atualizações via GitHub Releases API.

Consulta a API do GitHub em background para verificar se há uma versão
mais recente disponível. Não bloqueia a interface.
"""

import logging
import threading
from typing import Callable

logger = logging.getLogger(__name__)

GITHUB_API_URL = "https://api.github.com/repos/wcmendes/pdftollm/releases/latest"
CURRENT_VERSION = "0.1.1-beta"


def _parse_version(version_str: str) -> tuple:
    """Converte uma string de versão em tupla comparável.

    Remove prefixos (v) e sufixos (-beta, -alpha) para comparação numérica.
    Ex: "0.1.0-beta" -> (0, 1, 0), "v1.2.3" -> (1, 2, 3)
    """
    clean = version_str.strip().lstrip("v")
    # Remover sufixos como -beta, -alpha, -rc1
    base = clean.split("-")[0]
    try:
        return tuple(int(x) for x in base.split("."))
    except ValueError:
        return (0, 0, 0)


def check_for_updates(callback: Callable[[str, str], None]) -> None:
    """Verifica atualizações em background.

    Faz uma requisição à API do GitHub para obter a última release.
    Se houver versão mais nova, chama o callback com (versão, url).
    Se não houver ou der erro, não faz nada (falha silenciosa).

    Args:
        callback: Função chamada com (latest_version, download_url)
                  apenas se houver versão nova. Chamada na thread de trabalho,
                  então o caller deve usar root.after() para atualizar a GUI.
    """
    thread = threading.Thread(target=_check_worker, args=(callback,), daemon=True)
    thread.start()


def _check_worker(callback: Callable[[str, str], None]) -> None:
    """Worker que executa na thread de background."""
    try:
        import json
        import urllib.request

        req = urllib.request.Request(
            GITHUB_API_URL,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "PDF2LLM"},
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        latest_tag = data.get("tag_name", "")
        html_url = data.get("html_url", "")

        if not latest_tag:
            return

        latest_version = _parse_version(latest_tag)
        current_version = _parse_version(CURRENT_VERSION)

        if latest_version > current_version:
            callback(latest_tag, html_url)
        else:
            logger.debug("Versão atual (%s) está atualizada.", CURRENT_VERSION)

    except Exception as e:
        # Falha silenciosa — sem internet, rate limit, etc.
        logger.debug("Verificação de atualização falhou: %s", e)
