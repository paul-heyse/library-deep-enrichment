"""Real compiler shims, Rust-call ABI and independently executed closure/drop controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from attrs import evolve

from library_deep_enrichment.analyses.behavior import mir_lifecycle
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
    Outcome,
)
from library_deep_enrichment.analyses.behavior.witness_checks import CheckPolicy, compare
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    Cell,
    Input,
    Observation,
    Verdict,
)
from library_deep_enrichment.analyses.call_graph.contracts import (
    CallClosureRequest,
    CallIndexRequest,
    LifecycleClosure,
)
from library_deep_enrichment.collection import CollectionError
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.compiler_invocation import read as read_invocation
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.facts.mir_sources import witnesses
from library_deep_enrichment.facts.protocol import Frames
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.behavior import build
from library_deep_enrichment.workflows.call_graph import build as build_calls
from tests.test_behavior_callables import _summaries
from tests.test_call_graph import _index
from tests.test_native_lanes import SCHEMAS, _binary, _records

SOURCE = """
pub fn invoke<F: FnOnce(u8)->u8>(f: F, x: u8)->u8 { f(x) }
pub fn invoke_zero<F: FnOnce()->u8>(f: F)->u8 { f() }
pub fn invoke_two<F: FnOnce(u8,u8)->u8>(f: F, x:u8, y:u8)->u8 { f(x,y) }
pub fn owned(flag:bool,x:u8)->u8 { let f=move |v| if flag {v}else{0}; invoke(f,x) }
pub fn borrowed(flag:&bool,x:u8)->u8 { let f=|v| if *flag {v}else{0}; invoke(f,x) }
pub fn borrowed_wrapper(flag:bool,x:u8)->u8 { borrowed(&flag,x) }
pub fn zero(flag:bool,x:u8)->u8 { invoke_zero(move || if flag {x}else{0}) }
pub fn two(flag:bool,x:u8)->u8 { invoke_two(move |a,b| if flag {a}else{b},x,0) }
pub struct Token(pub u8);
impl Drop for Token { fn drop(&mut self) { self.0=0; } }
pub fn released(x:u8)->u8 { let token=Token(x); let value=token.0; drop(token); value }
"""
OPERATIONS = ("owned", "borrowed_wrapper", "zero", "two")
VALUES = (0, 1, 17, 127, 255)
ABSENT_ROOT = "definition:" + "0" * 16 + ":" + "0" * 32 + ":" + "0" * 32


@pytest.fixture(scope="module")
def lifecycle_cases(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, FactArtifact]:
    """Capture exact call/drop identities and execute an ordinary compiler oracle.

    Returns:
        A complete original native artifact and the independent runtime observations.

    """
    root = tmp_path_factory.mktemp("rust-lifecycle")
    source = root / "subject.rs"
    source.write_text(SOURCE)
    sysroot = Path(
        json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=root).stdout)["sysroot"]
    )
    output = root / "frames"
    with pytest.MonkeyPatch.context() as patch:
        for name, value in {
            "CONTEXT": "closure-lifecycle-controls",
            "BEHAVIOR": "1",
            "INSTANCES": "64",
            "INSTANCE_DEPTH": "5",
            "OUTPUT": str(output),
            "CALLABLES": "1",
            "LIFECYCLE": "1",
        }.items():
            patch.setenv("LDE_MIR_" + name, value)
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        result = execute(
            (
                str(_binary("mir-facts")),
                str(sysroot / "bin/rustc"),
                "--crate-name",
                "lifecycle_subject",
                "--crate-type=lib",
                "--edition=2024",
                str(source),
                "-o",
                str(root / "libwrapped_subject.rlib"),
            ),
            cwd=root,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    invocation_path = next(output.glob("*.invocation.json"))
    invocation = read_invocation(json.loads(invocation_path.read_bytes()))
    assert invocation.execution is not None
    assert invocation.execution.instance_options is not None
    assert invocation.execution.instance_options.lifecycle_uses
    artifact = extract(
        root,
        SourceJob(
            id="lifecycle-controls",
            kind="mir_lifecycle",
            input=str(next(output.glob("*.frames"))),
            helper=str(_binary("mir-facts")),
            profile="behavior-lifecycle",
            schema=str(SCHEMAS / "mir-lifecycle.v1.schema.json"),
            witnesses=(
                *witnesses(next(output.glob("*.frames")), Budget()),
                FileEntry(
                    path=str(invocation_path),
                    size=invocation_path.stat().st_size,
                    digest=digest_file(invocation_path),
                    kind="compiler_invocation",
                ),
            ),
        ),
        Budget(),
    )
    oracle = root / "oracle.rs"
    oracle.write_text(
        'extern crate lifecycle_subject as s; fn main() { for flag in [false,true] { for x in [0,1,17,127,255] { println!("{} {} {} {} {}",s::owned(flag,x),s::borrowed_wrapper(flag,x),s::zero(flag,x),s::two(flag,x),s::released(x)); } } }'
    )
    compiled = execute(
        (
            str(sysroot / "bin/rustc"),
            str(source),
            "--crate-name",
            "lifecycle_subject",
            "--crate-type=lib",
            "--edition=2024",
            "-o",
            str(root / "liboracle_subject.rlib"),
        ),
        cwd=root,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stderr
    compiled = execute(
        (
            str(sysroot / "bin/rustc"),
            str(oracle),
            "--extern",
            f"lifecycle_subject={root}/liboracle_subject.rlib",
            "-o",
            str(root / "oracle"),
        ),
        cwd=root,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stderr
    observed = execute((str(root / "oracle"),), cwd=root, timeout=10)
    assert observed.returncode == 0, observed.stderr
    results = [list(map(int, line.split())) for line in observed.stdout.splitlines()]
    assert results == [
        [x if flag else 0] * len(OPERATIONS) + [x] for flag in (False, True) for x in VALUES
    ]
    (root / "oracle-results.json").write_text(json.dumps(results))
    return root, artifact


def test_rust_call_spreading_and_drop_helpers_are_source_backed(
    lifecycle_cases: tuple[Path, FactArtifact],
    tmp_path: Path,
) -> None:
    """Automatic closure/drop selection composes correct scalar outputs and preserves replay."""
    root, artifact = lifecycle_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    index_request = CallIndexRequest(
        logical_id="lifecycle-catalog",
        profile=artifact.profile,
        artifacts=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
    )
    index = _index(corpus, index_request)
    owners = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact)
        and item.kind == "mir_owner"
        and item.symbol in {"lifecycle_subject::" + name for name in (*OPERATIONS, "released")}
    )
    request = CallClosureRequest(
        logical_id="lifecycle-roots",
        profile=artifact.profile,
        index=revision_of(index),
        roots=tuple(map(revision_of, owners)),
    )
    build_calls(corpus, request)
    selection = next(
        item
        for item in corpus.reader().records("lifecycle_closures")
        if isinstance(item, LifecycleClosure)
    )
    assert selection.drops
    assert all(item.state == "selected_concrete_instance" for item in selection.drops)
    behavior = corpus.reader().get("behavior_requests", selection.behavior)
    assert isinstance(behavior, BehaviorRequest)
    build(corpus, behavior)
    summaries = _summaries(corpus, behavior)
    _check_closure_results(corpus, root, summaries)
    released = summaries["lifecycle_subject::released"]
    assert all([e.kind for e in c.effects].count("drop_enter") == 1 for c in released.clauses)
    assert all([e.kind for e in c.effects].count("drop_return") == 1 for c in released.clauses)
    assert any(f.code == "may_alias_write" for f in released.frontier)
    portable = tmp_path / "portable"
    export_view(corpus.reader(), portable)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, portable, head="analysis")
    assert build_calls(restored, index_request).reused
    assert build_calls(restored, request).reused
    assert build(restored, behavior).reused
    assert _summaries(restored, behavior) == summaries


def _check_closure_results(
    corpus: Corpus, root: Path, summaries: dict[str, BehaviorSummary]
) -> None:
    results = json.loads((root / "oracle-results.json").read_bytes())
    for operation_index, name in enumerate(OPERATIONS):
        summary = summaries["lifecycle_subject::" + name]
        program = corpus.reader().get("behavior_programs", summary.program)
        assert isinstance(program, BehaviorProgram)
        assert summary.model == "guarded-executable-transfer.v3"
        assert {summary.terms[c.result].op for c in summary.clauses} == {"argument", "literal"}
        assert not any(
            effect.kind == "unknown_call" for c in summary.clauses for effect in c.effects
        )
        for case, (flag, value) in enumerate(
            (flag, value) for flag in (False, True) for value in VALUES
        ):
            observation = Observation(
                case=str(case),
                summary=revision_of(summary),
                values=(
                    Cell(kind="bool", scalar=str(flag).lower()),
                    Cell(kind="int", scalar=str(value)),
                    Cell(kind="int", scalar=str(results[case][operation_index])),
                ),
                inputs=(
                    Input(parameter=program.parameters[0], value=0),
                    Input(parameter=program.parameters[1], value=1),
                ),
                result=2,
                outcome=Outcome.RETURN,
            )
            assert compare(program, summary, observation, CheckPolicy()).verdict == Verdict.MATCHED
            wrong = evolve(
                observation,
                values=(
                    *observation.values[:2],
                    Cell(kind="int", scalar=str(255 - results[case][operation_index])),
                ),
            )
            assert compare(program, summary, wrong, CheckPolicy()).verdict == Verdict.DISAGREEMENT


def test_lifecycle_denominators_reject_missing_drop_and_wrong_rust_call_abi(
    lifecycle_cases: tuple[Path, FactArtifact],
) -> None:
    """A complete native catalog cannot silently omit drop/ABI facts or exchange body targets."""
    root, artifact = lifecycle_cases
    rows = _records(root, artifact)
    bodies = {row["id"]: row for row in rows}
    for row in rows:
        mir_lifecycle.qualify(row, bodies, complete_catalog=True)
    raw = copy.deepcopy(next(row for row in rows if row["lifecycle"]["drops"]))
    raw["lifecycle"]["drops"].clear()
    with pytest.raises(CorpusError, match="denominator"):
        mir_lifecycle.validate(raw)
    raw = copy.deepcopy(next(row for row in rows if row["lifecycle"]["spread_arg"] is not None))
    raw["lifecycle"]["spread_arg"] = 1
    with pytest.raises(CorpusError, match="spread argument"):
        mir_lifecycle.validate(raw)
    raw = copy.deepcopy(next(row for row in rows if row["lifecycle"]["call_abis"]))
    raw["lifecycle"]["call_abis"].clear()
    with pytest.raises(CorpusError, match="ABI denominator"):
        mir_lifecycle.validate(raw)
    raw = copy.deepcopy(
        next(
            row
            for row in rows
            if any(s["abi"] == "RustCall" for s in row["lifecycle"]["call_abis"])
        )
    )
    signature = next(s for s in raw["lifecycle"]["call_abis"] if s["abi"] == "RustCall")
    signature["inputs"][-1]["args"].append(signature["output"])
    with pytest.raises(CorpusError, match="Rust-call"):
        mir_lifecycle.validate(raw)
    raw = copy.deepcopy(next(row for row in rows if row["lifecycle"]["spread_arg"] is not None))
    next(s for s in raw["lifecycle"]["call_abis"] if s["abi"] == "RustCall")["abi"] = "Rust"
    with pytest.raises(CorpusError, match="expanded body argument shapes"):
        mir_lifecycle.qualify(raw, bodies, complete_catalog=True)


def test_concrete_demand_preserves_generic_denominator_and_rejects_wrong_roots(
    lifecycle_cases: tuple[Path, FactArtifact],
) -> None:
    """Demand exact definitions without spending instance budgets on unrelated owners."""
    root, artifact = lifecycle_cases
    original = _records(root, artifact)
    definition = next(
        row["behavior"]["definition"]
        for row in original
        if row["symbol"] == "lifecycle_subject::released"
    )
    rows, invocation = _demand_capture(root, definition)
    observed = read_invocation(invocation)
    assert observed.execution is not None
    assert observed.execution.instance_options is not None
    assert observed.execution.instance_options.definition_roots == (definition,)
    assert {row["behavior"]["definition"] for row in rows if row["kind"] == "mir_owner"} == {
        row["behavior"]["definition"] for row in original if row["kind"] == "mir_owner"
    }
    assert any(
        use["state"] == "outside_requested_root_closure"
        for row in rows
        for use in row["execution"]["calls"]
    )
    assert sum(row["kind"] == "mir_instance" for row in rows) < sum(
        row["kind"] == "mir_instance" for row in original
    )
    assert any(
        row["kind"] == "mir_instance"
        and row["symbol"].startswith("std::ptr::drop_glue::<lifecycle_subject::Token>")
        for row in rows
    )
    bodies = {row["id"]: row for row in rows}
    for row in rows:
        mir_lifecycle.qualify(row, bodies, complete_catalog=True)
    mutated = copy.deepcopy(invocation)
    mutated["invocation"]["execution_context"]["instance_options"]["definition_roots"] = [
        definition[:-1] + ("a" if definition[-1] != "a" else "b")
    ]
    with pytest.raises(CollectionError, match="identity"):
        read_invocation(mutated)
    _demand_capture(root, ABSENT_ROOT)


def _demand_capture(root: Path, definition: str) -> tuple[list[dict], dict]:
    output = root / ("demand-" + definition.split(":")[1])
    sysroot = Path(
        json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=root).stdout)["sysroot"]
    )
    with pytest.MonkeyPatch.context() as patch:
        for name, value in {
            "CONTEXT": "exact-definition-demand",
            "BEHAVIOR": "1",
            "INSTANCES": "8",
            "INSTANCE_DEPTH": "5",
            "OUTPUT": str(output),
            "CALLABLES": "1",
            "LIFECYCLE": "1",
            "INSTANCE_ROOTS": json.dumps([definition]),
        }.items():
            patch.setenv("LDE_MIR_" + name, value)
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        result = execute(
            (
                str(_binary("mir-facts")),
                str(sysroot / "bin/rustc"),
                "--crate-name",
                "lifecycle_subject",
                "--crate-type=lib",
                "--edition=2024",
                str(root / "subject.rs"),
                "-o",
                str(root / "libwrapped_subject.rlib"),
            ),
            cwd=root,
            timeout=120,
        )
    if definition == ABSENT_ROOT:
        assert result.returncode != 0
        assert b"requested instance root is absent" in result.stderr
        assert not tuple(output.glob("*.frames"))
        return [], {}
    assert result.returncode == 0, result.stderr
    invocation = json.loads(next(output.glob("*.invocation.json")).read_bytes())
    read_invocation(invocation)
    data = next(output.glob("*.frames")).read_bytes()
    header = json.loads(data[4 : 4 + int.from_bytes(data[:4], "big")])["header"]
    parser = Frames(Budget(), header["request_id"], header["input_digest"])
    rows = list(parser.feed(data))
    parser.finish()
    return rows, invocation
