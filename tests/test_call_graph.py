"""Real compiler-catalog helper selection, context controls and portable ownership."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from attrs import evolve
from library_guides.analyses.behavior.contracts import BehaviorRequest, BehaviorSummary, Limits
from library_guides.analyses.call_graph.contracts import (
    CallClosure,
    CallClosureRequest,
    CallIndex,
    CallIndexRequest,
)
from library_guides.analyses.call_graph.service import validate
from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.facts.contracts import Budget, FactArtifact
from library_guides.native_admission import NativeInputs, admit_artifacts
from library_guides.publication.export import export_view, import_view
from library_guides.source_pipeline import SourceJob, extract
from library_guides.workflows.behavior import build as build_behavior
from library_guides.workflows.call_graph import build

from tests import test_behavior_mir as native_controls

native_cases = native_controls.native_cases


def _index(corpus: Corpus, request: CallIndexRequest) -> CallIndex:
    build(corpus, request)
    values = [
        item
        for item in corpus.reader().records("call_indexes")
        if isinstance(item, CallIndex) and item.request == revision_of(request)
    ]
    assert len(values) == 1
    return values[0]


def _selection(corpus: Corpus, request: CallClosureRequest) -> tuple[CallClosure, BehaviorRequest]:
    build(corpus, request)
    values = [
        item
        for item in corpus.reader().records("call_closures")
        if isinstance(item, CallClosure) and item.request == revision_of(request)
    ]
    assert len(values) == 1
    result = values[0]
    behavior = corpus.reader().get("behavior_requests", result.behavior)
    assert isinstance(behavior, BehaviorRequest)
    return result, behavior


def test_complete_call_index_selects_helpers_and_replays_portably(
    native_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """A public-only root gains its actual cross-unit helper without selecting it by name."""
    root, artifacts = native_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts[:2]))
    reader = corpus.reader()
    native = tuple(reader.records("native_artifacts"))
    index_request = CallIndexRequest(
        logical_id="complete-captured-calls",
        profile="behavior-native",
        artifacts=tuple(sorted(map(revision_of, native))),
    )
    index = _index(corpus, index_request)
    assert len(index.owners) == sum(
        item.record_count for item in native if isinstance(item, NativeArtifact)
    )
    assert any(
        arg.kind == "constant" and arg.scalar == "3"
        for owner in index.owners
        for call in owner.calls
        for arg in call.substitutions
    )
    root_fact = next(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact) and item.symbol.endswith("::wrapper")
    )
    request = CallClosureRequest(
        logical_id="public-root",
        profile="behavior-native",
        index=revision_of(index),
        roots=(revision_of(root_fact),),
    )
    result, behavior = _selection(corpus, request)
    assert len(result.helpers) == 1
    assert all(call.state == "selected_generic_definition" for call in result.calls)
    assert set(behavior.owners) == {*result.roots, *result.helpers}
    assert len(behavior.artifacts) == len(artifacts[:2])
    build_behavior(corpus, behavior)
    summaries = [
        item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary) and item.request == revision_of(behavior)
    ]
    assert len(summaries) == len(behavior.owners)
    assert all(clause.guards for item in summaries for clause in item.clauses)
    assert all(
        {item.terms[clause.result].op for clause in item.clauses} == {"literal", "field"}
        for item in summaries
    )
    with patch(
        "library_guides.workflows.remote.RemoteProducer.__call__", side_effect=AssertionError
    ):
        assert build(corpus, index_request).reused
        assert build(corpus, request).reused
    with pytest.raises(CorpusError, match="complete catalog replay"):
        validate(corpus.reader(), (evolve(index, owners=index.owners[:-1]),))
    with pytest.raises(CorpusError, match="contextual replay"):
        validate(corpus.reader(), (evolve(result, helpers=()),))
    with pytest.raises(BudgetExceededError, match="read budget"):
        build(corpus, evolve(index_request, logical_id="tiny-catalog", max_facts=1))
    archive = tmp_path / "portable"
    export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, archive, head="analysis")
    assert restored.reader().get("call_indexes", revision_of(index)) == index
    assert restored.reader().get("call_closures", revision_of(result)) == result
    validate(restored.reader(), (index, result))
    assert build(restored, request).reused


def test_helper_budgets_and_catalog_changes_withdraw_generated_requests(
    native_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """Missing/wrong-build helpers stay open; adding a matching body withdraws stale outputs."""
    root, artifacts = native_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts))
    root_fact = next(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.symbol.endswith("::wrapper")
    )
    all_artifacts = tuple(
        item
        for item in corpus.reader().records("native_artifacts")
        if isinstance(item, NativeArtifact)
    )
    dependency = [item for item in all_artifacts if revision_of(item) != root_fact.artifact]
    # Identify matching versus changed build by original artifact acquisition order, not names.
    wrong = next(item for item in dependency if item.external_id != artifacts[0].id)
    request = CallIndexRequest(
        logical_id="changing-catalog",
        profile="behavior-native",
        artifacts=tuple(sorted((root_fact.artifact, revision_of(wrong)))),
    )
    index = _index(corpus, request)
    selection = CallClosureRequest(
        logical_id="contextual-root",
        profile="behavior-native",
        index=revision_of(index),
        roots=(revision_of(root_fact),),
    )
    result, behavior = _selection(corpus, selection)
    assert not result.helpers
    assert {call.state for call in result.calls} == {"body_absent_from_finite_catalog"}
    build_behavior(corpus, behavior)
    index = _index(
        corpus, evolve(request, artifacts=tuple(sorted(map(revision_of, all_artifacts))))
    )
    assert not tuple(corpus.reader().records("call_closures"))
    assert not tuple(corpus.reader().records("behavior_requests"))
    assert not tuple(corpus.reader().records("behavior_summaries"))
    selection = evolve(selection, index=revision_of(index))
    resolved, _ = _selection(corpus, selection)
    assert len(resolved.helpers) == 1
    _assert_selection_budgets(corpus, selection)


def _assert_selection_budgets(corpus: Corpus, selection: CallClosureRequest) -> None:
    depth, _ = _selection(corpus, evolve(selection, logical_id="depth-zero", max_depth=0))
    assert not depth.helpers
    assert {call.state for call in depth.calls} == {"depth_budget_exhausted"}
    count, _ = _selection(
        corpus, evolve(selection, logical_id="owner-one", limits=Limits(owners=1))
    )
    assert not count.helpers
    assert {call.state for call in count.calls} == {"owner_budget_exhausted"}


def test_duplicate_captured_bodies_prevent_unqualified_choice(
    native_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """A second capture remains a candidate; graph traversal cannot arbitrarily pick one."""
    from tests.test_native_lanes import SCHEMAS, _binary

    root, artifacts = native_cases
    repeated = extract(
        root,
        SourceJob(
            id="repeated-compiler-capture",
            kind="mir_execution",
            input=str(root / artifacts[0].input_path),
            helper=str(_binary("mir-facts")),
            profile="behavior-native",
            schema=str(SCHEMAS / "mir-execution.v1.schema.json"),
            witnesses=tuple(
                evolve(item, path=str(root / item.path)) for item in artifacts[0].witnesses
            ),
        ),
        Budget(),
    )
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(*artifacts[:2], repeated)))
    index = _index(
        corpus,
        CallIndexRequest(
            logical_id="duplicate-captures",
            profile="behavior-native",
            artifacts=tuple(sorted(map(revision_of, corpus.reader().records("native_artifacts")))),
        ),
    )
    owner = next(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact) and item.symbol.endswith("::wrapper")
    )
    result, _ = _selection(
        corpus,
        CallClosureRequest(
            logical_id="ambiguous-root",
            profile="behavior-native",
            index=revision_of(index),
            roots=(revision_of(owner),),
        ),
    )
    assert not result.helpers
    assert {call.state for call in result.calls} == {"ambiguous_contextual_bodies"}
    assert all(len(call.candidates) == len(artifacts[:2]) for call in result.calls)
