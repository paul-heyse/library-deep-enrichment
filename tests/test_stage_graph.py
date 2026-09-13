"""The stage graph orders work and never silently reuses stale output."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from library_deep_enrichment.stages.graph import (
    CyclicStageGraphError,
    StageDefinition,
    StageGraph,
    UnknownStageError,
    stage_key,
)

if TYPE_CHECKING:
    from library_deep_enrichment.stages.graph import StageContext, StageResult


def _unused_runner(context: StageContext) -> StageResult:
    message = "stage graph tests never execute stage bodies"
    raise NotImplementedError(message)


def _definition(
    stage_id: str,
    inputs: tuple[str, ...] = (),
    outputs: tuple[str, ...] = (),
) -> StageDefinition:
    return StageDefinition(
        stage_id=stage_id,
        inputs=inputs,
        outputs=outputs,
        adapter_id=f"{stage_id}@1",
        schema_revision="v1",
        runner=_unused_runner,
    )


def _pipeline() -> StageGraph:
    return StageGraph(
        definitions=(
            _definition("render", ("api.jsonl", "docs.jsonl"), ("skill.md",)),
            _definition("acquire", (), ("sources.json",)),
            _definition("extract-api", ("sources.json",), ("api.jsonl",)),
            _definition("index-docs", ("sources.json",), ("docs.jsonl",)),
        )
    )


def test_producers_precede_consumers() -> None:
    """Every artifact is produced before the stage that reads it runs."""
    order = _pipeline().topological_order()
    assert order.index("acquire") < order.index("extract-api")
    assert order.index("extract-api") < order.index("render")
    assert order.index("index-docs") < order.index("render")


def test_an_unchanged_rebuild_runs_nothing() -> None:
    """Matching stage keys make a rebuild free."""
    graph = _pipeline()
    keys = {stage_id: f"key-{stage_id}" for stage_id in graph.topological_order()}
    plan = graph.plan(cached_keys=keys, current_keys=keys)
    assert plan.to_run == ()
    assert set(plan.reusable) == set(keys)


def test_a_changed_stage_invalidates_only_its_dependents() -> None:
    """Invalidation follows declared artifacts, not the whole graph."""
    graph = _pipeline()
    cached = {stage_id: f"key-{stage_id}" for stage_id in graph.topological_order()}
    current = dict(cached)
    current["extract-api"] = "changed"
    plan = graph.plan(cached_keys=cached, current_keys=current)
    assert plan.to_run == ("extract-api", "render")
    assert "index-docs" in plan.reusable
    assert "acquire" in plan.reusable


def test_a_dependency_cycle_is_rejected() -> None:
    """A cycle is a declaration error and fails loudly."""
    graph = StageGraph(
        definitions=(
            _definition("a", ("b.out",), ("a.out",)),
            _definition("b", ("a.out",), ("b.out",)),
        )
    )
    with pytest.raises(CyclicStageGraphError, match="cycle"):
        graph.topological_order()


def test_an_unproduced_input_is_rejected() -> None:
    """A stage cannot depend on an artifact nothing produces."""
    graph = StageGraph(definitions=(_definition("only", ("nobody-makes-this",), ()),))
    with pytest.raises(UnknownStageError, match="unproduced artifact"):
        graph.topological_order()


def test_the_stage_key_ignores_mapping_order() -> None:
    """Key computation is order-insensitive so it is reproducible."""
    definition = _definition("s")
    first = stage_key(
        definition,
        input_digests={"a": "1", "b": "2"},
        configuration={"z": 1, "a": 2},
        environment_facts={},
    )
    second = stage_key(
        definition,
        input_digests={"b": "2", "a": "1"},
        configuration={"a": 2, "z": 1},
        environment_facts={},
    )
    assert first == second


def test_the_stage_key_changes_with_the_adapter_identity() -> None:
    """Upgrading an extractor invalidates the work it produced."""
    baseline = _definition("s")
    upgraded = StageDefinition(
        stage_id="s",
        inputs=(),
        outputs=(),
        adapter_id="s@2",
        schema_revision="v1",
        runner=_unused_runner,
    )
    baseline_key = stage_key(
        baseline,
        input_digests={},
        configuration={},
        environment_facts={},
    )
    upgraded_key = stage_key(
        upgraded,
        input_digests={},
        configuration={},
        environment_facts={},
    )
    assert baseline_key != upgraded_key
