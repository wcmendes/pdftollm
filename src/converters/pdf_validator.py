"""Validador de arquivos PDF.

Verifica se um arquivo é um PDF válido, não-corrompido e não-protegido por senha.
"""

from pathlib import Path

import fitz  # PyMuPDF

from src.models.data_models import ValidationResult


class PDFValidator:
    """Valida arquivos PDF antes da conversão."""

    @staticmethod
    def validate(file_path: Path) -> ValidationResult:
        """
        Verifica se o arquivo é um PDF válido.

        Checks:
        1. Arquivo existe e tem extensão .pdf
        2. Pode ser aberto pelo PyMuPDF (não corrompido)
        3. Não está protegido por senha
        4. Tem pelo menos 1 página

        Args:
            file_path: Caminho para o arquivo a ser validado.

        Returns:
            ValidationResult com is_valid e motivo de rejeição.
        """
        # 1. Verifica existência do arquivo
        if not file_path.exists():
            return ValidationResult(
                is_valid=False,
                reason="Arquivo não encontrado"
            )

        # 2. Verifica extensão .pdf (case-insensitive)
        if file_path.suffix.lower() != ".pdf":
            return ValidationResult(
                is_valid=False,
                reason="Arquivo não possui extensão .pdf"
            )

        # 3. Tenta abrir com PyMuPDF para verificar integridade
        try:
            doc = fitz.open(str(file_path))
        except Exception:
            return ValidationResult(
                is_valid=False,
                reason="Arquivo corrompido ou formato inválido"
            )

        try:
            # 4. Verifica se está protegido por senha
            if doc.is_encrypted:
                return ValidationResult(
                    is_valid=False,
                    reason="Arquivo protegido por senha"
                )

            # 5. Verifica se tem pelo menos 1 página
            if doc.page_count < 1:
                return ValidationResult(
                    is_valid=False,
                    reason="PDF não contém páginas"
                )
        finally:
            doc.close()

        return ValidationResult(is_valid=True)
