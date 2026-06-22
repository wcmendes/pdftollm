"""Classe abstrata base para motores OCR.

Define a interface que todos os motores OCR devem implementar.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class OCREngine(ABC):
    """Interface abstrata para um motor OCR."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador do motor (ex: 'Tesseract', 'EasyOCR')."""
        ...

    @abstractmethod
    def extract_text(self, pdf_path: Path) -> str:
        """
        Extrai texto de um PDF usando OCR.

        Args:
            pdf_path: Caminho para o arquivo PDF.

        Returns:
            Texto extraído das páginas do PDF concatenado.
            Retorna string vazia em caso de falha.
        """
        ...
