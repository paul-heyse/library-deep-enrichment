"""Wrong carriers and duplicated consumed values cannot become eligible by semantic similarity."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.semantics.applicability import inputs
from library_guides.semantics.contracts import Capability, Slot, State, Task
from library_guides.semantics.task_matching import compare, replay
from library_guides.semantics.task_matching_v1 import compare as historical_compare

from tests.test_semantic_intelligence import _operation, _setup, _task

if TYPE_CHECKING:
    from pathlib import Path


def _slot(
    *,
    type_expression: str = "Array[int64]",
    representation: str = "arrow-array",
    resource: str = "",
    consumes: bool = False,
) -> Slot:
    return Slot(
        role="value",
        type_expression=type_expression,
        representation=representation,
        resource=resource,
        consumes=consumes,
    )


def _contracts() -> tuple[Task, Capability]:
    task = Task(
        logical_id="task",
        goal="compute",
        profiles=("p",),
        requirements=(),
        context=(),
        inputs=(_slot(),),
        preferences=(),
        description="checked input",
    )
    cap = Capability(
        logical_id="cap",
        schema="compute",
        operation="op",
        mode="mode",
        inputs=(_slot(),),
        outputs=(),
        assertions=(),
        condition="",
        label="compute",
    )
    return task, cap


@pytest.mark.parametrize(
    ("slot", "expected"),
    [
        (_slot(), State.SUPPORTED),
        (_slot(representation="datafusion-expression"), State.REFUTED),
        (_slot(type_expression="Array[uint64]"), State.REFUTED),
        (_slot(type_expression="Any"), State.UNKNOWN),
        (_slot(representation="unknown"), State.UNKNOWN),
        (_slot(consumes=True), State.REFUTED),
        (_slot(resource="live-stream"), State.UNKNOWN),
    ],
)
def test_input_contract_dimensions(slot: Slot, expected: State) -> None:
    """Known incompatibility rejects; unresolved facts cannot satisfy a concrete input."""
    task, cap = _contracts()
    assert inputs(task, evolve(cap, inputs=(slot,))).state == expected


def test_multi_input_consumption_and_limit() -> None:
    """A single owned value cannot satisfy two consuming ports, even with matching types."""
    task, cap = _contracts()
    owned = _slot(consumes=True)
    task = evolve(task, inputs=(owned,))
    cap = evolve(cap, inputs=(owned, owned))
    assert inputs(task, cap).state == State.REFUTED
    assert inputs(evolve(task, inputs=(owned, owned)), cap).state == State.SUPPORTED
    assert inputs(evolve(task, inputs=(owned,) * 33), cap).state == State.UNKNOWN


def test_versioned_comparison_and_forgery(tmp_path: Path) -> None:
    """Old decisions replay under V1; a changed V2 candidate disposition fails admission."""
    corpus = Corpus(tmp_path)
    _setup(corpus)
    task = _task(corpus)
    old_scope, old = historical_compare(corpus.reader(), task)
    scope, current = compare(corpus.reader(), task)
    assert old.logical_id != current.logical_id
    assert replay(corpus.reader(), task, old) == old
    writer = Coordinator(corpus, WriterIdentity(principal="test"))
    writer.commit((task, old_scope, old, scope, current), expected=corpus.reader().manifest_id)
    corrupted = evolve(
        current,
        candidates=tuple(evolve(item, disposition="eligible") for item in current.candidates),
    )
    with pytest.raises(CorpusError, match="versioned task"):
        writer.commit((corrupted,), expected=corpus.reader().manifest_id)


def test_task_mutation_preserves_other_decisions_but_new_competitor_invalidates(
    tmp_path: Path,
) -> None:
    """Two consumers coexist, while a changed requirement or candidate still matters."""
    corpus = Corpus(tmp_path)
    _setup(corpus)
    writer = Coordinator(corpus, WriterIdentity(principal="test"))
    first = _task(corpus)
    universe, first_comparison = compare(corpus.reader(), first)
    writer.commit((first, universe, first_comparison), expected=corpus.reader().manifest_id)
    second = evolve(_task(corpus, "collected"), logical_id="task:second")
    universe, second_comparison = compare(corpus.reader(), second)
    writer.commit((second, universe, second_comparison), expected=corpus.reader().manifest_id)
    assert corpus.reader().get("comparisons", revision_of(first_comparison)) == first_comparison
    writer.commit(
        (evolve(first, description="changed consumer"),), expected=corpus.reader().manifest_id
    )
    assert corpus.reader().lookup("comparisons", first_comparison.logical_id, first.profile) is None
    assert corpus.reader().get("comparisons", revision_of(second_comparison)) == second_comparison
    writer.commit(
        (_operation("new-competitor", "BatchStream"),), expected=corpus.reader().manifest_id
    )
    assert not tuple(corpus.reader().records("comparisons"))
