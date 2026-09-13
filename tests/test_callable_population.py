"""Actual source/compiler joins, denominator preservation, mutation controls and portable replay."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.callable_contracts import CallablePopulation, CallableRequest
from library_deep_enrichment.analyses.callable_population import analyze, validate
from library_deep_enrichment.analyses.callable_sources import RetainedSource
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.native_contracts import NativeArtifact
from library_deep_enrichment.corpus.schemas import REGISTRY, revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.corpus.validation import AdmissionReader
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.facts.witness_origins import read as read_origins
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.callables import build
from tests import test_behavior_mir as mir_controls
from tests.test_declaration_identity import _rekey
from tests.test_native_lanes import SCHEMAS, _binary

native_cases = mir_controls.native_cases


@pytest.fixture(scope="module")
def python_case(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, FactArtifact]:
    """Collect a real public/private/nested/stub population.

    Returns:
        Source and interface candidates under one finite extraction context.

    """
    root = tmp_path_factory.mktemp("callable-python")
    source = root / "public.py"
    source.write_text(
        "class Public:\n"
        " def __iter__(self): return self\n"
        " def run(self):\n"
        "  def nested(): return 1\n"
        "  return nested()\n"
        " def _private(self): return 2\n"
        "class _Private:\n"
        " def run(self): return 3\n"
    )
    stub = root / "interface.pyi"
    stub.write_text("def run() -> int: ...\n")
    request = root / "request.json"
    request.write_text(
        json.dumps(
            {
                "root": str(root),
                "profile": "callable-python",
                "python_minor": 14,
                "lexical": True,
                "execution": True,
                "files": [
                    {"path": path.name, "digest": digest_file(path), "language": "python"}
                    for path in (source, stub)
                ],
            }
        )
    )
    artifact = extract(
        root,
        SourceJob(
            id="python-callable-selection",
            kind="execution",
            input=str(request),
            helper=str(_binary("source-facts")),
            profile="callable-python",
            schema=str(SCHEMAS / "source-execution.v1.schema.json"),
            witnesses=tuple(
                FileEntry(
                    path=str(path),
                    digest=digest_file(path),
                    size=path.stat().st_size,
                    kind="python",
                )
                for path in (source, stub)
            ),
        ),
        Budget(),
    )
    return root, artifact


@pytest.fixture(scope="module")
def declared_cases(
    native_cases: tuple[Path, tuple[FactArtifact, ...]],
) -> tuple[Path, tuple[FactArtifact, ...]]:
    """Use real rustdoc on the already compiled source, then renumber its local IDs.

    Returns:
        Two source-attributed declaration artifacts with identical API semantics.

    """
    root, _ = native_cases
    source = root / "behavior_dependency.rs"
    output = root / "doc"
    result = execute(
        (
            "rustup",
            "run",
            "nightly-2026-08-18",
            "rustdoc",
            "--crate-name",
            "behavior_dependency",
            "--edition=2024",
            "-Zunstable-options",
            "--output-format=json",
            "--document-private-items",
            "-o",
            str(output),
            str(source),
        ),
        cwd=root,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr.decode()
    document = output / "behavior_dependency.json"
    raw = json.loads(document.read_bytes())
    ids = {int(key): int(key) + 4_000_000 for key in {*raw["index"], *raw["paths"]}}
    shifted = output / "shifted.json"
    shifted.write_text(json.dumps(_rekey(raw, ids)))
    artifacts = tuple(
        extract(
            root,
            SourceJob(
                id="declarations:" + path.stem,
                kind="declarations",
                input=str(path),
                helper=str(_binary("rustdoc")),
                profile="behavior-native",
                schema=str(SCHEMAS / "declaration.v1.schema.json"),
                witnesses=(
                    FileEntry(
                        path=str(source),
                        digest=digest_file(source),
                        size=source.stat().st_size,
                        kind="rust",
                    ),
                ),
            ),
            Budget(),
        )
        for path in (document, shifted)
    )
    return root, artifacts


def test_real_rust_source_join_survives_numbering_and_rejects_wrong_source(
    native_cases: tuple[Path, tuple[FactArtifact, ...]],
    declared_cases: tuple[Path, tuple[FactArtifact, ...]],
    tmp_path: Path,
) -> None:
    """Same names and spans from a changed build cannot satisfy exact byte correspondence."""
    root, native = native_cases
    _, declarations = declared_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(*native, *declarations)))
    reader = corpus.reader()
    artifacts = {
        item.external_id: revision_of(item)
        for item in reader.records("native_artifacts")
        if isinstance(item, NativeArtifact)
    }
    request = CallableRequest(
        logical_id="rust-candidates",
        profile="behavior-native",
        interfaces=tuple(artifacts[item.id] for item in declarations),
        executables=tuple(artifacts[item.id] for item in native),
        files=(str(root / "behavior_dependency.rs"),),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    population = next(corpus.reader().records("callable_populations"))
    assert isinstance(population, CallablePopulation)
    chosen = [item for item in population.candidates if item.symbol.endswith("::choose")]
    assert len(chosen) == len(declarations)
    assert len({item.identity for item in chosen}) == 1
    assert len({item.context for item in chosen}) == len(declarations)
    assert all(item.reachability == "documented_public_route" for item in chosen)
    assert all(len(item.bodies) == 1 for item in chosen)
    assert {body.artifact for item in chosen for body in item.bodies} == {artifacts[native[-1].id]}
    assert all(item.frontier for item in chosen)
    wrong = analyze(reader, evolve(request, executables=(artifacts[native[0].id],)))
    assert all(not item.bodies for item in wrong.candidates if item.symbol.endswith("::choose"))
    with pytest.raises(CorpusError, match="retained-source replay"):
        validate(corpus.reader(), (evolve(population, candidates=()),))
    archive = tmp_path / "portable"
    receipt = export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    assert import_view(restored, archive) == receipt.manifest
    assert analyze(restored.reader("release"), request) == population


def test_python_population_keeps_private_and_nested_exclusions(
    python_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """Source-body candidates retain explicit public-selection and runtime-binding limits."""
    root, artifact = python_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    native = next(corpus.reader().records("native_artifacts"))
    request = CallableRequest(
        logical_id="python-candidates",
        profile=artifact.profile,
        interfaces=(revision_of(native),),
        executables=(revision_of(native),),
        files=("public.py", "interface.pyi"),
    )
    assert not build(corpus, request).reused
    assert build(corpus, request).reused
    population = analyze(corpus.reader(), request)
    reordered = AdmissionReader(
        corpus.reader(),
        {
            "native_facts": [
                REGISTRY["native_facts"].encode(item)
                for item in reversed(tuple(corpus.reader().records("native_facts")))
            ]
        },
        replace=False,
    )
    assert analyze(reordered, request) == population
    assert population.candidates
    assert all(item.frontier for item in population.candidates)
    assert any(item.reachability == "excluded_nested_function" for item in population.candidates)
    assert any(item.reachability == "excluded_private_name" for item in population.candidates)
    assert all(
        item.disposition == "stub_interface" and not item.bodies
        for item in population.candidates
        if item.path.endswith(".pyi")
    )
    assert all(len(item.bodies) == 1 for item in population.candidates if item.path.endswith(".py"))
    without = analyze(corpus.reader(), evolve(request, executables=()))
    assert len(without.candidates) == len(population.candidates)
    assert all(not item.bodies for item in without.candidates)
    assert {item.identity for item in without.candidates} == {
        item.identity for item in population.candidates
    }


def test_witness_origin_version_denominator_and_historical_absence() -> None:
    """Unattributed old receipts stay unknown and malformed new associations are rejected."""
    retained = {"path": "retained", "digest": digest("source"), "size": 4, "kind": "rust"}
    entries = [{"original_path": "/never/open/this.rs", "retained": retained}]
    receipt = {
        "witnesses": [retained],
        "witness_origins": {"model": "library-guides.witness-origins.v1", "entries": entries},
    }
    assert read_origins(receipt) == (("/never/open/this.rs", retained),)
    assert read_origins({"witnesses": [retained]}) == ()
    with pytest.raises(CollectionError, match="denominator"):
        read_origins({**receipt, "witnesses": []})
    with pytest.raises(CollectionError, match="unsupported"):
        read_origins({**receipt, "witness_origins": {"model": "newer", "entries": entries}})


def test_rustdoc_unicode_coordinates_are_checked() -> None:
    """A source character column is never treated as a UTF-8 byte offset."""
    source = RetainedSource(
        revision="source", digest="bytes", data="// é\npub fn é() {}\n".encode()
    )
    expected = len("// é\npub fn é".encode())
    assert source.offset([2, 9]) == expected
    with pytest.raises(CorpusError, match="escapes source"):
        source.offset([2, 100])
