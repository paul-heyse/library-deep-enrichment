"""Generate, model, compile, and contrast real Arrow Schema compositions in a scoped corpus."""

from __future__ import annotations

from collections import deque
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from attrs import evolve
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Operation, Passage, Policy, TypeUse
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.corpus.validation import references
from library_deep_enrichment.publication.closure import _source_links
from library_deep_enrichment.publication.export import export_view
from library_deep_enrichment.semantics.composition_models import evaluate_composition
from library_deep_enrichment.semantics.composition_programs import render, witness_disposition
from library_deep_enrichment.semantics.contracts import Assignment, Capability, Composition, Slot, Task
from library_deep_enrichment.semantics.enrichment_contracts import (
    CompositionGoal,
    CompositionProgram,
    CompositionWitness,
    InvocationContract,
    TransferMapping,
    TransferModel,
    TransferRule,
    WitnessRecipe,
    WitnessRun,
)
from library_deep_enrichment.semantics.experiments import run_witness
from library_deep_enrichment.semantics.planning import PlanBudget, compose
from library_deep_enrichment.semantics.vocabulary import approve_rules, foundation, text_value
from library_deep_enrichment.workflows import semantics, shapes

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record

PROFILE = "rust-docsrs-54.1-58.4"
EXPECTED_PLANS = 2
SYMBOLS = {
    f"arrow_schema::<impl Schema>::{name}" for name in ("new", "new_with_metadata", "project")
}
PROLOGUE = """use arrow_schema::{DataType, Field, Schema};
use std::collections::HashMap;
fn main() {
let fields = vec![Field::new("temperature", DataType::Float64, true), Field::new("id", DataType::Int64, false)];
let metadata = HashMap::from([("dataset".into(), "measurements".into())]);
let indices = vec![0usize];"""
EPILOGUE = """println!("{{\\"environment\\":{{\\"arrow-schema\\":\\"58.4.0\\"}},\\"metadata\\":\\"{}\\",\\"fields\\":{}}}",
$RESULT.metadata().get("dataset").cloned().unwrap_or_default(), $RESULT.fields().len());
}"""


def _approval(record: Record, kind: str) -> Policy:
    return Policy(
        logical_id=f"approval:{record.logical_id}",
        kind=kind,
        subject=revision_of(record),
        authority="implementation-agent",
        rationale="Same agent authors and reviews this explicitly modeled, finite pilot specialization",
        allowed_predicates=(),
        required_scopes=(),
    )


def _writer(corpus: Corpus) -> Coordinator:
    return Coordinator(corpus, WriterIdentity(principal="composition-pilot", role="policy"))


def _seed(corpus: Corpus) -> str:
    reader = Corpus(
        Path(".cache/library-guides-intelligence/pilot-v4/corpus"), max_rows=2_500_000
    ).reader()
    operations = tuple(
        item
        for item in reader.records("operations")
        if isinstance(item, Operation)
        and item.profile == PROFILE
        and item.symbol in SYMBOLS
        and any(source.family == "native_facts" for source in item.evidence)
    )
    assert {item.symbol for item in operations} == SYMBOLS
    assert len(operations) == len(SYMBOLS)
    owners = {revision_of(item) for item in operations}
    pending = deque(("operations", revision_of(item)) for item in operations)
    for family, cls in (("passages", Passage), ("type_uses", TypeUse)):
        pending.extend(
            (family, revision_of(item))
            for item in reader.records(family)
            if isinstance(item, cls) and item.owner in owners
        )
    retained: dict[str, Record] = {}
    while pending:
        family, revision = pending.popleft()
        if revision in retained:
            continue
        record = reader.get(family, revision)
        retained[revision] = record
        pending.extend((*references(record), *_source_links(record)))
    models = foundation()
    _writer(corpus).commit(
        (
            *retained.values(),
            *models,
            *approve_rules(
                models,
                authority="implementation-agent",
                rationale="Retained reusable declaration rules; same agent authors and reviews",
            ),
        ),
        expected="",
    )
    shapes.build(corpus)
    semantics.build(corpus)
    return reader.manifest_id


def _slot(role: str, kind: str) -> Slot:
    return Slot(
        role=role,
        type_expression=kind,
        representation="owned-rust-value",
        resource="",
        consumes=False,
    )


def _task() -> Task:
    return Task(
        logical_id="task:project-with-metadata",
        profile=PROFILE,
        profiles=(PROFILE,),
        goal="declared-operation",
        requirements=(),
        preferences=(),
        inputs=(
            _slot("fields", "Vec<Field>"),
            _slot("metadata", "HashMap<String, String>"),
            _slot("indices", "Vec<usize>"),
        ),
        context=(Assignment(variable="input.metadata.value", value=text_value("measurements")),),
        description="Construct a schema, then project valid field indices while retaining dataset metadata",
    )


