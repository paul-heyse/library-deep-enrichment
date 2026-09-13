"""Source qualifiers, dynamic defaults, approved transfers, and finite witness counterexamples."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from attrs import evolve

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Argument, Operation, Passage, Policy
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.corpus.validation import validate_records
from library_deep_enrichment.semantics.contracts import (
    Assignment,
    Interpretation,
    Rule,
    Value,
    ValueKind,
)
from library_deep_enrichment.semantics.documents import literal, parameters, statements
from library_deep_enrichment.semantics.enrichment_contracts import (
    TransferMapping,
    TransferModel,
    TransferRule,
    WitnessObservation,
    WitnessRecipe,
)
from library_deep_enrichment.semantics.experiments import run_witness
from library_deep_enrichment.semantics.rules import consequence
from library_deep_enrichment.semantics.transfers import evaluate
from library_deep_enrichment.workflows.engine import overlay

if TYPE_CHECKING:
    from pathlib import Path


def _operation() -> Operation:
    return Operation(
        logical_id="operation:counter",
        profile="fixture",
        symbol="collections.Counter",
        package="python",
        version="fixture",
        language="python",
        kind="class",
        signature="(iterable)",
        parameters=(),
        returns="Counter",
        routes=("collections.Counter",),
        resolution="test",
        evidence=(),
    )


def _approval(record: object, kind: str, subject: str) -> Policy:
    return Policy(
        logical_id=f"approval:{kind}:{subject}",
        kind=kind,
        subject=subject,
        authority="test-model-reviewer",
        rationale=f"Finite counterexample test: {type(record).__name__}",
        allowed_predicates=(),
        required_scopes=(),
    )


def test_document_projection_keeps_later_qualifiers_and_rejects_rewritten_text(
    tmp_path: Path,
) -> None:
    """Authentic source support cannot justify dropping a later exception."""
    corpus = Corpus(tmp_path)
    builder = ObservationBuilder("test-source")
    operation = _operation()
    builder.add(operation)
    text = "Construct a result.\n\nParameters\n----------\nvalues : iterable\n    Input values.\n\nRaises\n------\nValueError\n    Only if the value is invalid.\n\n.. warning::\n    Metadata may not be retained."
    passage = Passage(
        logical_id="doc:counter",
        profile=operation.profile,
        owner=revision_of(operation),
        role="upstream",
        text=text,
        language="en",
        source=builder.own_bytes(text.encode(), media_type="text/plain"),
    )
    builder.add(passage)
    projected = tuple(statements(passage))
    assert all("not" in item.qualifiers and "if" in item.qualifiers for item in projected)
    assert any(item.role == "exception" for item in projected)
    writer = Coordinator(corpus, WriterIdentity(principal="test"))
    writer.commit((*builder.records.values(), *projected), expected="")
    with pytest.raises(CorpusError, match="projection changed"):
        writer.commit((evolve(projected[0], qualifiers=()),), expected=corpus.reader().manifest_id)


def test_symbolic_default_never_becomes_a_constant_and_literal_domain_is_finite() -> None:
    """No environment lookup or constructor call is executed while specializing modes."""
    assert literal("get_default()") is None
    assert literal("os.environ['MODE']") is None
    assert literal("None") == Value(kind=ValueKind.NULL, text="")
    operation = evolve(
        _operation(),
        parameters=(
            Argument(
                name="mode",
                kind="keyword_only",
                type_expression="Literal['safe', 'fast']",
                default_expression="get_default()",
                required=False,
            ),
        ),
    )
    mode = next(parameters(operation))
    assert mode.default_status == "symbolic"
    assert tuple(value.text for value in mode.domain) == ("safe", "fast")


def test_state_transfer_requires_mapping_approval_and_does_not_invent_missing_properties(
    tmp_path: Path,
) -> None:
    """Identical nominal output types do not automatically preserve metadata."""
    corpus = Corpus(tmp_path)
    operation = _operation()
    missing = Value(kind=ValueKind.TEXT, text="")
    model = TransferModel(
        logical_id="model:projection",
        name="projection",
        condition="",
        rules=(
            TransferRule(output="metadata", operator="copy", inputs=("metadata",), value=missing),
            TransferRule(output="rows", operator="copy", inputs=("rows",), value=missing),
        ),
        description="Model copies only explicitly selected state properties",
    )
    mapping = TransferMapping(
        logical_id="mapping:projection",
        profile="fixture",
        operation=revision_of(operation),
        model=revision_of(model),
        condition="",
        interpretation="modeled",
        scope="",
        support=(select(operation, "/signature", "fixture-model-association"),),
    )
    writer = Coordinator(corpus, WriterIdentity(principal="test-reviewer", role="policy"))
    writer.commit(
        (
            operation,
            model,
            mapping,
            _approval(model, "transfer-model-approval", revision_of(model)),
        ),
        expected="",
    )
    with pytest.raises(CorpusError, match="both model"):
        evaluate(corpus.reader(), mapping, ())
    writer.commit(
        (_approval(mapping, "transfer-mapping-approval", revision_of(mapping)),),
        expected=corpus.reader().manifest_id,
    )
    inputs = (
        Assignment(
            variable="metadata", value=Value(kind=ValueKind.TEXT, text="dataset=measurements")
        ),
    )
    result = evaluate(corpus.reader(), mapping, inputs)
    assert result.outputs == inputs
    assert any("rows: missing" in item for item in result.frontier)
    with pytest.raises(CorpusError, match="not entailed"):
        writer.commit((evolve(result, outputs=()),), expected=corpus.reader().manifest_id)


def test_real_isolated_witness_is_finite_and_cannot_rewrite_its_output(tmp_path: Path) -> None:
    """An actual standard-library computation has an independent expected count and scope."""
    corpus = Corpus(tmp_path)
    builder = ObservationBuilder("test-witness")
    operation = _operation()
    builder.add(operation)
    program = b'import json\nfrom collections import Counter\nprint(json.dumps({"environment": {}, "count": Counter("abca")["a"]}))\n'
    recipe = WitnessRecipe(
        logical_id="recipe:count",
        profile="fixture",
        name="count",
        language="python",
        program=builder.own_bytes(program, media_type="text/python"),
        manifest=builder.own_bytes(b"", media_type="text/plain"),
        packages=(),
        toolchain="test-python",
        description="Count a in abca with the standard library",
        fields=("/count",),
    )
    builder.add(recipe)
    writer = Coordinator(corpus, WriterIdentity(principal="test-reviewer", role="policy"))
    writer.commit(builder.records.values(), expected="")
    with pytest.raises(CorpusError, match="exact finite program"):
        run_witness(corpus, recipe, {"/count": revision_of(operation)})
    writer.commit(
        (_approval(recipe, "witness-recipe-approval", revision_of(recipe)),),
        expected=corpus.reader().manifest_id,
    )
    manifest = run_witness(corpus, recipe, {"/count": revision_of(operation)})
    assert run_witness(corpus, recipe, {"/count": revision_of(operation)}) == manifest
    observation = next(
        item
        for item in corpus.reader().records("witness_observations")
        if isinstance(item, WitnessObservation)
    )
    assert observation.value == Value(kind=ValueKind.INTEGER, text="2")
    altered = evolve(observation, value=Value(kind=ValueKind.INTEGER, text="3"))
    with pytest.raises(CorpusError, match="changed the retained result"):
        validate_records(overlay(corpus.reader(), (altered,)), (altered,))
    rule = Rule(
        logical_id="rule:count",
        algorithm="witness-field",
        source_family="witness_observations",
        selector="/field",
        pattern="^/count$",
        predicate="fixture-predicate",
        value=Value(kind=ValueKind.INTEGER, text="999"),
        condition="",
        quantifier="retained-inputs",
        domain="exact-execution-scope",
        phase="execution",
        interpretation=Interpretation.WITNESSED,
        description="Retain the observed count",
        version="1",
    )
    assertion = consequence(rule, observation, operation)
    assert assertion is not None
    assert assertion.scope == observation.scope
    assert assertion.value.text == "2"
    assert consequence(evolve(rule, quantifier="all-inputs"), observation, operation) is None
