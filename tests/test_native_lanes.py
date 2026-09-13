"""Executable upstream canaries; build the standalone native workers before this suite."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from attrs import evolve
from library_deep_enrichment.analyses.declarations import neighborhood, nominate
from library_deep_enrichment.authoring import accept, packet
from library_deep_enrichment.collection import CollectionError, load, save
from library_deep_enrichment.evidence_graph import EvidenceGraph
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FactHead
from library_deep_enrichment.knowledge import Profile
from library_deep_enrichment.knowledge_v3 import KnowledgeV3
from library_deep_enrichment.processes import execute
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import canonical_bytes, digest_file
from library_deep_enrichment.worker_runtime import WorkerRequest, run

from tests.support.workers import SCHEMAS, worker_binary

TOOLING = Path(__file__).parents[1]
pytestmark = pytest.mark.native_lanes


def _binary(name: str) -> Path:
    return worker_binary("rustdoc-facts" if name == "rustdoc" else name)


def _records(root: Path, artifact: FactArtifact) -> list[dict]:
    return [
        json.loads(line)
        for shard in artifact.shards
        for line in (root / shard.path).read_bytes().splitlines()
    ]


@pytest.fixture(scope="module")
def rustdoc(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Compile the full private/hidden canary.

    Returns:
        Actual output from the pinned compiler.

    """
    target = tmp_path_factory.mktemp("declaration-build")
    manifest = TOOLING / "tests/fixtures/rust_declarations/Cargo.toml"
    result = execute(
        (
            "cargo",
            "+nightly-2026-08-18",
            "rustdoc",
            "--locked",
            "--manifest-path",
            str(manifest),
            "--target-dir",
            str(target),
            "--lib",
            "--",
            "-Zunstable-options",
            "--output-format=json",
            "--document-private-items",
            "--document-hidden-items",
        ),
        cwd=TOOLING,
        timeout=180,
        max_bytes=1_000_000,
    )
    assert result.returncode == 0, result.stderr.decode()
    return target / "doc/reference_fixture.json"


def _declaration_job(path: Path) -> SourceJob:
    return SourceJob(
        id="fixture",
        kind="declarations",
        input=str(path),
        helper=str(_binary("rustdoc")),
        profile="fixture-doc",
        schema=str(SCHEMAS / "declaration.v1.schema.json"),
    )


def _attach(root: Path, artifact: FactArtifact) -> KnowledgeV3:
    from cattrs import Converter
    from library_deep_enrichment.facts.contracts import SemanticProfile

    receipt = json.loads((root / artifact.receipt_path).read_bytes())
    context = Converter(forbid_extra_keys=True).structure(
        receipt["semantic_profile"], SemanticProfile
    )
    value = KnowledgeV3(
        schema_version="library-guides.knowledge.v3",
        collection_id="native-fixture",
        profiles=(
            Profile(
                id="fixture-doc",
                description="Pinned documentation context, not consumer compilation",
            ),
        ),
        fact_artifacts=(artifact,),
        semantic_profiles=(context,),
        fact_heads=(
            FactHead(
                job=artifact.job,
                profile=artifact.profile,
                request=artifact.id,
                artifact=artifact.id,
                outcome="complete",
            ),
        ),
    )
    save(root, value)
    return value


