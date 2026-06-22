"""Testes unitários para o PDFValidator.

Valida o comportamento do PDFValidator em cenários:
- Arquivo PDF válido
- Arquivo inexistente
- Extensão não-PDF
- Arquivo corrompido
- PDF protegido por senha
- PDF sem páginas (edge case)
"""

import tempfile
from pathlib import Path

import fitz  # PyMuPDF
import pytest

from src.converters.pdf_validator import PDFValidator
from src.models.data_models import ValidationResult


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """Cria um PDF válido com 1 página para testes."""
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello, World!")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def multi_page_pdf(tmp_path: Path) -> Path:
    """Cria um PDF válido com múltiplas páginas."""
    pdf_path = tmp_path / "multi_page.pdf"
    doc = fitz.open()
    for i in range(5):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def password_protected_pdf(tmp_path: Path) -> Path:
    """Cria um PDF protegido por senha."""
    pdf_path = tmp_path / "protected.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Secret content")
    doc.save(
        str(pdf_path),
        encryption=fitz.PDF_ENCRYPT_AES_256,
        user_pw="userpass",
        owner_pw="ownerpass",
    )
    doc.close()
    return pdf_path


@pytest.fixture
def corrupted_pdf(tmp_path: Path) -> Path:
    """Cria um arquivo com extensão .pdf mas conteúdo inválido."""
    pdf_path = tmp_path / "corrupted.pdf"
    pdf_path.write_bytes(b"This is not a valid PDF content at all!")
    return pdf_path


@pytest.fixture
def non_pdf_file(tmp_path: Path) -> Path:
    """Cria um arquivo com extensão diferente de .pdf."""
    txt_path = tmp_path / "document.txt"
    txt_path.write_text("Just a text file")
    return txt_path


class TestPDFValidatorValidFile:
    """Testes com PDFs válidos."""

    def test_valid_pdf_returns_valid(self, valid_pdf: Path) -> None:
        result = PDFValidator.validate(valid_pdf)
        assert result.is_valid is True
        assert result.reason == ""

    def test_multi_page_pdf_returns_valid(self, multi_page_pdf: Path) -> None:
        result = PDFValidator.validate(multi_page_pdf)
        assert result.is_valid is True
        assert result.reason == ""


class TestPDFValidatorFileExistence:
    """Testes de existência de arquivo."""

    def test_nonexistent_file_returns_invalid(self, tmp_path: Path) -> None:
        fake_path = tmp_path / "nonexistent.pdf"
        result = PDFValidator.validate(fake_path)
        assert result.is_valid is False
        assert "não encontrado" in result.reason


class TestPDFValidatorExtension:
    """Testes de validação de extensão."""

    def test_non_pdf_extension_returns_invalid(self, non_pdf_file: Path) -> None:
        result = PDFValidator.validate(non_pdf_file)
        assert result.is_valid is False
        assert ".pdf" in result.reason

    def test_pdf_extension_case_insensitive(self, tmp_path: Path) -> None:
        """PDF com extensão .PDF (maiúscula) deve ser aceito."""
        pdf_path = tmp_path / "document.PDF"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Content")
        doc.save(str(pdf_path))
        doc.close()

        result = PDFValidator.validate(pdf_path)
        assert result.is_valid is True


class TestPDFValidatorCorruption:
    """Testes com arquivos corrompidos."""

    def test_corrupted_file_returns_invalid(self, corrupted_pdf: Path) -> None:
        result = PDFValidator.validate(corrupted_pdf)
        assert result.is_valid is False
        assert "corrompido" in result.reason.lower() or "inválido" in result.reason.lower()

    def test_empty_file_with_pdf_extension(self, tmp_path: Path) -> None:
        """Arquivo vazio com extensão .pdf deve ser detectado como corrompido."""
        pdf_path = tmp_path / "empty.pdf"
        pdf_path.write_bytes(b"")
        result = PDFValidator.validate(pdf_path)
        assert result.is_valid is False


class TestPDFValidatorPasswordProtection:
    """Testes com PDFs protegidos por senha."""

    def test_password_protected_returns_invalid(
        self, password_protected_pdf: Path
    ) -> None:
        result = PDFValidator.validate(password_protected_pdf)
        assert result.is_valid is False
        assert "senha" in result.reason.lower()


class TestPDFValidatorReturnType:
    """Verifica que o retorno é sempre ValidationResult."""

    def test_returns_validation_result_on_valid(self, valid_pdf: Path) -> None:
        result = PDFValidator.validate(valid_pdf)
        assert isinstance(result, ValidationResult)

    def test_returns_validation_result_on_invalid(self, tmp_path: Path) -> None:
        fake_path = tmp_path / "nonexistent.pdf"
        result = PDFValidator.validate(fake_path)
        assert isinstance(result, ValidationResult)
