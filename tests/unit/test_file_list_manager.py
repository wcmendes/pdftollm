"""Testes unitários para o FileListManager.

Valida o comportamento do FileListManager em cenários:
- Adição de arquivos válidos
- Rejeição de arquivos inválidos (não-PDF, corrompidos)
- Rejeição de duplicatas
- Rejeição por exceder limite de 50 arquivos
- Remoção de arquivos
- Limpeza da lista
- Propriedade files retorna cópia
"""

from pathlib import Path

import fitz  # PyMuPDF
import pytest

from src.models.data_models import AddFilesResult
from src.models.file_list_manager import FileListManager


@pytest.fixture
def manager() -> FileListManager:
    """Cria um FileListManager vazio."""
    return FileListManager()


@pytest.fixture
def valid_pdf(tmp_path: Path) -> Path:
    """Cria um PDF válido com 1 página."""
    pdf_path = tmp_path / "doc1.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello")
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture
def valid_pdfs(tmp_path: Path) -> list[Path]:
    """Cria 3 PDFs válidos distintos."""
    paths = []
    for i in range(3):
        pdf_path = tmp_path / f"doc{i}.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), f"Content {i}")
        doc.save(str(pdf_path))
        doc.close()
        paths.append(pdf_path)
    return paths


def _create_valid_pdf(path: Path) -> Path:
    """Utilitário para criar um PDF válido no caminho especificado."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Content")
    doc.save(str(path))
    doc.close()
    return path


class TestFileListManagerAddFiles:
    """Testes de adição de arquivos."""

    def test_add_valid_files(
        self, manager: FileListManager, valid_pdfs: list[Path]
    ) -> None:
        result = manager.add_files(valid_pdfs)
        assert len(result.accepted) == 3
        assert manager.count == 3
        assert result.rejected_invalid == []
        assert result.rejected_duplicate == []
        assert result.rejected_limit == []

    def test_add_single_valid_file(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        result = manager.add_files([valid_pdf])
        assert result.accepted == [valid_pdf]
        assert manager.count == 1

    def test_add_returns_add_files_result(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        result = manager.add_files([valid_pdf])
        assert isinstance(result, AddFilesResult)


class TestFileListManagerRejectInvalid:
    """Testes de rejeição de arquivos inválidos."""

    def test_reject_nonexistent_file(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        fake = tmp_path / "nonexistent.pdf"
        result = manager.add_files([fake])
        assert len(result.rejected_invalid) == 1
        assert result.rejected_invalid[0][0] == fake
        assert manager.count == 0

    def test_reject_non_pdf_extension(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        txt_file = tmp_path / "file.txt"
        txt_file.write_text("not a pdf")
        result = manager.add_files([txt_file])
        assert len(result.rejected_invalid) == 1
        assert manager.count == 0

    def test_reject_corrupted_file(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        corrupted = tmp_path / "corrupted.pdf"
        corrupted.write_bytes(b"not valid pdf bytes")
        result = manager.add_files([corrupted])
        assert len(result.rejected_invalid) == 1
        assert "corrompido" in result.rejected_invalid[0][1].lower() or "inválido" in result.rejected_invalid[0][1].lower()
        assert manager.count == 0

    def test_reject_invalid_includes_reason(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        fake = tmp_path / "missing.pdf"
        result = manager.add_files([fake])
        path, reason = result.rejected_invalid[0]
        assert path == fake
        assert reason != ""


class TestFileListManagerRejectDuplicate:
    """Testes de rejeição de duplicatas."""

    def test_reject_duplicate_file(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        manager.add_files([valid_pdf])
        result = manager.add_files([valid_pdf])
        assert result.rejected_duplicate == [valid_pdf]
        assert result.accepted == []
        assert manager.count == 1

    def test_reject_duplicate_by_resolved_path(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        """Duplicatas são detectadas por caminho resolvido."""
        manager.add_files([valid_pdf])
        # Cria um caminho diferente que resolve para o mesmo arquivo
        relative_path = valid_pdf.parent / "." / valid_pdf.name
        result = manager.add_files([relative_path])
        assert len(result.rejected_duplicate) == 1
        assert manager.count == 1


class TestFileListManagerRejectLimit:
    """Testes de rejeição por limite de 50 arquivos."""

    def test_max_files_constant(self) -> None:
        assert FileListManager.MAX_FILES == 50

    def test_reject_files_exceeding_limit(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        # Preenche até o limite
        for i in range(50):
            _create_valid_pdf(tmp_path / f"fill_{i}.pdf")

        fill_files = [tmp_path / f"fill_{i}.pdf" for i in range(50)]
        result = manager.add_files(fill_files)
        assert len(result.accepted) == 50
        assert manager.count == 50

        # Tenta adicionar mais um
        extra = _create_valid_pdf(tmp_path / "extra.pdf")
        result = manager.add_files([extra])
        assert result.rejected_limit == [extra]
        assert result.accepted == []
        assert manager.count == 50

    def test_partial_acceptance_at_limit(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        """Se há espaço para 2 mas 3 são adicionados, aceita 2 e rejeita 1."""
        # Preenche com 48
        for i in range(48):
            _create_valid_pdf(tmp_path / f"fill_{i}.pdf")
        fill_files = [tmp_path / f"fill_{i}.pdf" for i in range(48)]
        manager.add_files(fill_files)
        assert manager.count == 48

        # Tenta adicionar 3 mais
        extras = []
        for i in range(3):
            extras.append(_create_valid_pdf(tmp_path / f"extra_{i}.pdf"))

        result = manager.add_files(extras)
        assert len(result.accepted) == 2
        assert len(result.rejected_limit) == 1
        assert manager.count == 50


class TestFileListManagerMixedResults:
    """Testes com resultados mistos (aceitos + rejeitados)."""

    def test_mixed_valid_and_invalid(
        self, manager: FileListManager, tmp_path: Path
    ) -> None:
        valid = _create_valid_pdf(tmp_path / "valid.pdf")
        invalid = tmp_path / "invalid.txt"
        invalid.write_text("not pdf")

        result = manager.add_files([valid, invalid])
        assert result.accepted == [valid]
        assert len(result.rejected_invalid) == 1
        assert manager.count == 1


class TestFileListManagerRemoveFile:
    """Testes de remoção de arquivos."""

    def test_remove_existing_file(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        manager.add_files([valid_pdf])
        assert manager.count == 1
        manager.remove_file(valid_pdf)
        assert manager.count == 0

    def test_remove_nonexistent_file_no_error(
        self, manager: FileListManager, valid_pdf: Path, tmp_path: Path
    ) -> None:
        """Remover arquivo que não está na lista não deve gerar erro."""
        manager.add_files([valid_pdf])
        other = tmp_path / "other.pdf"
        manager.remove_file(other)
        assert manager.count == 1


class TestFileListManagerClear:
    """Testes de limpeza da lista."""

    def test_clear_removes_all_files(
        self, manager: FileListManager, valid_pdfs: list[Path]
    ) -> None:
        manager.add_files(valid_pdfs)
        assert manager.count == 3
        manager.clear()
        assert manager.count == 0
        assert manager.files == []

    def test_clear_empty_list(self, manager: FileListManager) -> None:
        manager.clear()
        assert manager.count == 0


class TestFileListManagerProperties:
    """Testes das propriedades files e count."""

    def test_files_returns_copy(
        self, manager: FileListManager, valid_pdf: Path
    ) -> None:
        """A propriedade files deve retornar cópia, não referência interna."""
        manager.add_files([valid_pdf])
        files_copy = manager.files
        files_copy.clear()
        assert manager.count == 1

    def test_count_reflects_state(
        self, manager: FileListManager, valid_pdfs: list[Path]
    ) -> None:
        assert manager.count == 0
        manager.add_files(valid_pdfs)
        assert manager.count == 3
        manager.remove_file(valid_pdfs[0])
        assert manager.count == 2

    def test_empty_manager_state(self, manager: FileListManager) -> None:
        assert manager.count == 0
        assert manager.files == []