def test_real_declaration_routes_self_bounds_and_nomination(tmp_path: Path, rustdoc: Path) -> None:
    """Public aliases, Self, typed bounds and uncertainty survive into draft packets."""
    artifact = extract(tmp_path, _declaration_job(rustdoc), Budget())
    _attach(tmp_path, artifact)
    values = _records(tmp_path, artifact)
    constructor = next(row for row in values if row["symbol"].endswith("<impl Schema>::new"))
    assert "reference_fixture::Schema::new" in constructor["public_routes"]
    assert "reference_fixture::Layout::new" in constructor["public_routes"]
    assert constructor["owner_contract"]["impl"]["for"]["resolved_path"]
    assert constructor["type_occurrences"][-1]["self_owner"] is not None
    page = neighborhood(tmp_path, artifact.id, "reference_fixture::Layout", limit=200)
    candidates = page["candidates"]
    assert isinstance(candidates, list)
    assert constructor["id"] in {row["id"] for row in candidates}
    nested = next(row for row in values if row["symbol"].endswith("::try_schema"))
    assert any(row["path"] == "Schema" and not row["direct"] for row in nested["type_occurrences"])
    assert "Iterator<Item = u8>" in next(
        row["signature"] for row in values if row["symbol"].endswith("::opaque")
    )
    assert 'extern "C"' in next(
        row["signature"] for row in values if row["symbol"].endswith("::pointer")
    )
    assert any(row["item"]["inner"].get("impl", {}).get("is_negative") for row in values)
    assert any(row["symbol"].endswith("::documentation_only") for row in values)
    result = nominate(tmp_path, artifact.id, (constructor["id"],), family="construct-schema")
    current = load(tmp_path)
    assert current.reviews == ()
    capabilities = result["capabilities"]
    assert isinstance(capabilities, list)
    request = packet(tmp_path, current, capabilities[0])
    assert request["fact_support"]
    assert request["facet_seeds"]
    claim = current.claims[0]
    fingerprint = EvidenceGraph(tmp_path, current).fingerprint(claim.id)
    accept(
        tmp_path,
        claim.id,
        expected=fingerprint,
        reviewer="native-fixture-test",
        rationale="Constructor declaration and owning impl match the assertion",
    )
    current = load(tmp_path)
    assert isinstance(current, KnowledgeV3)
    changed = evolve(
        current,
        claim_support=tuple(
            evolve(s, kind="behavior") if s.claim == claim.id else s for s in current.claim_support
        ),
    )
    save(tmp_path, changed)
    with pytest.raises(CollectionError, match="cannot establish"):
        accept(
            tmp_path,
            claim.id,
            expected=EvidenceGraph(tmp_path, changed).fingerprint(claim.id),
            reviewer="native-fixture-test",
            rationale="Invalid promotion must fail",
        )