def _install_models(corpus: Corpus, task: Task) -> CompositionGoal:
    operations = {
        revision_of(item): item
        for item in corpus.reader().records("operations")
        if isinstance(item, Operation)
    }
    records: list[Record] = [task]
    contracts = []
    for capability in corpus.reader().records("capabilities"):
        if not isinstance(capability, Capability):
            continue
        operation = operations[capability.operation]
        name = operation.symbol.rsplit("::", 1)[-1]
        inputs, expression, source = {
            "new": ((_slot("fields", "Vec<Field>"),), "Schema::new({fields}.clone())", ""),
            "new_with_metadata": (
                (_slot("fields", "Vec<Field>"), _slot("metadata", "HashMap<String, String>")),
                "Schema::new_with_metadata({fields}.clone(), {metadata}.clone())",
                "metadata.value",
            ),
            "project": (
                (_slot("self", "Schema"), _slot("indices", "Vec<usize>")),
                '{self}.project(&{indices}).expect("finite fixture indices are valid")',
                "self.metadata",
            ),
        }[name]
        model = TransferModel(
            logical_id=f"model:{name}-metadata",
            name=f"{name} metadata transfer",
            condition="",
            rules=(
                TransferRule(
                    output="result.metadata",
                    operator="copy" if source else "constant",
                    inputs=(source,) if source else (),
                    value=text_value(""),
                ),
            ),
            description="Approved data-authored application of copy/constant semantics; no general inference from carrier identity",
        )
        mapping = TransferMapping(
            logical_id=f"mapping:{name}",
            profile=PROFILE,
            operation=capability.operation,
            model=revision_of(model),
            condition="",
            interpretation="modeled",
            scope="",
            support=(select(operation, "/signature", "exact-specialized-declaration"),),
        )
        contract = InvocationContract(
            logical_id=f"invoke:{name}",
            profile=PROFILE,
            capability=revision_of(capability),
            mapping=revision_of(mapping),
            inputs=inputs,
            outputs=(_slot("result", "Schema"),),
            expression=expression,
            support=mapping.support,
            frontier=(
                "Finite owned inputs and valid indices; borrowing and Result handling remain explicit in generated Rust; compiler/execution witness required",
            ),
        )
        contracts.append(contract)
        records.extend(
            (
                model,
                mapping,
                _approval(model, "transfer-model-approval"),
                _approval(mapping, "transfer-mapping-approval"),
                _approval(contract, "invocation-approval"),
            )
        )
    goal = CompositionGoal(
        logical_id="goal:retain-dataset-metadata",
        profile=PROFILE,
        task=revision_of(task),
        required=(Assignment(variable="result.metadata", value=text_value("measurements")),),
    )
    records.append(goal)
    _writer(corpus).commit(records, expected=corpus.reader().manifest_id)
    semantics.build(corpus)
    _writer(corpus).commit(contracts, expected=corpus.reader().manifest_id)
    return goal


def _programs(
    corpus: Corpus, plans: tuple[Composition, ...], task: Task
) -> tuple[ObservationBuilder, tuple[WitnessRecipe, ...]]:
    builder = ObservationBuilder("generated-composition.v1")
    recipes = []
    for plan in plans:
        inputs = tuple(
            Assignment(variable=slot.role, value=text_value(slot.role)) for slot in task.inputs
        )
        program = CompositionProgram(
            logical_id=f"program:{revision_of(plan)}",
            profile=PROFILE,
            composition=revision_of(plan),
            inputs=inputs,
            prologue=builder.own_bytes(PROLOGUE.encode(), media_type="text/rust"),
            epilogue=builder.own_bytes(EPILOGUE.encode(), media_type="text/rust"),
            program=builder.own_bytes(
                render(corpus.reader(), plan, inputs, PROLOGUE, EPILOGUE), media_type="text/rust"
            ),
        )
        builder.add(program)
        recipe = WitnessRecipe(
            logical_id=f"recipe:{revision_of(plan)}",
            profile=PROFILE,
            name="generated-schema-composition",
            language="rust",
            program=program.program,
            manifest=builder.own_bytes(
                files("library_deep_enrichment")
                .joinpath("assets/witnesses/arrow_schema_projection.toml")
                .read_bytes(),
                media_type="text/toml",
            ),
            packages=("arrow-schema==58.4.0",),
            toolchain="1.98.1-x86_64-unknown-linux-gnu",
            description="Compiler and finite execution of exact generated plan; no universal property claim",
            fields=("/metadata", "/fields"),
        )
        builder.add(recipe)
        builder.add(_approval(recipe, "witness-recipe-approval"))
        recipes.append(recipe)
    return builder, tuple(recipes)


