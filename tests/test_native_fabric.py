"""Native facts remain exactly attributable after the transport directory is removed."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import bytes_digest, canonical
from library_deep_enrichment.corpus.evidence import read_field
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.native_validation import validate
from library_deep_enrichment.corpus.signature_syntax import return_clause
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import FactArtifact, FactShard
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts


def _artifact(root: Path) -> FactArtifact:
    root.mkdir()
    source = b'{"files": []}'
    row = {
        "id": "syntax:test",
        "kind": "operation",
        "symbol": "subject.run",
        "file": "subject.py",
        "payload": {"owner": "subject", "node_kind": "call", "start": 5, "end": 11},
    }
    shard = canonical(row) + b"\n"
    header = {"expected_records": 1, "input_digest": bytes_digest(source)}
    receipt = {
        "header": header,
        "dependencies": [],
        "witnesses": [],
        "terminal": {"records": 1, "coverage": {"state": "complete"}},
    }
    receipt_bytes = canonical(receipt)
    for path, data in (
        ("input.json", source),
        ("shard.jsonl", shard),
        ("header.json", canonical(header)),
        ("receipt.json", receipt_bytes),
    ):
        (root / path).write_bytes(data)
    return FactArtifact(
        id="facts:fixture",
        schema="library-guides.source-facts.v1",
        profile="fixture",
        producer="verified-worker-fixture",
        input_path="input.json",
        input_digest=bytes_digest(source),
        header_path="header.json",
        receipt_path="receipt.json",
        receipt_digest=bytes_digest(receipt_bytes),
        shards=(FactShard(path="shard.jsonl", digest=bytes_digest(shard), records=1),),
        outcome="complete",
        artifact_kind="syntax",
    )


def test_native_authority_and_forged_projection(tmp_path: Path) -> None:
    """Only managed bytes and checked projections control an admitted native read."""
    transport = tmp_path / "transport"
    inputs = NativeInputs(root=transport, artifacts=(_artifact(transport),))
    corpus = Corpus(tmp_path / "corpus")
    first = admit_artifacts(corpus, inputs)
    assert not first.reused
    assert admit_artifacts(corpus, inputs).reused
    reader = corpus.reader()
    fact = next(reader.records("native_facts"))
    assert isinstance(fact, NativeFact)
    with pytest.raises(CorpusError, match="differs from original"):
        validate(reader, evolve(fact, symbol="invented.call"))
    shutil.rmtree(transport)
    from library_deep_enrichment.corpus.schemas import revision_of

    assert read_field(reader, "native_facts", revision_of(fact), "/raw/payload/node_kind") == "call"


def test_native_receipt_denominator_is_not_a_citation_gesture(tmp_path: Path) -> None:
    """A genuine receipt digest cannot disguise an invalid record denominator."""
    transport = tmp_path / "transport"
    artifact = _artifact(transport)
    raw = json.loads((transport / "receipt.json").read_bytes())
    raw["terminal"]["records"] = 2
    data = canonical(raw)
    (transport / "receipt.json").write_bytes(data)
    artifact = evolve(artifact, receipt_digest=bytes_digest(data))
    with pytest.raises(ValueError, match="denominator"):
        admit_artifacts(
            Corpus(tmp_path / "corpus"), NativeInputs(root=transport, artifacts=(artifact,))
        )


def test_contextual_identity_does_not_merge_reused_item_ids_across_artifacts(
    tmp_path: Path,
) -> None:
    """Identical local IDs and source spelling do not prove a cross-artifact identity join."""
    from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
    from library_deep_enrichment.corpus.identities import identify, join
    from library_deep_enrichment.corpus.schemas import revision_of
    from library_deep_enrichment.publication.export import export_view, import_view

    transport = tmp_path / "transport"
    first = _artifact(transport)
    second = evolve(first, id="facts:second-context")
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=transport, artifacts=(first, second)))
    reader = corpus.reader()
    facts = tuple(reader.records("native_facts"))
    assert len(facts) == len((first, second))
    identities = tuple(identify(reader, "native_facts", revision_of(fact)) for fact in facts)
    assert identities[0].identities != identities[1].identities
    assert join(identities[0], identities[0]).resolution == "exact-source"
    cross = join(*identities)
    assert cross.resolution == "unresolved"
    writer = Coordinator(corpus, WriterIdentity(principal="identity-check"))
    writer.commit((*identities, cross), expected=reader.manifest_id)
    with pytest.raises(CorpusError, match="contextual identity"):
        writer.commit(
            (evolve(cross, resolution="exact-source"),), expected=corpus.reader().manifest_id
        )
    archive = tmp_path / "export"
    export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive) == corpus.reader().manifest_id


@pytest.mark.parametrize(
    ("signature", "expected"),
    [
        ("fn(f: fn(T) -> U) -> fn(V) -> W", "fn(V) -> W"),
        ("fn map<F: Fn(T) -> U>(f: F) -> Vec<U>", "Vec<U>"),
        ("def f(x: Callable[[A], B]) -> Callable[[C], D]:", "Callable[[C], D]"),
        ("fn f(callback: fn() -> ())", ""),
    ],
)
def test_nested_callback_return_recovery(signature: str, expected: str) -> None:
    """The operation return is selected independently of nested function arrows."""
    assert return_clause(signature) == expected


def test_native_corruption_withdraws_current_success(tmp_path: Path) -> None:
    """A source mutation cannot turn a previous successful admission into warm reuse."""
    from library_deep_enrichment.corpus.contracts import Disposition, Job

    transport = tmp_path / "transport"
    inputs = NativeInputs(root=transport, artifacts=(_artifact(transport),))
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, inputs)
    pinned = corpus.reader()
    (transport / "shard.jsonl").write_text("{}\n")
    with pytest.raises(ValueError, match="artifact changed"):
        admit_artifacts(corpus, inputs)
    job = corpus.reader().lookup("jobs", "native:native-scope")
    assert isinstance(job, Job)
    assert job.disposition == Disposition.FAILED
    assert tuple(corpus.reader().records("native_facts")) == ()
    assert len(tuple(pinned.records("native_facts"))) == 1


def test_python_source_interface_preserves_slots_and_replays_without_transport(
    tmp_path: Path,
) -> None:
    """Defaults remain unevaluated; current source slots cannot become a runtime guarantee."""
    from library_deep_enrichment.corpus.contracts import Operation
    from library_deep_enrichment.corpus.native_contracts import NativeArtifact
    from library_deep_enrichment.corpus.python_interfaces import normalize
    from library_deep_enrichment.corpus.python_interfaces import validate as validate_interface
    from library_deep_enrichment.corpus.schemas import revision_of
    from library_deep_enrichment.workflows.python_interfaces import build

    transport = tmp_path / "transport"
    artifact = _artifact(transport)
    row = {
        "id": "syntax:function",
        "kind": "definition",
        "symbol": "decode",
        "file": "example.py",
        "payload": {
            "node_kind": "function_definition",
            "owner": None,
            "syntax_valid": True,
            "signature": "def decode(value: bytes, /, *args, strict: bool = dangerous(), **kwargs) -> list[int]:",
        },
    }
    raw = canonical(row) + b"\n"
    (transport / "shard.jsonl").write_bytes(raw)
    artifact = evolve(
        artifact, shards=(FactShard(path="shard.jsonl", digest=bytes_digest(raw), records=1),)
    )
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=transport, artifacts=(artifact,)))
    native = next(corpus.reader().records("native_artifacts"))
    assert isinstance(native, NativeArtifact)
    build(corpus, revision_of(native))
    assert build(corpus, revision_of(native)).reused
    reader = corpus.reader()
    operation = next(reader.records("operations"))
    assert isinstance(operation, Operation)
    assert operation.routes == ()
    assert operation.returns == "list[int]"
    assert tuple(item.kind for item in operation.parameters) == (
        "positional_only",
        "variadic_positional",
        "keyword_only",
        "variadic_keyword",
    )
    assert operation.parameters[2].default_expression == "dangerous()"
    assert not operation.parameters[2].required
    with pytest.raises(CorpusError, match="exact source normalization"):
        validate_interface(reader, evolve(operation, routes=("example.decode",)))
    fact = next(reader.records("native_facts"))
    assert isinstance(fact, NativeFact)
    shutil.rmtree(transport)
    assert normalize(reader, fact) == operation


def _mir_artifact(root: Path, *, projected: bool = False) -> FactArtifact:
    artifact = _artifact(root)
    body = {
        "locals": [{"index": 0, "role": "return"}, {"index": 1, "role": "argument"}],
        "events": [
            {
                "block": 0,
                "statement": 0,
                "kind": "use",
                "destination": {"local": 0, "projection": [{"kind": "deref"}] if projected else []},
                "values": [{"mode": "copy", "place": {"local": 1, "projection": []}, "ty": None}],
            }
        ],
        "exits": [
            {"block": 0, "kind": "return", "successors": [], "args": [], "unwind_block": None}
        ],
        "frontier": [],
    }
    raw = (
        canonical(
            {
                "id": "mir:fixture:1",
                "kind": "mir_owner",
                "symbol": "fixture::return_arg",
                "payload": body,
            }
        )
        + b"\n"
    )
    (root / "shard.jsonl").write_bytes(raw)
    return evolve(
        artifact,
        schema="library-guides.mir.v1",
        artifact_kind="mir",
        shards=(FactShard(path="shard.jsonl", digest=bytes_digest(raw), records=1),),
    )


@pytest.mark.parametrize("projected", [False, True])
def test_fabric_source_analysis_replays_after_transport_removal(
    tmp_path: Path, *, projected: bool
) -> None:
    """Actual retained MIR fields drive typed flow/effects, open writes, and tamper rejection."""
    from library_deep_enrichment.analyses.fabric import validate as validate_analysis
    from library_deep_enrichment.analyses.fabric_contracts import AnalysisRequest, SourceAnalysis
    from library_deep_enrichment.corpus.schemas import revision_of
    from library_deep_enrichment.publication.export import export_view, import_view
    from library_deep_enrichment.workflows.source_analysis import build

    transport = tmp_path / "mir-transport"
    corpus = Corpus(tmp_path / "mir-corpus")
    admit_artifacts(
        corpus,
        NativeInputs(root=transport, artifacts=(_mir_artifact(transport, projected=projected),)),
    )
    fact = next(corpus.reader().records("native_facts"))
    assert isinstance(fact, NativeFact)
    request = AnalysisRequest(
        logical_id="fixture-flow",
        profile=fact.profile,
        artifact=fact.artifact,
        owners=(revision_of(fact),),
    )
    shutil.rmtree(transport)
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    result = next(corpus.reader().records("source_analyses"))
    assert isinstance(result, SourceAnalysis)
    assert ("projected_memory_write" in result.may_effects) == projected
    assert "argument:1" in result.return_dependencies
    assert bool(result.frontier) == projected
    with pytest.raises(CorpusError, match="independent model replay"):
        validate_analysis(corpus.reader(), (evolve(result, return_dependencies=("invented",)),))
    destination = tmp_path / "analysis-export"
    export_view(corpus.reader(), destination)
    restored = Corpus(tmp_path / "analysis-restored")
    assert import_view(restored, destination, head="analysis") == corpus.reader().manifest_id
    assert restored.reader().get("source_analyses", revision_of(result)) == result
