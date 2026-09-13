"""Semantic counterexamples and a real corpus-to-decision-to-portable-release chain."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

import pytest
from attrs import evolve
from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import ByteRange, Disposition, Job, Operation, Passage, Release
from library_guides.corpus.encoding import bytes_digest
from library_guides.corpus.evidence import stage_blob
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.publication.export import export_view, import_view
from library_guides.publication.releases import publish, read_guide
from library_guides.semantics.conditions import check_condition
from library_guides.semantics.contracts import (
    Assertion,
    Assignment,
    Expression,
    Interpretation,
    Predicate,
    Requirement,
    Rule,
    State,
    Task,
)
from library_guides.semantics.proofs import check_consequence
from library_guides.semantics.realization import realize
from library_guides.semantics.rules import consequence, derive
from library_guides.semantics.task_matching import compare
from library_guides.semantics.vocabulary import approve_rules, foundation, text_value
from library_guides.workflows.semantics import STAGE, build

if TYPE_CHECKING:
    from pathlib import Path


def _operation(name: str, returns: str) -> Operation:
    return Operation(
        logical_id=f"operation:{name}",
        profile="sample-1",
        symbol=f"sample.{name}",
        package="sample",
        version="1",
        language="python",
        kind="method",
        signature=f"def {name}(self) -> {returns}:",
        parameters=(),
        returns=returns,
        routes=(f"sample.{name}",),
        resolution="resolved",
        evidence=(),
    )


def _setup(corpus: Corpus) -> None:
    records = list(foundation())
    for name, returns, documentation in (
        ("collect", "list[Batch]", "Execute this query and collect results into memory."),
        (
            "stream",
            "BatchStream",
            "Executes this query and returns a stream over a single partition.",
        ),
        (
            "near_neighbor",
            "BatchStream",
            "Returns a stream unless the backend requires materialization.",
        ),
    ):
        operation = _operation(name, returns)
        data = documentation.encode()
        blob, chunks = stage_blob(io.BytesIO(data), media_type="text/plain")
        records.extend(
            [
                *chunks,
                blob,
                operation,
                Passage(
                    logical_id=f"passage:{name}",
                    profile=operation.profile,
                    owner=revision_of(operation),
                    role="upstream-documentation",
                    text=documentation,
                    language="en",
                    source=ByteRange(
                        blob=revision_of(blob), start=0, end=len(data), digest=bytes_digest(data)
                    ),
                ),
            ]
        )
    approvals = approve_rules(
        tuple(records),
        authority="test-rule-reviewer",
        rationale="Narrow controlled source grammar with adversarial fixtures",
    )
    Coordinator(corpus, WriterIdentity(principal="test-rule-reviewer", role="policy")).commit(
        [*records, *approvals],
        expected="",
    )
    writer = Coordinator(corpus, WriterIdentity(principal="rule-worker"))
    pairs = list(derive(corpus.reader()))
    writer.commit([item for pair in pairs for item in pair], expected=corpus.reader().manifest_id)
    receipts = [check_consequence(corpus.reader(), proof) for _, proof in pairs]
    writer.commit(receipts, expected=corpus.reader().manifest_id)
    writer.commit(realize(corpus.reader()), expected=corpus.reader().manifest_id)


def _task(corpus: Corpus, delivery: str = "incremental") -> Task:
    predicate = next(
        item
        for item in corpus.reader().records("predicates")
        if isinstance(item, Predicate) and item.name == "documented_result_delivery"
    )
    return Task(
        logical_id="task:consume",
        profile="sample-1",
        profiles=("sample-1",),
        goal="consume-results",
        requirements=(
            Requirement(
                predicate=revision_of(predicate),
                value=text_value(delivery),
                operator="equal",
                interpretations=(Interpretation.UPSTREAM_CONTRACT,),
                mandatory=True,
            ),
        ),
        context=(),
        inputs=(),
        preferences=(),
        description="Choose the documented result delivery contract",
    )


def test_generated_choice_reverse_and_portable_release(tmp_path: Path) -> None:
    """Reusable rules choose a stream, reject collection, and retain a qualified neighbor gap."""
    corpus = Corpus(tmp_path / "fabric")
    _setup(corpus)
    task = _task(corpus)
    universe, comparison = compare(corpus.reader(), task)
    statuses = {
        str(corpus.reader().row("operations", item.operation)["symbol"]): item.disposition
        for item in comparison.candidates
    }
    assert statuses == {
        "sample.collect": "rejected",
        "sample.stream": "eligible",
        "sample.near_neighbor": "conditional",
    }
    assert len(universe.members) == len(statuses)
    _, reversed_choice = compare(corpus.reader(), _task(corpus, "collected"))
    assert (
        next(
            item
            for item in reversed_choice.candidates
            if corpus.reader().row("operations", item.operation)["symbol"] == "sample.collect"
        ).disposition
        == "eligible"
    )
    writer = Coordinator(corpus, WriterIdentity(principal="task-compiler"))
    writer.commit([task, universe, comparison], expected=corpus.reader().manifest_id)
    release_id = publish(corpus, comparison, expected="")
    destination = tmp_path / "portable"
    export_view(corpus.reader("release"), destination)
    restored = Corpus(tmp_path / "clean")
    assert import_view(restored, destination) == release_id
    release = next(
        item for item in restored.reader("release").records("releases") if isinstance(item, Release)
    )
    guide = read_guide(restored.reader("release"), release)
    assert "sample.stream" in guide
    assert "unknown" in guide
    assert "total operator memory" not in guide  # No unsupported memory claim is synthesized.


def test_portable_successor_withdraws_changed_premise_without_jobs(tmp_path: Path) -> None:
    """A changed source retires its proof closure while unrelated evidence survives."""
    corpus = Corpus(tmp_path / "source")
    _setup(corpus)
    task = _task(corpus)
    universe, comparison = compare(corpus.reader(), task)
    Coordinator(corpus, WriterIdentity(principal="fixture")).commit(
        (task, universe, comparison), expected=corpus.reader().manifest_id
    )
    publish(corpus, comparison, expected="")
    export_view(corpus.reader("release"), tmp_path / "export")
    restored = Corpus(tmp_path / "restored")
    import_view(restored, tmp_path / "export", head="analysis")
    before = restored.reader()
    assert not tuple(before.records("jobs"))
    source = before.lookup("passages", "passage:stream", "sample-1")
    assert isinstance(source, Passage)
    unaffected = {
        revision_of(item)
        for item in before.records("assertions")
        if isinstance(item, Assertion) and item.subject != source.owner
    }
    assert unaffected
    data = b"Returns a stream unless the backend requires materialization."
    blob, chunks = stage_blob(io.BytesIO(data), media_type="text/plain")
    replacement = evolve(
        source,
        text=data.decode(),
        source=ByteRange(blob=revision_of(blob), start=0, end=len(data), digest=bytes_digest(data)),
    )
    Coordinator(restored, WriterIdentity(principal="source-updater")).commit(
        (*chunks, blob, replacement), expected=before.manifest_id
    )
    after = restored.reader()
    assert not tuple(after.records("comparisons"))
    assert not tuple(after.records("releases"))
    assert unaffected <= {revision_of(item) for item in after.records("assertions")}
    assert before.get("comparisons", revision_of(comparison)) == comparison
    _, changed = compare(after, task)
    assert not any(item.disposition == "eligible" for item in changed.candidates)


def test_counterfactuals_recompute_actual_eligibility_and_reject_forged_delta(
    tmp_path: Path,
) -> None:
    """Changing delivery has a checked comparison delta, not a prose reversal trigger."""
    from library_guides.semantics.comparison import counterfactuals
    from library_guides.semantics.decision_contracts import Counterfactual
    from library_guides.semantics.decision_validation import validate

    corpus = Corpus(tmp_path / "fabric")
    _setup(corpus)
    records = tuple(counterfactuals(corpus.reader(), _task(corpus)))
    Coordinator(corpus, WriterIdentity(principal="task-compiler")).commit(
        records, expected=corpus.reader().manifest_id
    )
    delta = next(item for item in records if isinstance(item, Counterfactual))
    assert {
        corpus.reader().row("operations", item)["symbol"] for item in delta.became_eligible
    } == {"sample.collect"}
    assert {
        corpus.reader().row("operations", item)["symbol"] for item in delta.ceased_eligible
    } == {"sample.stream"}
    with pytest.raises(CorpusError, match="recomputed"):
        validate(corpus.reader(), evolve(delta, became_eligible=()))
    comparison = corpus.reader().get("comparisons", delta.baseline)
    from library_guides.semantics.contracts import Comparison

    assert isinstance(comparison, Comparison)
    manifest = publish(corpus, comparison, expected="")
    destination = tmp_path / "counterfactual-release"
    export_view(corpus.reader("release"), destination)
    restored = Corpus(tmp_path / "restored-counterfactual")
    assert import_view(restored, destination) == manifest
    assert restored.reader("release").get("counterfactuals", revision_of(delta)) == delta
    release = next(
        item for item in restored.reader("release").records("releases") if isinstance(item, Release)
    )
    assert "Computed requirement changes" in read_guide(restored.reader("release"), release)


def test_preferences_do_not_assign_favorable_cost_to_unknown_candidates(tmp_path: Path) -> None:
    """An explicit preference can select known values but must retain unknown tradeoffs."""
    from library_guides.semantics.comparison import choose
    from library_guides.semantics.decision_contracts import Objective, PreferencePolicy
    from library_guides.semantics.realization import qualified_assertions

    corpus = Corpus(tmp_path / "fabric")
    _setup(corpus)
    task = _task(corpus)
    policy = PreferencePolicy(
        logical_id="consumer:prefer-collected",
        strategy="lexicographic",
        objectives=(
            Objective(
                predicate=task.requirements[0].predicate,
                direction="ordered",
                order=(text_value("collected"), text_value("incremental")),
                interpretations=(Interpretation.UPSTREAM_CONTRACT,),
            ),
        ),
        rationale="Explicit fixture consumer preference, not a performance claim",
    )
    Coordinator(corpus, WriterIdentity(principal="consumer")).commit(
        (policy,), expected=corpus.reader().manifest_id
    )
    task = evolve(task, preferences=(revision_of(policy),), requirements=())
    universe, comparison = compare(corpus.reader(), task)
    assert {corpus.reader().row("operations", item)["symbol"] for item in comparison.preferred} == {
        "sample.collect"
    }
    supported = qualified_assertions(corpus.reader())
    missing = {
        candidate.operation: tuple(
            item for item in supported if item.subject == candidate.operation
        )
        for candidate in comparison.candidates
        if corpus.reader().row("operations", candidate.operation)["symbol"] != "sample.stream"
    }
    frontier, gaps = choose(corpus.reader(), task, comparison.candidates, missing)
    assert {corpus.reader().row("operations", item)["symbol"] for item in frontier} == {
        "sample.collect",
        "sample.stream",
    }
    assert "lack comparable objective support" in gaps[0]
    Coordinator(corpus, WriterIdentity(principal="consumer")).commit(
        (task, universe, comparison), expected=corpus.reader().manifest_id
    )
    _preference_release(corpus, tmp_path)


def _preference_release(corpus: Corpus, tmp_path: Path) -> None:
    from library_guides.publication.objectives import evidence
    from library_guides.semantics.contracts import Comparison

    comparison = next(
        item for item in corpus.reader().records("comparisons") if isinstance(item, Comparison)
    )
    objective_support = {revision_of(item) for item in evidence(corpus.reader(), comparison)}
    assert objective_support
    manifest = publish(corpus, comparison, expected="")
    export_view(corpus.reader("release"), tmp_path / "preferred-release")
    restored = Corpus(tmp_path / "restored-preferences")
    assert import_view(restored, tmp_path / "preferred-release") == manifest
    reader = restored.reader("release")
    assert objective_support <= {revision_of(item) for item in reader.records("assertions")}
    task = reader.get("tasks", comparison.task)
    assert isinstance(task, Task)
    assert compare(reader, task)[1] == comparison
    release = next(item for item in reader.records("releases") if isinstance(item, Release))
    assert "Consumer preferences" in read_guide(reader, release)


def test_forged_consequence_cannot_reuse_valid_citations(tmp_path: Path) -> None:
    """Changing a predicate value while retaining real citations defeats qualification."""
    corpus = Corpus(tmp_path / "fabric")
    _setup(corpus)
    assertion, proof = next(derive(corpus.reader()))
    changed = evolve(
        assertion, logical_id="forged-assertion", value=text_value("unbounded-memory-guarantee")
    )
    forged = evolve(proof, logical_id="forged-proof", conclusion=revision_of(changed))
    Coordinator(corpus, WriterIdentity(principal="adversarial-producer")).commit(
        [changed, forged],
        expected=corpus.reader().manifest_id,
    )
    with pytest.raises(CorpusError, match="not entailed"):
        check_consequence(corpus.reader(), forged)


@pytest.mark.parametrize("qualifier", ["not", "never", "may", "might", "unless", "if", "except"])
def test_document_qualifiers_are_not_discarded(tmp_path: Path, qualifier: str) -> None:
    """A positive phrase cannot erase a modality, negation, or exception."""
    Corpus(tmp_path / "fabric")
    rule = next(
        item
        for item in foundation()
        if isinstance(item, Rule) and item.logical_id == "rule:stream-document"
    )
    operation = _operation("stream", "BatchStream")
    text = f"Returns a stream {qualifier} backend semantics change."
    source = Passage(
        logical_id="qualified-document",
        profile=operation.profile,
        owner=revision_of(operation),
        role="upstream-documentation",
        text=text,
        language="en",
        source=ByteRange(blob="fixture", start=0, end=1, digest="fixture"),
    )
    assert consequence(rule, source, operation) is None


def test_solver_does_not_assign_unknown_context_in_our_favor(tmp_path: Path) -> None:
    """Satisfiability leaves an unobserved parameter unknown; known values can settle it."""
    Corpus(tmp_path / "fabric")
    expression = Expression(
        logical_id="requires-stream",
        operator="equal",
        arguments=(),
        variable="consumer",
        value=text_value("stream"),
    )
    revision = revision_of(expression)
    catalog = {revision: expression}
    assert check_condition(revision, catalog, ()).state == State.UNKNOWN
    assert (
        check_condition(
            revision, catalog, (Assignment(variable="consumer", value=text_value("stream")),)
        ).state
        == State.SUPPORTED
    )

    assert (
        check_condition(
            revision, catalog, (Assignment(variable="consumer", value=text_value("list")),)
        ).state
        == State.REFUTED
    )


def test_failed_semantic_build_retires_its_old_current_outputs(tmp_path: Path) -> None:
    """An actual analysis failure becomes the latest job and cannot serve old success."""
    corpus = Corpus(tmp_path / "fabric")
    _setup(corpus)
    first = build(corpus)
    assert not first.reused
    assert build(corpus).reused
    rule = next(
        item
        for item in corpus.reader().records("rules")
        if isinstance(item, Rule) and item.source_family == "operations"
    )
    Coordinator(corpus, WriterIdentity(principal="new-model-candidate")).commit(
        [evolve(rule, algorithm="unsupported-model")],
        expected=corpus.reader().manifest_id,
    )
    with pytest.raises(CorpusError, match="unsupported"):
        build(corpus)
    job = corpus.reader().lookup("jobs", STAGE)
    assert isinstance(job, Job)
    assert job.disposition == Disposition.FAILED
    assert not tuple(corpus.reader().records("capabilities"))


def test_later_paragraph_exception_prevents_unconditional_delivery(tmp_path: Path) -> None:
    """A summary cannot hide an exception in a later retained documentation paragraph."""
    Corpus(tmp_path / "fabric")
    operation = _operation("conditional_stream", "BatchStream")
    rule = next(
        item
        for item in foundation()
        if isinstance(item, Rule) and item.logical_id == "rule:stream-document"
    )
    data = b"Returns a stream.\n\nExcept when the backend collects the result first."
    passage = Passage(
        logical_id="exception-after-summary",
        profile=operation.profile,
        owner=revision_of(operation),
        role="upstream-documentation",
        text=data.decode(),
        language="en",
        source=ByteRange(
            blob="not-needed-for-pure-rule-test", start=0, end=len(data), digest=bytes_digest(data)
        ),
    )
    assert consequence(rule, passage, operation) is None


def test_integer_range_and_unconditional_context_conflict(tmp_path: Path) -> None:
    """Range entailment uses observed integers, while inconsistent context never becomes favorable."""
    from library_guides.semantics.contracts import Value, ValueKind

    Corpus(tmp_path / "fabric")
    zero = Value(kind=ValueKind.INTEGER, text="0")
    node = Expression(
        logical_id="nonnegative",
        operator="greater_equal",
        arguments=(),
        variable="index",
        value=zero,
    )
    revision = revision_of(node)
    expressions = {revision: node}
    assert check_condition(revision, expressions, ()).state == State.UNKNOWN
    assert (
        check_condition(revision, expressions, (Assignment(variable="index", value=zero),)).state
        == State.SUPPORTED
    )
    negative = Value(kind=ValueKind.INTEGER, text="-1")
    assert (
        check_condition(
            revision, expressions, (Assignment(variable="index", value=negative),)
        ).state
        == State.REFUTED
    )
    contradictory = (
        Assignment(variable="index", value=zero),
        Assignment(variable="index", value=negative),
    )
    assert check_condition("", expressions, contradictory).state == State.CONFLICTING