def _run_programs(
    corpus: Corpus, plans: tuple[Composition, ...], recipes: tuple[WitnessRecipe, ...]
) -> None:
    capabilities = tuple(
        corpus.reader().get("capabilities", plan.steps[-1].capability) for plan in plans
    )
    for capability, recipe in zip(capabilities, recipes, strict=True):
        assert isinstance(capability, Capability)
        run_witness(
            corpus, recipe, {"/metadata": capability.operation, "/fields": capability.operation}
        )


def main() -> None:
    """Execute the full source-to-generated-plan-to-contrastive-witness chain."""
    corpus = Corpus(Path(".cache/library-guides-intelligence/composition-pilot") / uuid4().hex)
    source_manifest = _seed(corpus)
    task = _task()
    goal = _install_models(corpus, task)
    result = compose(corpus.reader(), task, PlanBudget(max_steps=2, max_states=64, max_plans=16))
    assert len(result.plans) == EXPECTED_PLANS
    builder, recipes = _programs(corpus, result.plans, task)
    # Install both exact program approvals before the semantic build that they invalidate.
    # This preserves the dependency protocol instead of copying stale stage receipts.
    _writer(corpus).commit(
        (item for item in builder.records.values() if not isinstance(item, CompositionProgram)),
        expected=corpus.reader().manifest_id,
    )
    semantics.build(corpus)
    assert (
        compose(corpus.reader(), task, PlanBudget(max_steps=2, max_states=64, max_plans=16)).plans
        == result.plans
    )
    outcomes = [evaluate_composition(corpus.reader(), plan, goal) for plan in result.plans]
    assert {item.disposition for item, _ in outcomes} == {"modeled-requires-witness", "rejected"}
    derived = (
        result.scope,
        *result.plans,
        *(record for evaluation, transfers in outcomes for record in (*transfers, evaluation)),
        *(item for item in builder.records.values() if isinstance(item, CompositionProgram)),
    )
    _writer(corpus).commit(derived, expected=corpus.reader().manifest_id)
    _run_programs(corpus, result.plans, recipes)
    semantics.build(corpus)
    assert (
        compose(corpus.reader(), task, PlanBudget(max_steps=2, max_states=64, max_plans=16)).plans
        == result.plans
    )
    _writer(corpus).commit(derived, expected=corpus.reader().manifest_id)
    witnesses = []
    for (evaluation, _), recipe in zip(outcomes, recipes, strict=True):
        run = corpus.reader().lookup("witness_runs", f"witness-run:{revision_of(recipe)}", PROFILE)
        program = corpus.reader().lookup(
            "composition_programs", f"program:{evaluation.composition}", PROFILE
        )
        assert isinstance(run, WitnessRun)
        assert isinstance(program, CompositionProgram)
        receipt = CompositionWitness(
            logical_id=f"composition-witness:{evaluation.composition}",
            profile=PROFILE,
            evaluation=revision_of(evaluation),
            program=revision_of(program),
            run=revision_of(run),
            fields=(Assignment(variable="result.metadata", value=text_value("/metadata")),),
            disposition="pending",
        )
        receipt = evolve(receipt, disposition=witness_disposition(corpus.reader(), receipt))
        assert receipt.disposition == "corroborated"
        witnesses.append(receipt)
    _writer(corpus).commit(witnesses, expected=corpus.reader().manifest_id)
    portable = export_view(corpus.reader(), corpus.root.parent / f"{corpus.root.name}-export")
    report = {
        "corpus": str(corpus.root),
        "source_manifest": source_manifest,
        "manifest": corpus.reader().manifest_id,
        "author": "implementation-agent",
        "reviewer": "same implementation-agent",
        "independent_review": False,
        "source_operations": sorted(SYMBOLS),
        "candidate_scope": CONVERTER.unstructure(result.scope),
        "plans": [CONVERTER.unstructure(item) for item in result.plans],
        "evaluations": [CONVERTER.unstructure(item) for item, _ in outcomes],
        "witnesses": [CONVERTER.unstructure(item) for item in witnesses],
        "portable": CONVERTER.unstructure(portable),
        "interpretation": "Both exact generated programs compiled and executed. Their different metadata results corroborate the model for these retained inputs only.",
    }
    Path(
        "tooling/library_deep_enrichment/pilot/intelligence/reports/resume-generated-composition.json"
    ).write_bytes(canonical(report) + b"\n")


if __name__ == "__main__":
    main()
