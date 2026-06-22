"""Testes de propriedade para FileListManager.

**Validates: Requirements 1.2, 1.3, 1.5, 1.6**

Property 1: Invariantes do FileListManager
Para qualquer sequência de operações de adição e remoção de arquivos,
a lista resultante deve:
- Conter no máximo 50 itens (MAX_FILES)
- Não conter duplicatas (caminhos resolvidos únicos)
- Não conter arquivos inválidos (todos passaram pela validação PyMuPDF)
"""

import tempfile
from pathlib import Path

import fitz  # PyMuPDF
from hypothesis import given, settings
from hypothesis import strategies as st

from src.models.file_list_manager import FileListManager


# ─── Setup: pool de PDFs válidos criados uma vez ──────────────────────────────

# Cria um diretório temporário persistente para o módulo de testes
_tmp_dir = tempfile.mkdtemp(prefix="pbt_flm_")
_PDF_POOL: list[Path] = []

for _i in range(10):
    _pdf_path = Path(_tmp_dir) / f"test_doc_{_i}.pdf"
    _doc = fitz.open()
    _page = _doc.new_page()
    _page.insert_text((72, 72), f"Test content for document {_i}")
    _doc.save(str(_pdf_path))
    _doc.close()
    _PDF_POOL.append(_pdf_path)


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Operações possíveis no FileListManager
_operations = st.sampled_from(["add", "remove", "clear"])

# Índices para selecionar subconjuntos de PDFs do pool
_pdf_indices = st.lists(
    st.integers(min_value=0, max_value=9),
    min_size=1,
    max_size=10,
)

# Estratégia combinada: sequência de (operação, indices dos PDFs a usar)
_operation_with_data = st.tuples(
    _operations,
    _pdf_indices,
)

full_operation_sequence = st.lists(_operation_with_data, min_size=1, max_size=20)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _is_valid_pdf(path: Path) -> bool:
    """Verifica se o arquivo é um PDF válido usando PyMuPDF."""
    try:
        doc = fitz.open(str(path))
        is_valid = not doc.is_encrypted and doc.page_count > 0
        doc.close()
        return is_valid
    except Exception:
        return False


def _execute_operations(
    ops: list[tuple[str, list[int]]],
) -> FileListManager:
    """Executa uma sequência de operações sobre um FileListManager novo."""
    manager = FileListManager()

    for operation, indices in ops:
        if operation == "add":
            files_to_add = [_PDF_POOL[i] for i in indices]
            manager.add_files(files_to_add)
        elif operation == "remove":
            if manager.count > 0:
                idx = indices[0] % manager.count
                file_to_remove = manager.files[idx]
                manager.remove_file(file_to_remove)
        elif operation == "clear":
            manager.clear()

    return manager


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyFileListManagerInvariants:
    """Property 1: Invariantes do FileListManager.

    **Validates: Requirements 1.2, 1.3, 1.5, 1.6**
    """

    @given(ops=full_operation_sequence)
    @settings(max_examples=100, deadline=None)
    def test_invariants_after_random_operations(
        self, ops: list[tuple[str, list[int]]]
    ) -> None:
        """Após qualquer sequência de operações, as 3 invariantes devem valer.

        Invariantes verificadas a cada passo:
        1. manager.count <= 50 (nunca excede limite)
        2. Sem duplicatas (caminhos resolvidos são únicos)
        3. Todos os arquivos na lista são PDFs válidos
        """
        manager = FileListManager()

        for operation, indices in ops:
            if operation == "add":
                files_to_add = [_PDF_POOL[i] for i in indices]
                manager.add_files(files_to_add)
            elif operation == "remove":
                if manager.count > 0:
                    idx = indices[0] % manager.count
                    manager.remove_file(manager.files[idx])
            elif operation == "clear":
                manager.clear()

            # Invariante 1: Nunca excede MAX_FILES
            assert manager.count <= FileListManager.MAX_FILES, (
                f"Lista excedeu limite: {manager.count} > {FileListManager.MAX_FILES}"
            )

            # Invariante 2: Sem duplicatas (por caminho resolvido)
            resolved_paths = [f.resolve() for f in manager.files]
            assert len(resolved_paths) == len(set(resolved_paths)), (
                f"Lista contém duplicatas: {resolved_paths}"
            )

            # Invariante 3: Todos os arquivos são PDFs válidos
            for f in manager.files:
                assert _is_valid_pdf(f), (
                    f"Arquivo inválido encontrado na lista: {f}"
                )

    @given(ops=full_operation_sequence)
    @settings(max_examples=100, deadline=None)
    def test_count_never_exceeds_max_files(
        self, ops: list[tuple[str, list[int]]]
    ) -> None:
        """A contagem nunca excede MAX_FILES, independente de quantos adds são feitos."""
        manager = _execute_operations(ops)
        assert manager.count <= FileListManager.MAX_FILES

    @given(ops=full_operation_sequence)
    @settings(max_examples=100, deadline=None)
    def test_no_duplicates_after_operations(
        self, ops: list[tuple[str, list[int]]]
    ) -> None:
        """A lista nunca contém duplicatas após qualquer sequência de operações."""
        manager = _execute_operations(ops)
        resolved = [f.resolve() for f in manager.files]
        assert len(resolved) == len(set(resolved))

    @given(ops=full_operation_sequence)
    @settings(max_examples=100, deadline=None)
    def test_all_files_are_valid_pdfs(
        self, ops: list[tuple[str, list[int]]]
    ) -> None:
        """Todos os arquivos presentes na lista são PDFs válidos."""
        manager = _execute_operations(ops)
        for f in manager.files:
            assert _is_valid_pdf(f), f"Arquivo inválido na lista: {f}"

    @given(
        add_counts=st.lists(
            st.integers(min_value=1, max_value=10),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_repeated_adds_respect_limit(
        self, add_counts: list[int]
    ) -> None:
        """Adições repetidas (mesmo com mesmos arquivos) respeitam o limite."""
        manager = FileListManager()

        for count in add_counts:
            subset = _PDF_POOL[:count]
            manager.add_files(subset)
            assert manager.count <= FileListManager.MAX_FILES

    @given(
        ops=st.lists(
            st.sampled_from(["add", "remove", "clear"]),
            min_size=5,
            max_size=30,
        )
    )
    @settings(max_examples=80, deadline=None)
    def test_count_matches_files_length(
        self, ops: list[str]
    ) -> None:
        """A propriedade count sempre é igual ao comprimento de files."""
        manager = FileListManager()

        for op in ops:
            if op == "add":
                manager.add_files(_PDF_POOL[:3])
            elif op == "remove":
                if manager.count > 0:
                    manager.remove_file(manager.files[0])
            elif op == "clear":
                manager.clear()

            assert manager.count == len(manager.files)
