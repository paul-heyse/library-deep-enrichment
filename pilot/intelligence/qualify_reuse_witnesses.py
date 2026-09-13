"""Retain finite strictness/framing counterexamples under the generalized core freeze."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from library_guides.corpus.admission import Coordinator, WriterIdentity
from library_guides.corpus.contracts import Operation, Policy, Record
from library_guides.corpus.encoding import canonical
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.staging import ObservationBuilder
from library_guides.corpus.store import Corpus
from library_guides.corpus.validation import references
from library_guides.publication.closure import _source_links
from library_guides.publication.export import export_view, import_view
from library_guides.semantics.enrichment_contracts import (
    WitnessObservation,
    WitnessRecipe,
    WitnessRun,
)
from library_guides.semantics.experiments import run_witness

from pilot.intelligence.qualify_reuse import REPORTS, RUN, verify_freeze


def _seed(corpus: Corpus, name: str, symbols: dict[str, str]) -> dict[str, str]:
    reader = Corpus(RUN / f"reuse-{name}" / "corpus", max_rows=2_500_000).reader()
    operations = {
        item.symbol: item
        for item in reader.records("operations")
        if isinstance(item, Operation) and item.symbol in symbols.values()
    }
    assert set(operations) == set(symbols.values())
    pending = deque(("operations", revision_of(item)) for item in operations.values())
    retained: dict[str, Record] = {}
    while pending:
        family, revision = pending.popleft()
        if revision not in retained:
            record = reader.get(family, revision)
            retained[revision] = record
            pending.extend((*references(record), *_source_links(record)))
    Coordinator(corpus, WriterIdentity(principal="witness-source-retention")).commit(
        retained.values(), expected=corpus.reader().manifest_id
    )
    return {field: revision_of(operations[symbol]) for field, symbol in symbols.items()}


def _recipe(corpus: Corpus, name: str, fields: tuple[str, ...]) -> WitnessRecipe:
    files = Path(__file__).with_name("witnesses")
    builder = ObservationBuilder("reuse-finite-witness-authoring.v1")
    recipe = WitnessRecipe(
        logical_id=f"recipe:{name}-input-counterexample",
        profile="pydantic-2.13.4" if name == "pydantic" else "serde-json-1.0.151",
        name=f"{name} finite input counterexample",
        language="python" if name == "pydantic" else "rust",
        program=builder.own_bytes(
            (
                files / ("input_strictness.py" if name == "pydantic" else "serde_framing.rs")
            ).read_bytes(),
            media_type="text/plain",
        ),
        manifest=builder.own_bytes(
            b"" if name == "pydantic" else (files / "serde_framing.toml").read_bytes(),
            media_type="text/plain",
        ),
        packages=("pydantic==2.13.4",)
        if name == "pydantic"
        else ("serde==1.0.228", "serde_json==1.0.151"),
        toolchain="CPython 3.14" if name == "pydantic" else "1.98.1-x86_64-unknown-linux-gnu",
        description="Exactly the retained date-string strictness pair or a complete object followed by WouldBlock. This is neither universal strictness equivalence nor an actual persistent socket timing experiment.",
        fields=fields,
    )
    builder.add(recipe)
    builder.add(
        Policy(
            logical_id=f"approval:{recipe.logical_id}",
            kind="witness-recipe-approval",
            subject=revision_of(recipe),
            authority="implementation-agent",
            rationale="Same-agent finite program review with expected negative and positive outcomes; no independent review.",
            allowed_predicates=(),
            required_scopes=(),
        )
    )
    Coordinator(corpus, WriterIdentity(principal="implementation-agent", role="policy")).commit(
        builder.records.values(), expected=corpus.reader().manifest_id
    )
    return recipe


def run(name: str, symbols: dict[str, str]) -> dict[str, object]:
    """Execute and independently restore an exact finite witness scope.

    Returns:
        The portable artifact, observation values and explicit manual binding count.

    """
    work = RUN / f"reuse-{name}-witness-{verify_freeze()[:16]}"
    corpus = Corpus(work / "corpus", max_rows=2_500_000)
    bindings = _seed(corpus, name, symbols)
    recipe = _recipe(corpus, name, tuple(symbols))
    manifest = run_witness(corpus, recipe, bindings)
    assert run_witness(corpus, recipe, bindings) == manifest
    selected = corpus.reader()
    runs = [item for item in selected.records("witness_runs") if isinstance(item, WitnessRun)]
    assert len(runs) == 1
    assert runs[0].returncode == 0
    observations = [
        item
        for item in selected.records("witness_observations")
        if isinstance(item, WitnessObservation)
    ]
    values = {item.field: item.value.text for item in observations}
    assert set(values.values()) == {"false", "true"}
    destination = work / "export"
    export_view(selected, destination)
    restored = Corpus(work / "restored", max_rows=2_500_000)
    assert import_view(restored, destination, head="analysis") == manifest
    assert {revision_of(item) for item in restored.reader().records("witness_observations")} == {
        revision_of(item) for item in observations
    }
    return {
        "library": name,
        "manifest": manifest,
        "export": str(destination),
        "recipe": revision_of(recipe),
        "run": revision_of(runs[0]),
        "values": values,
        "witness_bindings": len(bindings),
        "operation_overrides": 0,
        "warm_reuse": True,
        "portable_replay": True,
        "scope_limit": recipe.description,
    }


if __name__ == "__main__":
    freeze = verify_freeze()
    results = [
        run(
            "pydantic",
            {
                "/python_accepts": "pydantic.type_adapter.TypeAdapter.validate_python",
                "/json_accepts": "pydantic.type_adapter.TypeAdapter.validate_json",
            },
        ),
        run(
            "serde",
            {
                "/whole_document_before_eof": "serde_json::de::from_reader",
                "/prefix_before_eof": "serde_json::<impl Deserializer<read::IoRead<R>>>::from_reader",
            },
        ),
    ]
    assert verify_freeze() == freeze
    (REPORTS / "completion-reuse-witnesses.json").write_bytes(
        canonical(
            {
                "freeze": freeze,
                "author": "implementation-agent",
                "reviewer": "same implementation-agent",
                "independent_review": False,
                "results": results,
            }
        )
        + b"\n"
    )
