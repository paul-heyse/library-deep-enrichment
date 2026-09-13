"""Retained Python boundary positives, missing dispatch, nested-owner and forgery controls."""

from __future__ import annotations

import json
import shutil
from typing import TYPE_CHECKING, Literal

import pytest
from attrs import asdict, evolve
from library_deep_enrichment.analyses.fabric_contracts import PythonBoundary, PythonBoundaryRequest
from library_deep_enrichment.analyses.python_fabric import analyze, validate
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import bytes_digest, canonical
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import FactArtifact, FactShard, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.workflows.python_boundaries import build

from tests.test_native_fabric import _artifact

if TYPE_CHECKING:
    from pathlib import Path


def _lane(
    root: Path, lane: Literal["syntax", "types"], rows: list[dict], source: bytes
) -> FactArtifact:
    artifact = _artifact(root)
    witness = FileEntry(
        path="subject.py", digest=bytes_digest(source), size=len(source), kind="python"
    )
    (root / witness.path).write_bytes(source)
    shard = b"".join(canonical(row) + b"\n" for row in rows)
    (root / "shard.jsonl").write_bytes(shard)
    header = json.loads((root / "header.json").read_bytes())
    header["expected_records"] = len(rows)
    (root / "header.json").write_bytes(canonical(header))
    receipt = canonical(
        {
            "header": header,
            "dependencies": [],
            "witnesses": [asdict(witness)],
            "terminal": {"records": len(rows), "coverage": {"state": "complete"}},
        }
    )
    (root / "receipt.json").write_bytes(receipt)
    return evolve(
        artifact,
        id=f"facts:{lane}",
        artifact_kind=lane,
        witnesses=(witness,),
        receipt_digest=bytes_digest(receipt),
        shards=(FactShard(path="shard.jsonl", digest=bytes_digest(shard), records=len(rows)),),
    )


def test_boundary_exact_sources_and_portability(tmp_path: Path) -> None:
    """A typed callee candidate stays a candidate, and removing it from a packet fails replay."""
    source = b"def run():\n    return fn()\n"
    start = source.index(b"fn")
    digest = bytes_digest(source)
    syntax = [
        {
            "id": "owner",
            "kind": "definition",
            "file": "subject.py",
            "payload": {
                "node_kind": "function_definition",
                "signature": "def run():",
                "source_digest": digest,
            },
        },
        {
            "id": "call",
            "kind": "operation",
            "file": "subject.py",
            "payload": {
                "node_kind": "call",
                "owner": "owner",
                "start": start,
                "end": start + 4,
                "source_digest": digest,
                "fields": [{"name": "function", "start": start, "end": start + 2}],
            },
        },
        {
            "id": "nested",
            "kind": "operation",
            "file": "subject.py",
            "payload": {"node_kind": "call", "owner": "other", "start": start, "end": start + 4},
        },
    ]
    typed = [
        {
            "id": "target",
            "file": "subject.py",
            "source_digest": digest,
            "payload": {
                "kind": "call",
                "anchor": {"start": start, "end": start + 2},
                "target": "example.fn",
                "dispatch": "candidate",
            },
        }
    ]
    corpus = Corpus(tmp_path / "corpus")
    for lane, rows in (("syntax", syntax), ("types", typed)):
        assert lane in {"syntax", "types"}
        root = tmp_path / lane
        artifact = _lane(root, "syntax" if lane == "syntax" else "types", rows, source)
        admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,), stage=lane))
    reader = corpus.reader()
    owner = next(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact) and item.native_id == "owner"
    )
    artifact = next(
        item
        for item in reader.records("native_artifacts")
        if isinstance(item, NativeArtifact) and item.lane == "types"
    )
    request = PythonBoundaryRequest(
        logical_id="test-boundary",
        profile="fixture",
        owner=revision_of(owner),
        types=revision_of(artifact),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    record = next(corpus.reader().records("python_boundaries"))
    assert isinstance(record, PythonBoundary)
    assert len(record.calls) == 1
    assert len(record.calls[0].targets) == 1
    assert record.calls[0].state == "candidate"
    with pytest.raises(CorpusError, match="source-alignment replay"):
        validate(corpus.reader(), (evolve(record, calls=()),))
    with pytest.raises(CorpusError, match="same-profile"):
        analyze(corpus.reader(), evolve(request, profile="different"))
    for lane in ("syntax", "types"):
        shutil.rmtree(tmp_path / lane)
    destination = tmp_path / "export"
    export_view(corpus.reader(), destination)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, destination, head="analysis")
    assert analyze(restored.reader(), request) == record
