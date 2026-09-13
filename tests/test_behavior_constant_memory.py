"""Actual compiler constant tables, physical layouts, identity controls and portable admission."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from library_deep_enrichment.analyses.behavior import mir_memory
from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.compiler_invocation import read as read_invocation
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.facts.mir_sources import witnesses
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.behavior import build
from tests.test_behavior_callables import _summaries
from tests.test_native_lanes import SCHEMAS, _binary, _records

EXPECTED_STATIC_COUNT = 2

SOURCE = """
#[repr(C)]
pub struct Entry<T> { pub name: &'static [u8], pub tag: T, pub callback: fn(u8)->u8 }
pub fn identity(x:u8)->u8 {x}
pub fn complement(x:u8)->u8 {!x}
pub const ENTRIES: &[Entry<u16>] = &[
    Entry{name:b"first",tag:257,callback:identity},
    Entry{name:b"second",tag:513,callback:complement},
];
pub fn entries()-> &'static [Entry<u16>] { ENTRIES }
pub fn niche(x:bool)->Option<&'static [Entry<u16>]> { if x {Some(ENTRIES)} else {None} }
pub static LEFT: [u8;2] = [3,4];
pub static RIGHT: [u8;2] = [3,4];
pub fn aliases()->(&'static [u8;2], &'static [u8;2], &'static [u8;2]) { (&LEFT,&LEFT,&RIGHT) }
pub const LARGE: &[u8] = &[0;1_048_577];
pub fn large()-> &'static [u8] {LARGE}
"""
ORACLE = """
extern crate memory_subject as s;
fn main() {
    println!("{} {} {} {} {}",std::mem::size_of::<s::Entry<u16>>(),std::mem::align_of::<s::Entry<u16>>(),std::mem::offset_of!(s::Entry<u16>,name),std::mem::offset_of!(s::Entry<u16>,tag),std::mem::offset_of!(s::Entry<u16>,callback));
    for entry in s::entries() {
        println!("{} {} {} {} {} {}",std::str::from_utf8(entry.name).unwrap(),entry.tag,(entry.callback)(0),(entry.callback)(1),(entry.callback)(17),(entry.callback)(255));
    }
    let (a,b,c)=s::aliases(); println!("{} {}",std::ptr::eq(a,b),std::ptr::eq(a,c));
}
"""


@pytest.fixture(scope="module")
def memory_cases(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, FactArtifact]:
    """Capture an actual compiler catalog and a separately compiled consumer.

    Returns:
        The retained artifact root and exact native artifact.

    """
    root = tmp_path_factory.mktemp("constant-memory")
    source = root / "subject.rs"
    source.write_text(SOURCE)
    binary = _binary("mir-facts")
    sysroot = Path(json.loads(execute((str(binary), "toolchain"), cwd=root).stdout)["sysroot"])
    compiler = str(sysroot / "bin/rustc")
    output = root / "frames"
    arguments = (
        "--crate-name",
        "memory_subject",
        "--crate-type=lib",
        "--edition=2024",
        str(source),
    )
    with pytest.MonkeyPatch.context() as patch:
        for key, value in {
            "CONTEXT": "constant-memory-controls",
            "BEHAVIOR": "1",
            "INSTANCES": "16",
            "INSTANCE_DEPTH": "3",
            "OUTPUT": str(output),
            "CALLABLES": "1",
            "LIFECYCLE": "1",
            "MEMORY": "1",
        }.items():
            patch.setenv("LDE_MIR_" + key, value)
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        patch.delenv("LDE_MIR_INSTANCE_ROOTS", raising=False)
        result = execute(
            (str(binary), compiler, *arguments, "-o", str(root / "libwrapped.rlib")),
            cwd=root,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    invocation = next(output.glob("*.invocation.json"))
    parsed = read_invocation(json.loads(invocation.read_bytes()))
    assert parsed.execution is not None
    assert parsed.execution.instance_options is not None
    assert parsed.execution.instance_options.constant_memory
    frames = next(output.glob("*.frames"))
    artifact = extract(
        root,
        SourceJob(
            id="memory-controls",
            kind="mir_memory",
            input=str(frames),
            helper=str(binary),
            profile="constant-memory",
            schema=str(SCHEMAS / "mir-memory.v1.schema.json"),
            witnesses=(
                *witnesses(frames, Budget()),
                FileEntry(
                    path=str(invocation),
                    size=invocation.stat().st_size,
                    digest=digest_file(invocation),
                    kind="compiler_invocation",
                ),
            ),
        ),
        Budget(),
    )
    compiled = execute(
        (compiler, *arguments, "-o", str(root / "libordinary.rlib")), cwd=root, timeout=120
    )
    assert compiled.returncode == 0, compiled.stderr
    oracle = root / "oracle.rs"
    oracle.write_text(ORACLE)
    compiled = execute(
        (
            compiler,
            str(oracle),
            "--extern",
            f"memory_subject={root}/libordinary.rlib",
            "-o",
            str(root / "oracle"),
        ),
        cwd=root,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stderr
    observed = execute((str(root / "oracle"),), cwd=root, timeout=10)
    assert observed.returncode == 0, observed.stderr
    (root / "observed.txt").write_bytes(observed.stdout)
    return root, artifact


def test_constant_tables_match_independent_layout_and_runtime(
    memory_cases: tuple[Path, FactArtifact],
) -> None:
    """A registration-shaped table retains names, field bytes, callback targets and padding."""
    root, artifact = memory_cases
    rows = _records(root, artifact)
    bodies = {row["id"]: row for row in rows}
    for row in rows:
        mir_memory.qualify(row, bodies, complete_catalog=True)
    raw = next(row for row in rows if row["symbol"] == "memory_subject::entries")
    memory = raw["memory"]
    observed = (root / "observed.txt").read_text().splitlines()
    assert observed[1:] == ["first 257 0 1 17 255", "second 513 255 254 238 0", "true false"]
    entry = next(
        ty
        for ty in memory["types"]
        if ty["definition"] and ty["ty"]["nominal"] == "memory_subject::Entry"
    )
    layout = entry["layout"]
    assert [layout["size"], layout["alignment"], *layout["fields"]["offsets"]] == list(
        map(int, observed[0].split())
    )
    fields = entry["variants"][0]["members"]
    assert [field["name"] for field in fields] == ["name", "tag", "callback"]
    assert memory["types"][fields[1]["ty"]]["ty"]["nominal"] == "U16"
    _table_bytes(raw, layout)
    functions = [node for node in memory["nodes"] if node["kind"] == "function"]
    assert {bodies[node["identity"]["key"]]["symbol"] for node in functions} == {
        "memory_subject::identity",
        "memory_subject::complement",
    }
    assert all(node["selection"]["state"] == "captured" for node in functions)
    niche = next(row for row in rows if row["symbol"] == "memory_subject::niche")
    assert any(
        (ty["layout"] or {}).get("tag", {}).get("encoding") == "niche"
        for ty in niche["memory"]["types"]
        if (ty["layout"] or {}).get("tag")
    )


def _table_bytes(raw: dict, layout: dict) -> None:
    memory = raw["memory"]
    nodes = memory["nodes"]
    root_node = nodes[memory["roots"][0]["allocation"]]
    table = nodes[root_node["pointers"][0]["target"]]
    for index, tag in enumerate((257, 513)):
        offset = index * layout["size"] + layout["fields"]["offsets"][1]
        assert (
            int.from_bytes(
                bytes(table["bytes"][offset : offset + 2]), raw["behavior"]["target"]["endianness"]
            )
            == tag
        )
    names = {
        bytes(node["bytes"])
        for node in nodes
        if node["kind"] == "memory" and not node["pointers"] and None not in node["bytes"]
    }
    assert {b"first", b"second"} <= names
    assert None in table["bytes"]


def test_constant_graph_budgets_aliases_and_rejection_controls(
    memory_cases: tuple[Path, FactArtifact],
) -> None:
    """Incomplete graphs stay explicit and a function from another build cannot be substituted."""
    root, artifact = memory_cases
    rows = _records(root, artifact)
    aliases = next(row for row in rows if row["symbol"] == "memory_subject::aliases")
    statics = [node for node in aliases["memory"]["nodes"] if node["kind"] == "static"]
    assert len({node["definition"] for node in statics}) == len(statics) == EXPECTED_STATIC_COUNT
    assert any("constant_byte_budget" in row["memory"]["frontier"] for row in rows)
    assert all(row["memory"]["retained_bytes"] <= mir_memory.MAX_BYTES for row in rows)
    original = next(row for row in rows if row["symbol"] == "memory_subject::entries")
    raw = copy.deepcopy(original)
    raw["memory"]["roots"].pop()
    with pytest.raises(CorpusError, match="operand denominator"):
        mir_memory.validate(raw)
    raw = copy.deepcopy(original)
    node = next(
        node for node in raw["memory"]["nodes"] if node["kind"] == "memory" and node["pointers"]
    )
    node["pointers"][0]["offset"] = len(node["bytes"])
    with pytest.raises(CorpusError, match="pointer provenance"):
        mir_memory.validate(raw)
    raw = copy.deepcopy(original)
    node = next(node for node in raw["memory"]["nodes"] if node["kind"] == "function")
    node["identity"]["definition"] = node["definition"][:-1] + (
        "a" if node["definition"][-1] != "a" else "b"
    )
    with pytest.raises(CorpusError, match="target identity"):
        mir_memory.validate(raw)
    raw = copy.deepcopy(original)
    raw["memory"]["locals"].pop()
    with pytest.raises(CorpusError, match="local type denominator"):
        mir_memory.validate(raw)
    invocation = json.loads(next((root / "frames").glob("*.invocation.json")).read_bytes())
    invocation["invocation"]["execution_context"]["instance_options"]["constant_memory"] = False
    with pytest.raises(CollectionError, match="explicitly enabled"):
        read_invocation(invocation)


def test_constant_memory_portable_admission_preserves_unknown_semantics(
    memory_cases: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """New memory facts replay through the existing behavior service without assuming binding laws."""
    root, artifact = memory_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact)
        and item.symbol
        in {"memory_subject::identity", "memory_subject::complement", "memory_subject::entries"}
        and item.kind == "mir_owner"
    )
    request = BehaviorRequest(
        logical_id="memory-controls",
        profile=artifact.profile,
        owners=tuple(map(revision_of, owners)),
        artifacts=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
    )
    build(corpus, request)
    summaries = _summaries(corpus, request)
    assert set(summaries) == {item.symbol for item in owners}
    archive = tmp_path / "portable.tar"
    export_view(corpus.reader(), archive)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, archive, head="analysis")
    assert {revision_of(row) for row in restored.reader().records("native_facts")} == {
        revision_of(row) for row in corpus.reader().records("native_facts")
    }
    assert build(restored, request).reused