def test_worker_reuse_and_corruption_are_observed(
    tmp_path: Path, rustdoc: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Count real worker launches across warm reuse and corrupt-shard recovery."""
    from library_deep_enrichment import source_pipeline

    calls = []
    original = source_pipeline.run

    def observed(
        request: WorkerRequest, consume: Callable[[dict[str, object]], None]
    ) -> dict[str, object]:
        calls.append(request.request_id)
        return original(request, consume)

    monkeypatch.setattr(source_pipeline, "run", observed)
    job = _declaration_job(rustdoc)
    first = extract(tmp_path, job, Budget())
    assert len(calls) == 1
    assert extract(tmp_path, job, Budget()) == first
    assert len(calls) == 1
    (tmp_path / first.shards[0].path).write_bytes(b"{}\n")
    repaired = extract(tmp_path, job, Budget())
    expected_invocations = 2
    assert len(calls) == expected_invocations
    assert repaired.shards == first.shards


def test_real_ruff_and_pyrefly_keep_scopes_and_uncertainty(tmp_path: Path) -> None:
    """The real upstream engines resolve aliases without erasing dispatch uncertainty."""
    source = tmp_path / "source"
    source.mkdir()
    shutil.copyfile(
        TOOLING / "tests/fixtures/python_semantics/subject.py.fixture", source / "subject.py"
    )
    file_digest = digest_file(source / "subject.py")
    lexical_request = {
        "profile": "python-314",
        "root": str(source),
        "files": [{"path": "subject.py", "digest": file_digest, "language": "python"}],
        "python_minor": 14,
        "lexical": True,
    }
    lexical = _worker(tmp_path, "source-facts", lexical_request)
    events = [row["payload"] for row in lexical if row["payload"]["family"] == "lexical"]
    assert any(row["event"] == "nonlocal" for row in events)
    assert any(row["event"] == "unbound_exception" for row in events)
    assert any(row["target"] == "math.sqrt" for row in events)
    assert any(row["event"] == "unresolved_reference" and row["name"] == "error" for row in events)
    request = {
        "profile": "python-314",
        "root": str(source),
        "files": [{"path": "subject.py", "digest": file_digest, "module": "subject"}],
        "search_paths": ["."],
        "python_version": "3.14",
        "python_platform": "linux",
    }
    typed = _worker(tmp_path, "python-semantics", request)
    calls = [row["payload"] for row in typed if row["payload"]["kind"] == "call"]
    assert any(row["target"] == "math.sqrt" for row in calls)
    assert all(row["dispatch"] == "heuristic" for row in calls)
    assert any(row["target_origin"] == "external_source_not_selected" for row in calls)


def _worker(root: Path, name: str, request: dict) -> list[dict]:
    path = root / f"{name}.json"
    path.write_bytes(canonical_bytes(request))
    rows = []
    receipt = run(
        WorkerRequest(
            argv=(str(_binary(name)), "normalize", str(path), name),
            cwd=root,
            request_id=name,
            input_digest=digest_file(path),
            budget=Budget(),
            isolate=True,
            read_roots=(root, _binary(name).parent),
            write_roots=(root,),
        ),
        rows.append,
    )
    terminal = receipt["terminal"]
    assert isinstance(terminal, dict)
    assert terminal["coverage"]["state"] == "complete"
    return rows


def test_review_equivalence_and_contract_mutation(tmp_path: Path, rustdoc: Path) -> None:
    """Presentation-only bytes refresh; an unsafe obligation reopens the same review."""
    from library_deep_enrichment.declaration_refresh import refresh
    from library_deep_enrichment.qualification import Qualification
    from library_deep_enrichment.revalidation import record

    root = tmp_path / "current"
    first = extract(root, _declaration_job(rustdoc), Budget())
    _attach(root, first)
    item = next(r for r in _records(root, first) if r["symbol"].endswith("<impl Schema>::new"))
    nominate(root, first.id, (item["id"],), family="construction")
    original = load(root)
    claim = original.claims[0]
    accept(
        root,
        claim.id,
        expected=EvidenceGraph(root, original).fingerprint(claim.id),
        reviewer="mutation-fixture",
        rationale="Reviewed full callable and owning impl contract",
    )
    previous = tmp_path / "previous"
    shutil.copytree(root, previous)
    presentation = tmp_path / "reordered.json"
    raw = json.loads(rustdoc.read_bytes())
    presentation.write_text(json.dumps(raw, indent=2, sort_keys=True))
    second = _revision(root, presentation)
    refresh(root, first.id, second.id)
    changed = load(root)
    assert any(
        "review required" in e
        for e in Qualification(root, changed).subject_errors(claim, require_review=True)
    )
    report = record(root, previous)
    reviews = report["reviews"]
    assert isinstance(reviews, list)
    assert all(p["outcome"] == "equivalent" for p in reviews)
    current = load(root)
    assert current.reviews == load(previous).reviews
    assert not Qualification(root, current).subject_errors(claim, require_review=True)
    raw["index"][str(item["local_id"])]["inner"]["function"]["header"]["is_unsafe"] = True
    presentation.write_text(json.dumps(raw))
    third = _revision(root, presentation)
    refresh(root, second.id, third.id)
    report = record(root, previous)
    reviews = report["reviews"]
    assert isinstance(reviews, list)
    assert all(p["outcome"] == "needs_review" for p in reviews)
    changed = load(root)
    assert any(
        "review required" in e
        for e in Qualification(root, changed).subject_errors(claim, require_review=True)
    )


def _revision(root: Path, source: Path) -> FactArtifact:
    from cattrs import Converter
    from library_deep_enrichment.facts.contracts import SemanticProfile

    artifact = extract(root, _declaration_job(source), Budget())
    knowledge = load(root)
    assert isinstance(knowledge, KnowledgeV3)
    context = Converter().structure(
        json.loads((root / artifact.receipt_path).read_bytes())["semantic_profile"], SemanticProfile
    )
    save(
        root,
        evolve(
            knowledge,
            fact_artifacts=(*knowledge.fact_artifacts, artifact),
            semantic_profiles=(*knowledge.semantic_profiles, context),
            fact_heads=(
                FactHead(
                    job=artifact.job,
                    profile=artifact.profile,
                    request=artifact.id,
                    artifact=artifact.id,
                    outcome="complete",
                ),
            ),
        ),
    )
    return artifact


def test_targeted_type_roles_and_expected_fallback(tmp_path: Path) -> None:
    """Union detail survives; a computed fallback cannot impersonate an expected type."""
    code = b"value: int | str = 1\nresult = value\n"
    (tmp_path / "subject.py").write_bytes(code)
    start = code.rfind(b"value")
    request = {
        "profile": "tsp-test",
        "root": str(tmp_path),
        "files": [
            {
                "path": "subject.py",
                "digest": digest_file(tmp_path / "subject.py"),
                "module": "subject",
            }
        ],
        "search_paths": ["."],
        "python_version": "3.14",
        "python_platform": "linux",
        "targeted_queries": [
            {"module": "subject", "start": start, "end": start + 5, "role": role}
            for role in ("computed", "declared", "expected")
        ],
    }
    rows = _worker(tmp_path, "python-semantics", request)
    targeted = {
        r["payload"]["role"]: r["payload"] for r in rows if r["payload"]["kind"] == "targeted"
    }
    assert set(targeted) == {"computed", "declared", "expected"}
    assert targeted["expected"]["expected_fallback"]
    assert not targeted["computed"]["expected_fallback"]
    assert targeted["declared"]["tsp"]["nodes"][0]["category"] == "union"
    assert {
        n["name"] for n in targeted["computed"]["tsp"]["nodes"] if n["category"] == "class"
    } == {"int", "str"}
    assert targeted["computed"]["anchor"] == {
        "start": start,
        "end": start + 5,
        "coordinate": "utf8_bytes",
    }


def test_targeted_declaration_resolves_unicode_name_through_reexport(tmp_path: Path) -> None:
    """Provider resolvers retain the defining source and UTF-16 identifier coordinates."""
    files = {
        "origin": "def café(value: int) -> int:\n    return value\n",
        "bridge": "from origin import café as chosen\n",
        "subject": "from bridge import chosen\nresult = chosen(1)\n",
    }
    for name, code in files.items():
        (tmp_path / (name + ".py")).write_text(code)
    start = files["subject"].rfind("chosen")
    rows = _worker(
        tmp_path,
        "python-semantics",
        {
            "profile": "declaration-control",
            "root": str(tmp_path),
            "files": [
                {
                    "path": name + ".py",
                    "digest": digest_file(tmp_path / (name + ".py")),
                    "module": name,
                }
                for name in files
            ],
            "search_paths": ["."],
            "python_version": "3.14",
            "python_platform": "linux",
            "targeted_queries": [
                {"module": "subject", "start": start, "end": start + 6, "role": "declared"}
            ],
        },
    )
    target = next(row["payload"] for row in rows if row["payload"]["kind"] == "targeted")
    declaration = json.loads(target["tsp"]["raw_tsp"])["declaration"]
    assert declaration["name"] == "café"
    assert declaration["node"]["uri"] == (tmp_path / "origin.py").as_uri()
    assert declaration["node"]["range"] == {
        "start": {"line": 0, "character": 4},
        "end": {"line": 0, "character": 8},
    }
    assert target["tsp"]["location_precision"] == (
        "transaction_source_resolvers_attempted_per_declaration"
    )


def test_source_examples_use_documentation_roles_and_exact_maps(tmp_path: Path) -> None:
    """Ordinary string lookalikes are excluded; prompts and hidden Rust lines retain maps."""
    from library_deep_enrichment.example_discovery import discover
    from library_deep_enrichment.source_snapshots import Acquisition, freeze, source_request

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    (upstream / "example.py").write_bytes(
        '"""Example.\r\n\r\n>>> print("π")\r\nπ\r\n"""\r\ndecoy = """```python\nraise RuntimeError("not documentation")\n```"""\n'.encode()
    )
    (upstream / "lib.rs").write_bytes(
        b"/// Example.\r\n/// ```rust\r\n/// # let value = 1;\r\n/// assert_eq!(value, 1);\r\n/// ```\r\npub fn example() {}\r\n"
    )
    root = tmp_path / "collection"
    snapshot = freeze(
        root,
        upstream,
        Acquisition(
            package="example-control", version="1", origin="fixture", attribution="test authors"
        ),
    )
    request = tmp_path / "syntax.json"
    request.write_bytes(canonical_bytes(source_request(root, snapshot, profile="fixture-doc")))
    artifact = extract(
        root,
        SourceJob(
            id="examples",
            kind="syntax",
            input=str(request),
            helper=str(_binary("source-facts")),
            profile="fixture-doc",
            schema=str(SCHEMAS / "source-facts.v1.schema.json"),
            snapshots=(snapshot.id,),
            inputs=tuple((str(root / e.path), e.digest) for e in snapshot.files),
        ),
        Budget(),
    )
    save(root, evolve(_attach(root, artifact), source_snapshots=(snapshot,)))
    report = discover(root, artifact.id)
    files = report["files"]
    assert isinstance(files, list)
    assert all(item["state"] == "complete" for item in files)
    current = load(root)
    assert isinstance(current, KnowledgeV3)
    python = next(e for e in current.example_discoveries if e.language == "python")
    rust = next(e for e in current.example_discoveries if e.language == "rust")
    assert python.code == 'print("π")\n'
    assert python.status == "parsed"
    assert "let value = 1;" in rust.code
    assert "let value" not in rust.display_code
    assert rust.status == "located"
    assert not any("RuntimeError" in e.code for e in current.example_discoveries)
    assert all(
        segment.host_start is not None
        for e in current.example_discoveries
        for segment in e.anchor.segments
    )
    assert not current.reviews
    assert not current.examples


def test_independent_universe_detects_added_competitor(tmp_path: Path, rustdoc: Path) -> None:
    """An uncited new producer changes a choice even when its positive support is unchanged."""
    import yaml
    from attrs import asdict
    from cattrs import Converter
    from library_deep_enrichment.analyses.universes import enumerate_candidates, policy_errors
    from library_deep_enrichment.facts.contracts import (
        CandidateUniverse,
        SemanticProfile,
        UniverseDependency,
    )

    first = extract(tmp_path, _declaration_job(rustdoc), Budget())
    knowledge = _attach(tmp_path, first)
    item = next(r for r in _records(tmp_path, first) if r["symbol"].endswith("<impl Schema>::new"))
    nominate(tmp_path, first.id, (item["id"],), family="construction")
    knowledge = load(tmp_path)
    assert isinstance(knowledge, KnowledgeV3)
    catalog = extract(tmp_path, evolve(_declaration_job(rustdoc), id="catalog"), Budget())
    universe = CandidateUniverse(
        id="universe:schemas",
        profile="fixture-doc",
        jobs=("catalog",),
        nominal="reference_fixture::Schema",
    )
    dependency = UniverseDependency(subject=knowledge.claims[0].id, universe=universe.id)
    knowledge = evolve(
        knowledge,
        fact_artifacts=(*knowledge.fact_artifacts, catalog),
        fact_heads=(
            *knowledge.fact_heads,
            FactHead(
                job="catalog",
                profile=catalog.profile,
                request=catalog.id,
                artifact=catalog.id,
                outcome="complete",
            ),
        ),
        candidate_universes=(universe,),
        universe_dependencies=(dependency,),
    )
    save(tmp_path, knowledge)
    (tmp_path / "candidate-universes.yaml").write_text(
        yaml.safe_dump({"universes": [asdict(universe)], "dependencies": [asdict(dependency)]})
    )
    assert not policy_errors(tmp_path, knowledge)
    before = EvidenceGraph(tmp_path, knowledge).fingerprint(dependency.subject)
    total = enumerate_candidates(tmp_path, knowledge, universe)["total"]
    assert isinstance(total, int)
    raw = json.loads(rustdoc.read_bytes())
    candidate = next(r for r in _records(tmp_path, first) if r["symbol"].endswith("::try_schema"))
    added = dict(raw["index"][str(candidate["local_id"])])
    added.update(id=999999, name="another_schema")
    raw["index"]["999999"] = added
    raw["index"][str(raw["root"])]["inner"]["module"]["items"].append(999999)
    revision = tmp_path / "new.json"
    revision.write_text(json.dumps(raw))
    new = extract(tmp_path, evolve(_declaration_job(revision), id="catalog"), Budget())
    context = Converter().structure(
        json.loads((tmp_path / new.receipt_path).read_bytes())["semantic_profile"], SemanticProfile
    )
    changed = evolve(
        knowledge,
        fact_artifacts=(*knowledge.fact_artifacts, new),
        fact_heads=(
            knowledge.fact_heads[0],
            evolve(knowledge.fact_heads[1], request=new.id, artifact=new.id),
        ),
        semantic_profiles=(*knowledge.semantic_profiles, context),
    )
    assert enumerate_candidates(tmp_path, changed, universe)["total"] == total + 1
    assert EvidenceGraph(tmp_path, changed).fingerprint(dependency.subject) != before
    assert changed.claim_support == knowledge.claim_support
    assert policy_errors(tmp_path, evolve(changed, candidate_universes=()))


def test_source_capability_preserves_documentation_and_nested_call_ids(tmp_path: Path) -> None:
    """Actual docstrings produce purpose claims; ordinary literals do not gain that authority."""
    from library_deep_enrichment.analyses.source_capabilities import nominate as source_nominate
    from library_deep_enrichment.source_snapshots import Acquisition, freeze, source_request

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    (upstream / "wrapper.py").write_text(
        'def collect(value: int) -> list[int]:\n    """Collect a value into a list.\n\n    Native dispatch is not involved here.\n    """\n    return [value]\n\ndef nested(value):\n    return value.call().finish()\n'
    )
    root = tmp_path / "collection"
    snapshot = freeze(
        root,
        upstream,
        Acquisition(
            package="source-fixture", version="1", origin="fixture", attribution="test authors"
        ),
    )
    request = tmp_path / "syntax.json"
    request.write_bytes(canonical_bytes(source_request(root, snapshot, profile="fixture-doc")))
    artifact = extract(
        root,
        SourceJob(
            id="syntax",
            kind="syntax",
            input=str(request),
            helper=str(_binary("source-facts")),
            profile="fixture-doc",
            schema=str(SCHEMAS / "source-facts.v1.schema.json"),
            snapshots=(snapshot.id,),
            inputs=tuple((str(root / e.path), e.digest) for e in snapshot.files),
        ),
        Budget(),
    )
    save(root, evolve(_attach(root, artifact), source_snapshots=(snapshot,)))
    rows = _records(root, artifact)
    owner = next(
        r for r in rows if r["kind"] == "definition" and r["payload"].get("name") == "collect"
    )
    source_nominate(root, artifact.id, (owner["id"],), "collect-values")
    knowledge = load(root)
    assert not knowledge.reviews
    assert any(c.statement == "Collect a value into a list." for c in knowledge.claims)
    assert "-> list[int]" in knowledge.bindings[0].signature
    request_packet = packet(root, knowledge, knowledge.capabilities[0].id)
    assert request_packet["fact_support"]
    for claim in knowledge.claims:
        accept(
            root,
            claim.id,
            expected=EvidenceGraph(root, load(root)).fingerprint(claim.id),
            reviewer="agent:fixture",
            rationale="Exact source declaration and actual documentation role agree with this claim.",
        )
    current = load(root)
    assert isinstance(current, KnowledgeV3)
    from library_deep_enrichment.facts.support import SupportGraph

    assert SupportGraph(root, evolve(current, claim_support=())).errors(current.claims[-1])


@pytest.fixture
def mir_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, FactArtifact]:
    """Extract a real compiler fixture under a pinned toolchain.

    Returns:
        Collection and source-attached body artifact.

    """
    from library_deep_enrichment.source_snapshots import Acquisition, freeze

    upstream = tmp_path / "upstream"
    upstream.mkdir()
    shutil.copyfile(TOOLING / "tests/fixtures/mir_control.rs.fixture", upstream / "lib.rs")
    root = tmp_path / "collection"
    snapshot = freeze(
        root,
        upstream,
        Acquisition(
            package="mir-control", version="1", origin="fixture", attribution="test authors"
        ),
    )
    output = tmp_path / "units"
    monkeypatch.setenv("LDE_MIR_OUTPUT", str(output))
    monkeypatch.setenv("LDE_MIR_CONTEXT", "compiler-control")
    monkeypatch.delenv("LDE_MIR_PACKAGES", raising=False)
    toolchain = json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=tmp_path).stdout)
    result = execute(
        (
            str(_binary("mir-facts")),
            str(Path(toolchain["sysroot"]) / "bin/rustc"),
            "--crate-type",
            "lib",
            "--crate-name",
            "mir_control",
            "--edition=2024",
            "--emit=metadata",
            "-o",
            str(tmp_path / "fixture.rmeta"),
            str(root / snapshot.files[0].path),
        ),
        cwd=tmp_path,
    )
    assert result.returncode == 0, result.stderr.decode()
    raw = tuple(output.glob("*.frames"))
    assert len(raw) == 1
    artifact = extract(
        root,
        SourceJob(
            id="mir-control",
            kind="mir",
            input=str(raw[0]),
            helper=str(_binary("mir-facts")),
            profile="fixture-doc",
            schema=str(SCHEMAS / "mir.v1.schema.json"),
            snapshots=(snapshot.id,),
        ),
        Budget(),
    )
    save(root, evolve(_attach(root, artifact), source_snapshots=(snapshot,)))
    return root, artifact


def test_mir_real_dispatch_and_derived_input_closure(
    mir_fixture: tuple[Path, FactArtifact],
) -> None:
    """Compiler item identity differs from generic/dynamic/indirect resolution and body closure."""
    from library_deep_enrichment.analyses.pipeline import derive
    from library_deep_enrichment.facts.support import SupportGraph
    from library_deep_enrichment.scope import facts_scope

    root, artifact = mir_fixture
    rows = {r["symbol"].split("::")[-1]: r for r in _records(root, artifact)}

    def call(name: str) -> dict:
        return next(e for e in rows[name]["payload"]["exits"] if e["kind"] == "call")

    assert call("direct")["dispatch"] == "compiler_resolved_item"
    assert rows["identity"]["id"].endswith(call("direct")["instance"]["local_definition"])
    assert call("generic")["instance"]["kind"] == "unresolved"
    assert call("indirect")["instance"]["kind"] == "unresolved"
    assert call("dynamic")["instance"]["kind"] == "virtual"
    report = derive(
        root, artifact.id, (rows["identity"]["id"], rows["direct"]["id"]), job="fixture-analysis"
    )
    current = load(root)
    assert isinstance(current, KnowledgeV3)
    derived = next(a for a in current.fact_artifacts if a.id == report["artifact"])
    assert {d.record for d in derived.dependencies} == {
        rows["identity"]["id"],
        rows["direct"]["id"],
    }
    assert all(r["analysis"]["absence"]["holds"] for r in _records(root, derived))
    portable = root.parent / "portable"
    facts_scope(root, (derived.id,), portable)
    assert SupportGraph(portable, load(portable)).artifact(derived.id)
    save(
        root,
        evolve(
            current,
            fact_heads=tuple(
                evolve(h, outcome="failed", artifact=None) if h.job == artifact.job else h
                for h in current.fact_heads
            ),
        ),
    )
    with pytest.raises(CollectionError, match="current requested head"):
        SupportGraph(root, load(root)).artifact(derived.id)


def test_trait_checklist_and_nested_composition(tmp_path: Path, rustdoc: Path) -> None:
    """Required, provided and associated defaults remain separate; wrappers stay candidates."""
    from library_deep_enrichment.analyses.contracts import composition, extension_contract

    artifact = extract(tmp_path, _declaration_job(rustdoc), Budget())
    _attach(tmp_path, artifact)
    rows = {r["symbol"]: r for r in _records(tmp_path, artifact)}
    trait = next(
        r for r in rows.values() if r["kind"] == "trait" and r["symbol"].endswith("::Consumer")
    )
    result = extension_contract(tmp_path, artifact.id, trait["id"])
    members = result["members"]
    assert isinstance(members, list)
    requirements = {
        r["symbol"].split("::")[-1]: r["requirement"] for r in members if r["role"] == "requirement"
    }
    assert requirements == {
        "Output": "required",
        "LIMIT": "default",
        "consume": "required",
        "description": "provided_body",
    }
    producer = next(r for r in rows.values() if r["symbol"].endswith("::try_schema"))
    consumer = next(r for r in rows.values() if r["symbol"].endswith("::asynchronously"))
    candidate = composition(tmp_path, artifact.id, producer["id"], consumer["id"])
    connections = candidate["connections"]
    assert isinstance(connections, list)
    assert any(
        not c["producer_role"]["direct"] and c["consumer_role"]["direct"] for c in connections
    )
    assert candidate["state"] == "candidate"


def test_derived_warm_reuse_executes_no_analysis(
    mir_fixture: tuple[Path, FactArtifact], monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unchanged derived request verifies bytes and skips the actual analysis passes."""
    from library_deep_enrichment.analyses import pipeline

    root, artifact = mir_fixture
    row = next(r for r in _records(root, artifact) if r["symbol"].endswith("::identity"))
    first = pipeline.derive(root, artifact.id, (row["id"],), job="reuse-control")

    def unexpected(_records: tuple[dict, ...]) -> list[dict]:
        message = "warm analysis was executed"
        raise AssertionError(message)

    monkeypatch.setattr(pipeline, "_results", unexpected)
    second = pipeline.derive(root, artifact.id, (row["id"],), job="reuse-control")
    assert first["artifact"] == second["artifact"]
    assert second["analysis_reused"]
