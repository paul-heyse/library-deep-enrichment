"""Finite hypergraph controls with declared fixture interfaces and qualified contract facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Argument, Operation, Passage, TypeUse
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.semantics.contracts import (
    Capability,
    Interpretation,
    Predicate,
    Requirement,
    Slot,
    Task,
)
from library_deep_enrichment.semantics.planning import compose
from library_deep_enrichment.semantics.vocabulary import approve_rules, foundation, text_value
from library_deep_enrichment.workflows.semantics import build

if TYPE_CHECKING:
    from pathlib import Path

    from library_deep_enrichment.semantics.contracts import Composition
    from library_deep_enrichment.semantics.enrichment_contracts import CompositionEvaluation


def _slot(name: str, kind: str) -> Slot:
    return Slot(
        role=name,
        type_expression=kind,
        representation="fixture-object",
        resource="",
        consumes=False,
    )


def _interface(
    builder: ObservationBuilder,
    name: str,
    inputs: tuple[tuple[str, str], ...],
    output: str,
    text: str,
) -> None:
    signature = f"({', '.join(f'{name}: {kind}' for name, kind in inputs)}) -> {output}"
    raw = builder.observe(
        f"source:{name}",
        {
            "signature": signature,
            "resolved_symbol": output,
            "role": "output",
            "position": 0,
            "direct": True,
            "selector": "/returns",
        },
        profile="fixture",
        kind="fixture-declaration",
    )
    operation = Operation(
        logical_id=f"operation:{name}",
        profile="fixture",
        symbol=name,
        package="fixture",
        version="1",
        language="python",
        kind="function",
        signature=signature,
        parameters=tuple(
            Argument(
                name=key,
                kind="positional",
                type_expression=kind,
                default_expression="",
                required=True,
            )
            for key, kind in inputs
        ),
        returns=output,
        routes=(name,),
        resolution="declared",
        evidence=(builder.select(raw, "/signature", "original-declaration"),),
    )
    owner = builder.add(operation)
    builder.add(
        TypeUse(
            logical_id=f"nominal:{name}",
            profile="fixture",
            owner=owner,
            nominal=output,
            nominal_scope="fixture-module",
            role="output",
            position=0,
            direct=True,
            selector="/returns",
            resolution="exact",
            evidence=tuple(
                builder.select(raw, f"/{field}", "nominal-declaration")
                for field in ("resolved_symbol", "role", "position", "direct", "selector")
            ),
        )
    )
    builder.add(
        Passage(
            logical_id=f"document:{name}",
            profile="fixture",
            owner=owner,
            role="upstream-summary",
            text=text,
            language="en",
            source=builder.own_bytes(text.encode(), media_type="text/plain"),
        )
    )


def _fixture(tmp_path: Path) -> Corpus:
    corpus = Corpus(tmp_path / "fabric")
    builder = ObservationBuilder("declared-fixture.v1")
    _interface(
        builder, "prepare", (("seed", "Seed"),), "Part", "Creates a new intermediate object."
    )
    _interface(
        builder,
        "incremental",
        (("part", "Part"), ("seal", "Seal")),
        "Finished",
        "Creates a new object and returns a stream.",
    )
    _interface(
        builder,
        "collected",
        (("part", "Part"), ("seal", "Seal")),
        "Finished",
        "Creates a new object and collects results into memory.",
    )
    models = foundation()
    Coordinator(corpus, WriterIdentity(principal="fixture-model-review", role="policy")).commit(
        (
            *builder.records.values(),
            *models,
            *approve_rules(
                models,
                authority="fixture-review",
                rationale="Given fixture contracts for hypergraph controls",
            ),
        ),
        expected="",
    )
    build(corpus)
    return corpus


def _task(corpus: Corpus, *, seal: bool) -> Task:
    predicates = {
        item.name: item
        for item in corpus.reader().records("predicates")
        if isinstance(item, Predicate)
    }
    requirements = tuple(
        Requirement(
            predicate=revision_of(predicates[name]),
            value=text_value(value),
            operator="equal",
            interpretations=(interpretation,),
            mandatory=True,
        )
        for name, value, interpretation in (
            ("declares_nominal_output", "Finished", Interpretation.DECLARATION),
            ("documented_result_delivery", "incremental", Interpretation.UPSTREAM_CONTRACT),
        )
    )
    return Task(
        logical_id="task:compose",
        profile="fixture",
        goal="construct-object",
        profiles=("fixture",),
        requirements=requirements,
        context=(),
        inputs=(_slot("seed", "Seed"), *([_slot("seal", "Seal")] if seal else [])),
        preferences=(),
        description="Prepare an intermediate, then produce the required documented delivery with both inputs present",
    )


def test_multi_input_composition_rejects_semantic_near_neighbor(tmp_path: Path) -> None:
    """A compatible return type cannot override a refuted result-delivery requirement."""
    corpus = _fixture(tmp_path)
    result = compose(corpus.reader(), _task(corpus, seal=True))
    assert result.plans
    labels = {
        revision_of(item): item.label
        for item in corpus.reader().records("capabilities")
        if isinstance(item, Capability)
    }
    plans = [tuple(labels[step.capability] for step in plan.steps) for plan in result.plans]
    assert any(len(plan) == len(("prepare", "incremental")) for plan in plans)
    assert all(not any("collected" in step for step in plan) for plan in plans)
    assert all(
        plan.disposition == "candidate-requires-witness" and plan.frontier for plan in result.plans
    )


def test_missing_second_input_does_not_become_a_free_solver_assignment(tmp_path: Path) -> None:
    """The final call needs both prerequisites, even though one type-correct path exists."""
    corpus = _fixture(tmp_path)
    result = compose(corpus.reader(), _task(corpus, seal=False))
    assert not result.plans
    assert "impossibility" in result.frontier[0]


def test_intermediate_state_is_replayed_and_a_compatible_loss_is_rejected(tmp_path: Path) -> None:
    """Equal final carriers cannot conceal a property lost at an intermediate operation."""
    from attrs import evolve
    from library_deep_enrichment.corpus.contracts import Policy, Record
    from library_deep_enrichment.corpus.evidence import select
    from library_deep_enrichment.semantics.composition_models import evaluate_composition
    from library_deep_enrichment.semantics.contracts import Assignment
    from library_deep_enrichment.semantics.enrichment_contracts import (
        CompositionGoal,
        InvocationContract,
        TransferMapping,
        TransferModel,
        TransferRule,
    )

    corpus = _fixture(tmp_path)
    task = evolve(
        _task(corpus, seal=True),
        requirements=_task(corpus, seal=True).requirements[:1],
        context=(Assignment(variable="input.seed.flag", value=text_value("retained")),),
    )
    goal = CompositionGoal(
        logical_id="goal",
        profile="fixture",
        task=revision_of(task),
        required=(Assignment(variable="result.flag", value=text_value("retained")),),
    )
    declarations = {
        revision_of(item): item
        for item in corpus.reader().records("operations")
        if isinstance(item, Operation)
    }
    capabilities = tuple(
        item
        for item in corpus.reader().records("capabilities")
        if isinstance(item, Capability) and item.schema == task.goal
    )
    records: list[Record] = [task, goal]
    contracts = []
    for capability in capabilities:
        operation = declarations[capability.operation]
        source = "seed.flag" if operation.symbol == "prepare" else "part.flag"
        model = TransferModel(
            logical_id=f"model:{operation.symbol}",
            name=operation.symbol,
            condition="",
            rules=(
                TransferRule(
                    output="result.flag",
                    operator="constant" if operation.symbol == "collected" else "copy",
                    inputs=() if operation.symbol == "collected" else (source,),
                    value=text_value("lost"),
                ),
            ),
            description="Explicit fixture state transition",
        )
        mapping = TransferMapping(
            logical_id=f"mapping:{operation.symbol}",
            profile="fixture",
            operation=capability.operation,
            model=revision_of(model),
            condition="",
            interpretation="modeled",
            scope="",
            support=(select(operation, "/signature", "fixture"),),
        )
        contract = InvocationContract(
            logical_id=f"invocation:{operation.symbol}",
            profile="fixture",
            capability=revision_of(capability),
            mapping=revision_of(mapping),
            inputs=capability.inputs,
            outputs=capability.outputs,
            expression=operation.symbol,
            support=mapping.support,
            frontier=("Fixture specialization needs an actual invocation witness",),
        )
        contracts.append(contract)
        records.extend((model, mapping))
        records.extend(
            Policy(
                logical_id=f"approval:{item.logical_id}",
                kind=kind,
                subject=revision_of(item),
                authority="fixture-review",
                rationale="Explicit fixture model; no production library assertion",
                allowed_predicates=(),
                required_scopes=(),
            )
            for item, kind in (
                (model, "transfer-model-approval"),
                (mapping, "transfer-mapping-approval"),
                (contract, "invocation-approval"),
            )
        )
    writer = Coordinator(corpus, WriterIdentity(principal="fixture-review", role="policy"))
    writer.commit(records, expected=corpus.reader().manifest_id)
    build(corpus)
    writer.commit(contracts, expected=corpus.reader().manifest_id)
    result = compose(corpus.reader(), task)
    outcomes = [evaluate_composition(corpus.reader(), plan, goal) for plan in result.plans]
    assert {evaluation.disposition for evaluation, _ in outcomes} == {
        "modeled-requires-witness",
        "rejected",
    }
    assert all(
        len(transfers) == len(result.plans[index].steps)
        for index, (_, transfers) in enumerate(outcomes)
    )
    assert all(transfers[-1].inputs[0].value.text == "retained" for _, transfers in outcomes)
    writer.commit(
        (
            result.scope,
            *result.plans,
            *(record for evaluation, transfers in outcomes for record in (*transfers, evaluation)),
        ),
        expected=corpus.reader().manifest_id,
    )
    _tamper_controls(
        corpus,
        task,
        result.plans[0],
        next(item for item, _ in outcomes if item.disposition == "modeled-requires-witness"),
    )


def _tamper_controls(
    corpus: Corpus, task: Task, plan: Composition, evaluation: CompositionEvaluation
) -> None:
    import pytest
    from attrs import evolve
    from library_deep_enrichment.corpus.backend import CorpusError
    from library_deep_enrichment.corpus.validation import validate_records
    from library_deep_enrichment.semantics.composition_programs import render
    from library_deep_enrichment.semantics.contracts import Assignment
    from library_deep_enrichment.semantics.enrichment_contracts import CompositionProgram
    from library_deep_enrichment.workflows.engine import overlay

    writer = Coordinator(corpus, WriterIdentity(principal="fixture-review", role="policy"))
    with pytest.raises(CorpusError, match="replayed intermediate states"):
        writer.commit((evolve(evaluation, outputs=()),), expected=corpus.reader().manifest_id)
    builder = ObservationBuilder("generated-program-tampering-control")
    initial = tuple(
        Assignment(variable=slot.role, value=text_value(slot.role)) for slot in task.inputs
    )
    program = CompositionProgram(
        logical_id="program",
        profile="fixture",
        composition=revision_of(plan),
        inputs=initial,
        prologue=builder.own_bytes(b"fn main() {", media_type="text/rust"),
        epilogue=builder.own_bytes(b"}", media_type="text/rust"),
        program=builder.own_bytes(
            render(corpus.reader(), plan, initial, "fn main() {", "}"), media_type="text/rust"
        ),
    )
    builder.add(program)
    validate_records(
        overlay(corpus.reader(), builder.records.values()), tuple(builder.records.values())
    )
    forged = evolve(
        program, program=builder.own_bytes(b"different program", media_type="text/rust")
    )
    with pytest.raises(CorpusError, match="differs from its generated composition"):
        validate_records(overlay(corpus.reader(), (*builder.records.values(), forged)), (forged,))
