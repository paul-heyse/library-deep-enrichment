"""Pinned type-provider evidence through source alignment, replay and portable closure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attrs import evolve
from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest
from library_deep_enrichment.analyses.behavior.service import validate
from library_deep_enrichment.analyses.behavior.typing_contracts import BehaviorTyping
from library_deep_enrichment.analyses.behavior.typing_locations import RetainedFiles, utf16_offset
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.contracts import Budget, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import canonical_bytes, digest_file
from library_deep_enrichment.workflows.behavior import build

from tests.test_native_lanes import SCHEMAS, _binary


@pytest.fixture(scope="module")
def typed_corpus(tmp_path_factory: pytest.TempPathFactory) -> tuple[Corpus, BehaviorRequest]:
    """Acquire both real native lanes with source, re-export and stub controls.

    Returns:
        An admitted source/typing request before behavioral derivation.

    """
    root = tmp_path_factory.mktemp("behavior-typing")
    sources = {
        "origin.py": "def café(value: int) -> int:\n    return value\n",
        "bridge.py": "from origin import café as chosen\n",
        "interface.pyi": "def opaque(value: int) -> int: ...\n",
        "subject.py": (
            "from bridge import chosen\nfrom interface import opaque\n"
            "def use(value: int):\n    first = chosen(value)\n    return opaque(first)\n"
        ),
    }
    for name, source in sources.items():
        (root / name).write_text(source)
    witnesses = tuple(
        FileEntry(
            path=str(root / name),
            digest=digest_file(root / name),
            size=(root / name).stat().st_size,
            kind="python",
        )
        for name in sources
    )
    profile = "typing-control"
    syntax_request = {
        "root": str(root),
        "profile": profile,
        "python_minor": 14,
        "lexical": True,
        "execution": True,
        "files": [
            {"path": "subject.py", "digest": digest_file(root / "subject.py"), "language": "python"}
        ],
    }
    subject = sources["subject.py"]
    queries = [
        {
            "module": "subject",
            "start": subject.rfind("chosen"),
            "end": subject.rfind("chosen") + len("chosen"),
            "role": role,
        }
        for role in ("computed", "declared", "expected")
    ]
    queries.append(
        {
            "module": "subject",
            "start": subject.rfind("opaque"),
            "end": subject.rfind("opaque") + len("opaque"),
            "role": "declared",
        }
    )
    typed_request = {
        "root": str(root),
        "profile": profile,
        "python_version": "3.14",
        "python_platform": "linux",
        "search_paths": ["."],
        "files": [
            {"path": name, "digest": digest_file(root / name), "module": name.split(".")[0]}
            for name in sources
        ],
        "targeted_queries": queries,
    }
    artifacts = []
    for kind, helper, schema, request in (
        ("execution", "source-facts", "source-execution", syntax_request),
        ("types", "python-semantics", "python-semantics", typed_request),
    ):
        path = root / (kind + ".json")
        path.write_bytes(canonical_bytes(request))
        artifacts.append(
            extract(
                root,
                SourceJob(
                    id="typing-control-" + kind,
                    kind=kind,
                    input=str(path),
                    helper=str(_binary(helper)),
                    profile=profile,
                    schema=str(SCHEMAS / (schema + ".v1.schema.json")),
                    witnesses=witnesses,
                    inputs=tuple((item.path, item.digest) for item in witnesses),
                ),
                Budget(),
            )
        )
    corpus = Corpus(root / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=tuple(artifacts)))
    reader = corpus.reader()
    owner = next(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact) and item.kind == "definition" and item.symbol == "use"
    )
    types = next(
        item
        for item in reader.records("native_artifacts")
        if isinstance(item, NativeArtifact) and item.lane == "types"
    )
    request = BehaviorRequest(
        logical_id="typing-control",
        profile=profile,
        owners=(revision_of(owner),),
        artifacts=(owner.artifact,),
        type_artifacts=(revision_of(types),),
    )
    return corpus, request


def test_static_type_locations_preserve_roles_stub_boundary_and_portable_sources(
    typed_corpus: tuple[Corpus, BehaviorRequest], tmp_path: Path
) -> None:
    """Actual type facts join source bytes without promoting a stub or annotation to code."""
    corpus, request = typed_corpus
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    reader = corpus.reader()
    evidence = tuple(reader.records("behavior_typing"))
    assert len(evidence) == 1
    item = evidence[0]
    assert isinstance(item, BehaviorTyping)
    assert item.source
    assert {point.role for point in item.points} >= {
        "computed",
        "declared",
        "expected",
        "call_candidate",
    }
    locations = [location for point in item.points for location in point.declarations]
    functions = [location for location in locations if location.name == "café"]
    assert functions
    assert all(location.state == "source_declaration" for location in functions)
    start, end = len(b"def "), len("def café".encode())
    assert all((location.start, location.end) == (start, end) for location in functions)
    assert any(
        location.name == "opaque" and location.state == "stub_interface" for location in locations
    )
    assert item.frontier
    with pytest.raises(CorpusError, match="retained-source replay"):
        validate(reader, (evolve(item, frontier=()),))
    exported = export_view(reader, tmp_path / "portable")
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, tmp_path / "portable") == exported.manifest
    assert tuple(restored.reader("release").records("behavior_typing")) == evidence


def test_declaration_identity_ignores_protocol_numbering_but_preserves_context(
    typed_corpus: tuple[Corpus, BehaviorRequest],
) -> None:
    """Renumbered TSP nodes retain identity; another context or absent source does not."""
    corpus, request = typed_corpus
    reader = corpus.reader()
    artifact = reader.get("native_artifacts", request.type_artifacts[0])
    assert isinstance(artifact, NativeArtifact)
    resolver = RetainedFiles(reader, artifact)
    row = next(
        json.loads(resolve_bytes(reader, fact.original))
        for fact in reader.filtered_records("native_facts", (("artifact", revision_of(artifact)),))
        if isinstance(fact, NativeFact) and fact.kind == "targeted"
    )
    wire = json.loads(row["payload"]["tsp"]["raw_tsp"])
    original = resolver.declarations(wire)
    absent = resolver.declarations({"kind": 6, "declaration": None})
    assert len(absent) == 1
    assert absent[0].state == "declaration_absent"
    assert not absent[0].identity
    wire["id"] += 1000
    assert resolver.declarations(wire) == original
    other = RetainedFiles(reader, evolve(artifact, context="other-context"))
    assert {item.identity for item in other.declarations(wire) if item.identity} != {
        item.identity for item in original if item.identity
    }
    wire["declaration"]["node"]["uri"] = "file:///source-not-in-the-request.py"
    missing = resolver.declarations(wire)[0]
    assert missing.state == "source_not_retained"
    assert not missing.source
    assert not missing.identity


def test_lsp_conversion_rejects_surrogate_splits_and_cross_line_columns() -> None:
    """An astral character consumes two UTF-16 units and four bytes, including under CRLF."""
    source = "a😀é\r\nnext\n".encode()
    assert utf16_offset(source, 0, 3) == len("a😀".encode())
    assert utf16_offset(source, 1, 0) == len("a😀é\r\n".encode())
    for line, column in ((0, 2), (0, 5), (3, 0), (-1, 0)):
        with pytest.raises(CorpusError):
            utf16_offset(source, line, column)
