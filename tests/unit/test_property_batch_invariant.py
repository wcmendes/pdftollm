"""Testes de propriedade para invariante de conversão em batch.

**Validates: Requirements 3.5, 3.7, 5.3, 5.4**

Property 3: Invariante de conversão em batch
Para qualquer lista de N arquivos processados pelo ConversionManager,
o resultado deve satisfazer:
- succeeded + failed == total == N
- A falha de qualquer arquivo individual não impede o processamento dos demais
"""

import queue
from pathlib import Path
from unittest.mock import patch

from hypothesis import given, settings
from hypothesis import strategies as st

from src.converters.conversion_manager import ConversionManager
from src.models.data_models import (
    ConversionFileResult,
    ConversionResult,
    ConversionStatus,
    ProgressUpdate,
)


# ─── Estratégias ──────────────────────────────────────────────────────────────

# Gera uma lista de outcomes por arquivo: True = sucesso, False = falha
_file_outcomes = st.lists(
    st.booleans(),
    min_size=1,
    max_size=30,
)

# Gera tipo de falha: retorno com status de erro ou exceção
_failure_mode = st.sampled_from(["status_error", "exception"])

# Combinação de outcomes com modo de falha para cada arquivo
_batch_scenario = st.lists(
    st.tuples(
        st.booleans(),  # True = sucesso, False = falha
        _failure_mode,  # tipo de falha quando False
    ),
    min_size=1,
    max_size=30,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _create_mock_side_effect(
    scenarios: list[tuple[bool, str]],
) -> callable:
    """Cria side_effect para o mock do convert() baseado nos cenários.

    Cada cenário é (sucesso?, modo_falha). Se sucesso=True, retorna
    ConversionFileResult com SUCCESS. Se False, retorna erro ou exceção.
    """
    call_index = {"value": 0}

    def side_effect(source: Path, output_dir: Path, extract_images: bool, skip_if_exists: bool = False):
        idx = call_index["value"]
        call_index["value"] += 1

        succeeds, failure_mode = scenarios[idx]

        if succeeds:
            return ConversionFileResult(
                source=source,
                output=output_dir / source.with_suffix(".md").name,
                status=ConversionStatus.SUCCESS,
            )

        if failure_mode == "exception":
            raise RuntimeError(f"Erro simulado no arquivo {source.name}")

        # status_error: retorna resultado com status de falha
        return ConversionFileResult(
            source=source,
            output=None,
            status=ConversionStatus.FAILED_CORRUPTED,
            error_message=f"Falha simulada em {source.name}",
        )

    return side_effect


def _run_batch(scenarios: list[tuple[bool, str]]) -> ConversionResult:
    """Executa o ConversionManager com cenários mock e retorna o resultado final."""
    n = len(scenarios)
    files = [Path(f"/fake/dir/file_{i}.pdf") for i in range(n)]
    progress_queue = queue.Queue()
    manager = ConversionManager(progress_queue)

    with patch.object(manager._converter, "convert") as mock_convert:
        mock_convert.side_effect = _create_mock_side_effect(scenarios)
        thread = manager.start(files, Path("/output"), False)
        thread.join(timeout=30)

    # Extrai resultado final da fila
    final_result: ConversionResult | None = None
    while not progress_queue.empty():
        msg = progress_queue.get_nowait()
        if isinstance(msg, ProgressUpdate) and msg.is_complete:
            final_result = msg.result

    assert final_result is not None, "Resultado final não encontrado na fila"
    return final_result


# ─── Testes de propriedade ────────────────────────────────────────────────────


class TestPropertyBatchInvariant:
    """Property 3: Invariante de conversão em batch.

    **Validates: Requirements 3.5, 3.7, 5.3, 5.4**
    """

    @given(scenarios=_batch_scenario)
    @settings(max_examples=100, deadline=None)
    def test_succeeded_plus_failed_equals_total_equals_n(
        self, scenarios: list[tuple[bool, str]]
    ) -> None:
        """succeeded + failed == total == N para qualquer batch.

        Gera listas de N arquivos com mocks que podem suceder ou falhar,
        e verifica que a soma dos contadores é sempre consistente.
        """
        n = len(scenarios)
        result = _run_batch(scenarios)

        # Invariante principal: succeeded + failed == total == N
        assert result.total == n, (
            f"total ({result.total}) != N ({n})"
        )
        assert result.succeeded + result.failed == result.total, (
            f"succeeded ({result.succeeded}) + failed ({result.failed}) "
            f"!= total ({result.total})"
        )

    @given(scenarios=_batch_scenario)
    @settings(max_examples=100, deadline=None)
    def test_individual_failures_do_not_stop_batch(
        self, scenarios: list[tuple[bool, str]]
    ) -> None:
        """Falha individual não impede processamento dos demais.

        Verifica que todos os N arquivos são processados independentemente
        de falhas individuais, confirmando que o batch completa com
        total == N resultados individuais.
        """
        n = len(scenarios)
        result = _run_batch(scenarios)

        # Todos os N arquivos devem ter um resultado individual
        assert len(result.results) == n, (
            f"Número de resultados individuais ({len(result.results)}) != N ({n})"
        )

        # Conta sucessos e falhas nos resultados individuais
        individual_succeeded = sum(
            1 for r in result.results if r.status == ConversionStatus.SUCCESS
        )
        individual_failed = sum(
            1 for r in result.results if r.status != ConversionStatus.SUCCESS
        )

        # Deve bater com os contadores agregados
        assert individual_succeeded == result.succeeded, (
            f"Contagem individual de sucessos ({individual_succeeded}) "
            f"!= resultado.succeeded ({result.succeeded})"
        )
        assert individual_failed == result.failed, (
            f"Contagem individual de falhas ({individual_failed}) "
            f"!= resultado.failed ({result.failed})"
        )

    @given(outcomes=_file_outcomes)
    @settings(max_examples=100, deadline=None)
    def test_succeeded_count_matches_expected(
        self, outcomes: list[bool]
    ) -> None:
        """O número de succeeded bate com a quantidade de arquivos que tiveram sucesso.

        Verifica que o ConversionManager conta corretamente os sucessos
        com base no status retornado pelo converter.
        """
        scenarios = [(outcome, "status_error") for outcome in outcomes]
        expected_succeeded = sum(1 for o in outcomes if o)
        expected_failed = sum(1 for o in outcomes if not o)

        result = _run_batch(scenarios)

        assert result.succeeded == expected_succeeded, (
            f"succeeded ({result.succeeded}) != expected ({expected_succeeded})"
        )
        assert result.failed == expected_failed, (
            f"failed ({result.failed}) != expected ({expected_failed})"
        )
