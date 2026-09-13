"""Exact discovery denominators, isolation, and explicit resource-bound failures."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.contracts import Disposition, Job, Operation, Scope
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.discovery.contracts import Descriptor, DiscoveryScope, SearchSelection
from library_guides.discovery.scopes import current, units
from library_guides.discovery.search import search
from library_guides.discovery.validation import validate
from library_guides.workflows.discovery import (
    build_fca,
    build_graphs,
    build_labels,
    build_retrieval,
    stage_name,
)

if TYPE_CHECKING:
    from pathlib import Path


def _source(name: str) -> Operation:
    return Operation(
        logical_id=f"op:{name}",
        profile="context",
        symbol=name,
        package="sample",
        version="1",
        language="python",
        kind="function",
        signature="(value)",
        parameters=(),
        returns="Object",
        routes=(name,),
        resolution="declared",
        evidence=(),
    )


def _corpus(tmp_path: Path) -> Corpus:
    corpus = Corpus(tmp_path / "corpus")
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(
        (_source("decode"), _source("unrelated")), expected=""
    )
    return corpus


def _selection(name: str = "sample") -> DiscoveryScope:
    return DiscoveryScope(
        logical_id=name,
        profiles=("context",),
        packages=("sample",),
        artifacts=(),
        max_units=10,
    )


def test_scopes_keep_exact_populations_and_separate_output_ownership(tmp_path: Path) -> None:
    """Overlapping declarations do not merge profiles, packages, or scope-owned products."""
    corpus = _corpus(tmp_path)
    coordinator = Coordinator(corpus, WriterIdentity(principal="scope-control"))
    coordinator.commit(
        (
            evolve(_source("wrong_profile"), profile="elsewhere"),
            evolve(_source("wrong_package"), package="different"),
        ),
        expected=corpus.reader().manifest_id,
    )
    left = _selection()
    right = evolve(left, logical_id="overlap")
    coordinator.commit((left, right), expected=corpus.reader().manifest_id)
    build_retrieval(corpus)
    build_retrieval(corpus, left)
    build_retrieval(corpus, right)
    assert build_retrieval(corpus, left).reused
    reader = corpus.reader()
    assert len(tuple(units(reader))) == len(
        {"decode", "unrelated", "wrong_profile", "wrong_package"}
    )
    assert len(tuple(units(reader, left))) == len({"decode", "unrelated"})
    assert {unit.logical_id for unit in units(reader, left)}.isdisjoint(
        unit.logical_id for unit in units(reader, right)
    )
    result = search(reader, "decode", selection=SearchSelection(scope=left))
    assert result.eligible == len({"decode", "unrelated"})
    assert result.scope == revision_of(current(reader, left))
    build_graphs(corpus, left)
    build_graphs(corpus, right)
    graphs = tuple(corpus.reader().records("graph_nodes"))
    assert len(graphs) == len({"left", "right"}) * len({"structural", "semantic", "fused"}) * len(
        {"decode", "unrelated"}
    )
    retained = current(corpus.reader(), left)
    with pytest.raises(CorpusError, match="complete contextual selection"):
        validate(corpus.reader(), evolve(retained, members=retained.members[:1]))


def test_scope_population_change_withdraws_current_products_without_losing_history(
    tmp_path: Path,
) -> None:
    """An added candidate forces a rebuild even when the previous selected rows survive."""
    corpus = _corpus(tmp_path)
    selection = _selection()
    build_retrieval(corpus, selection)
    before = corpus.reader()
    Coordinator(corpus, WriterIdentity(principal="candidate-control")).commit(
        (_source("new_candidate"),), expected=before.manifest_id
    )
    with pytest.raises(CorpusError, match="build retrieval"):
        tuple(units(corpus.reader(), selection))
    assert len(tuple(units(before, selection))) == len({"decode", "unrelated"})
    build_retrieval(corpus, selection)
    assert len(tuple(units(corpus.reader(), selection))) == len(
        {"decode", "unrelated", "new_candidate"}
    )


def test_scope_bound_failure_is_durable_and_never_truncates_the_universe(tmp_path: Path) -> None:
    """A selection exceeding its explicit budget cannot publish a favorable prefix."""
    corpus = _corpus(tmp_path)
    selection = evolve(_selection(), max_units=1)
    with pytest.raises(BudgetExceededError, match="unit bound"):
        build_retrieval(corpus, selection)
    reader = corpus.reader()
    job = reader.lookup("jobs", stage_name("retrieval-units.v1", selection))
    assert isinstance(job, Job)
    assert job.disposition == Disposition.FAILED
    assert not tuple(reader.records("retrieval_units"))
    assert not any(isinstance(record, Scope) for record in reader.records("scopes"))


def test_scoped_fca_labels_and_other_profile_addition(tmp_path: Path) -> None:
    """Overlapping analyses own distinct outputs; irrelevant profile growth preserves reuse."""
    corpus = _corpus(tmp_path)
    left = _selection("left")
    right = _selection("right")
    for scope in (left, right):
        build_retrieval(corpus, scope)
        build_graphs(corpus, scope)
        build_fca(corpus, scope)
        build_labels(corpus, scope)
    before = corpus.reader()
    descriptors = tuple(before.records("descriptors"))
    assert descriptors
    for descriptor in descriptors:
        assert isinstance(descriptor, Descriptor)
        assert descriptor.support
    assert build_fca(corpus, left).reused
    assert build_labels(corpus, left).reused
    Coordinator(corpus, WriterIdentity(principal="other-context")).commit(
        (evolve(_source("outside"), profile="outside"),), expected=before.manifest_id
    )
    assert build_retrieval(corpus, left).reused
    assert build_fca(corpus, left).reused
    assert build_labels(corpus, left).reused
    assert tuple(corpus.reader().records("descriptors")) == descriptors
