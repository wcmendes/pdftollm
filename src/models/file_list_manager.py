"""Gerenciador de lista de arquivos PDF selecionados.

Gerencia a lista de arquivos com validação, detecção de duplicatas
e limite máximo de 50 arquivos.
"""

from pathlib import Path

from src.converters.pdf_validator import PDFValidator
from src.models.data_models import AddFilesResult


class FileListManager:
    """Gerencia a lista de arquivos PDF selecionados."""

    MAX_FILES = 50

    def __init__(self) -> None:
        self._files: list[Path] = []

    def add_files(self, files: list[Path]) -> AddFilesResult:
        """
        Adiciona arquivos à lista, rejeitando duplicatas, inválidos e excedentes.

        Para cada arquivo na lista de entrada:
        1. Valida com PDFValidator - se inválido, adiciona a rejected_invalid
        2. Verifica duplicata por caminho resolvido - se duplicata, adiciona a rejected_duplicate
        3. Verifica se excede MAX_FILES - se sim, adiciona a rejected_limit
        4. Se todas as verificações passam, adiciona a accepted e à lista interna

        Args:
            files: Lista de caminhos de arquivos a serem adicionados.

        Returns:
            AddFilesResult com arquivos categorizados em aceitos e rejeitados.
        """
        result = AddFilesResult()

        for file_path in files:
            # 1. Validação do PDF
            validation = PDFValidator.validate(file_path)
            if not validation.is_valid:
                result.rejected_invalid.append((file_path, validation.reason))
                continue

            # 2. Verificação de duplicata (por caminho resolvido)
            resolved = file_path.resolve()
            if any(f.resolve() == resolved for f in self._files):
                result.rejected_duplicate.append(file_path)
                continue

            # 3. Verificação de limite
            if len(self._files) >= self.MAX_FILES:
                result.rejected_limit.append(file_path)
                continue

            # 4. Arquivo aceito
            self._files.append(file_path)
            result.accepted.append(file_path)

        return result

    def remove_file(self, file_path: Path) -> None:
        """
        Remove um arquivo da lista por caminho resolvido.

        Args:
            file_path: Caminho do arquivo a ser removido.
        """
        resolved = file_path.resolve()
        self._files = [f for f in self._files if f.resolve() != resolved]

    def clear(self) -> None:
        """Limpa toda a lista de arquivos."""
        self._files.clear()

    @property
    def files(self) -> list[Path]:
        """Retorna cópia da lista de arquivos."""
        return list(self._files)

    @property
    def count(self) -> int:
        """Retorna quantidade de arquivos na lista."""
        return len(self._files)
