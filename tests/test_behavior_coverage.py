"""Finite owner accounting through exhaustion, retry, replay and portable restoration."""

from pathlib import Path

import pytest
from attrs import evolve
from library_guides.analyses.behavior.contracts import BehaviorRequest, BehaviorSummary, Limits
from library_guides.analyses.behavior.coverage import BehaviorCoverage, State, analyze
from library_guides.analyses.behavior.service import validate
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.native_contracts import NativeFact
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.facts.contracts import FactArtifact
from library_guides.native_admission import NativeInputs, admit_artifacts
from library_guides.publication.export import export_view, import_view
from library_guides.workflows.behavior import build

from tests import test_behavior_python as python_controls
from tests.test_behavior_engine import builder

source_case = python_controls.source_case


def test_one_exhausted_owner_remains_counted_without_erasing_completed_peer(
    source_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """A finite successful stage can report incomplete interpretation without an empty summary."""
    root, artifact = source_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    names = {"final_override", "identity_condition"}
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.kind == "definition" and item.symbol in names
    )
    assert len(owners) == len(names)
    request = BehaviorRequest(
        logical_id="budget-control",
        profile=artifact.profile,
        owners=tuple(sorted(map(revision_of, owners))),
        artifacts=(owners[0].artifact,),
        limits=Limits(clauses=1),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    reader = corpus.reader()
    coverage = tuple(reader.records("behavior_coverage"))
    summaries = tuple(reader.records("behavior_summaries"))
    assert len(coverage) == len(owners)
    assert len(summaries) == 1
    by_owner = {item.owner: item for item in coverage if isinstance(item, BehaviorCoverage)}
    failed = by_owner[
        next(revision_of(owner) for owner in owners if owner.symbol == "identity_condition")
    ]
    assert failed.state == State.EXHAUSTED
    assert failed.phase == "interpretation"
    assert not failed.summary
    assert failed.metrics
    assert "clause budget" in failed.detail
    with pytest.raises(CorpusError, match="retained-source replay"):
        validate(reader, (evolve(failed, state=State.SUMMARIZED),))
    exported = export_view(reader, tmp_path / "portable")
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, tmp_path / "portable") == exported.manifest
    assert tuple(restored.reader("release").records("behavior_coverage")) == coverage
    larger = evolve(request, limits=Limits())
    assert not build(corpus, larger).reused
    current = tuple(corpus.reader().records("behavior_coverage"))
    assert len(current) == len(owners)
    assert all(
        isinstance(item, BehaviorCoverage) and item.state == State.SUMMARIZED for item in current
    )
    assert len(tuple(corpus.reader().records("behavior_summaries"))) == len(owners)


def test_shared_fixedpoint_exhaustion_does_not_invent_per_owner_work_counts() -> None:
    """A failed shared solution affects its whole selected population and yields no summary."""
    bodies = []
    for name in ("first", "second"):
        graph = builder(name)
        graph.emit("return", value=graph.term("literal", value="1", ty="python:int"))
        bodies.append(graph.finish(()))
    records = analyze(tuple(bodies), {}, Limits(steps=1))
    assert len(records) == len(bodies)
    assert not any(isinstance(item, BehaviorSummary) for item in records)
    assert all(
        isinstance(item, BehaviorCoverage)
        and item.state == State.EXHAUSTED
        and item.phase == "shared_fixedpoint"
        and not item.metrics
        and not item.summary
        for item in records
    )
