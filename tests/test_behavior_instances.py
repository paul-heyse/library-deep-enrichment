"""Pinned concrete Rust instances, observed substitutions and independent executable controls."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from library_deep_enrichment.analyses.behavior import mir_instances
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
)
from library_deep_enrichment.analyses.call_graph.contracts import CallClosureRequest, CallIndexRequest
from library_deep_enrichment.analyses.compilation_contracts import CompilationPopulation, CompilationRequest
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.compiler_invocation import read as read_invocation
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.behavior import build as build_behavior
from library_deep_enrichment.workflows.compilation import build as build_compilation

from tests.test_call_graph import _index, _selection
from tests.test_native_lanes import SCHEMAS, _binary, _records

SOURCE = """
pub fn width<const N: usize>(_: [u8; N]) -> usize { N }
pub fn choose<const N: usize>(flag: bool, value: u32) -> u32 {
    if N == 3 && flag { value } else { 0 }
}
pub fn three() -> usize { width([0; 3]) }
pub fn five() -> usize { width([0; 5]) }
pub fn select_three(flag: bool, value: u32) -> u32 { choose::<3>(flag, value) }
pub fn select_five(flag: bool, value: u32) -> u32 { choose::<5>(flag, value) }
"""


@pytest.fixture(scope="module")
def instance_cases(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, tuple[FactArtifact, ...]]:
    """Capture complete, instance-limited and zero-depth compiler selections.

    Returns:
        Source-attached generic/concrete catalogs from the actual pinned compiler.

    """
    root = tmp_path_factory.mktemp("concrete-instances")
    source = root / "subject.rs"
    source.write_text(SOURCE)
    sysroot = Path(
        json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=root).stdout)["sysroot"]
    )
    artifacts = tuple(
        _capture(root, source, sysroot, limit, depth) for limit, depth in ((16, 2), (1, 2), (16, 0))
    )
    oracle = root / "oracle.rs"
    oracle.write_text(
        'extern crate instance_subject as s; fn main() { println!("{} {} {} {} {} {}", s::three(), s::five(), s::select_three(false,9), s::select_three(true,9), s::select_five(false,9), s::select_five(true,9)); }'
    )
    compiled = execute(
        (
            str(sysroot / "bin/rustc"),
            str(oracle),
            "--extern",
            f"instance_subject={root}/libinstance_subject.rlib",
            "-o",
            str(root / "oracle"),
        ),
        cwd=root,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stderr
    observed = execute((str(root / "oracle"),), cwd=root, timeout=10)
    assert observed.returncode == 0
    assert list(map(int, observed.stdout.split())) == [3, 5, 0, 9, 0, 0]
    return root, artifacts


def _capture(root: Path, source: Path, sysroot: Path, limit: int, depth: int) -> FactArtifact:
    output = root / f"frames-{limit}-{depth}"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("LDE_MIR_CONTEXT", "concrete-instance-controls")
        patch.setenv("LDE_MIR_BEHAVIOR", "1")
        patch.setenv("LDE_MIR_INSTANCES", str(limit))
        patch.setenv("LDE_MIR_INSTANCE_DEPTH", str(depth))
        patch.setenv("LDE_MIR_OUTPUT", str(output))
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        result = execute(
            (
                str(_binary("mir-facts")),
                str(sysroot / "bin/rustc"),
                "--crate-name",
                "instance_subject",
                "--crate-type=lib",
                "--edition=2024",
                str(source),
                "-o",
                str(root / "libinstance_subject.rlib"),
            ),
            cwd=root,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    invocation_path = next(output.glob("*.invocation.json"))
    invocation = read_invocation(json.loads(invocation_path.read_bytes()))
    assert invocation.execution is not None
    assert invocation.execution.instance_options is not None
    assert invocation.execution.instance_options.max_instances == limit
    assert invocation.execution.instance_options.max_depth == depth
    return extract(
        root,
        SourceJob(
            id=f"instances-{limit}-{depth}",
            kind="mir_instances",
            input=str(next(output.glob("*.frames"))),
            helper=str(_binary("mir-facts")),
            profile="behavior-instances",
            schema=str(SCHEMAS / "mir-instances.v1.schema.json"),
            witnesses=tuple(
                FileEntry(
                    path=str(path), size=path.stat().st_size, digest=digest_file(path), kind=kind
                )
                for path, kind in ((source, "rust"), (invocation_path, "compiler_invocation"))
            ),
        ),
        Budget(),
    )


def test_concrete_instances_preserve_const_guards_and_distinct_bindings(
    instance_cases: tuple[Path, tuple[FactArtifact, ...]], tmp_path: Path
) -> None:
    """One generic implementation produces different evaluated instance relations without overrides."""
    root, artifacts = instance_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts[:1]))
    _check_compilation(corpus)
    index = _index(
        corpus,
        CallIndexRequest(
            logical_id="instances",
            profile="behavior-instances",
            artifacts=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
        ),
    )
    selected = tuple(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact)
        and item.kind == "mir_owner"
        and item.symbol.endswith(("::three", "::five", "::select_three", "::select_five"))
    )
    selection, behavior = _selection(
        corpus,
        CallClosureRequest(
            logical_id="instance-roots",
            profile="behavior-instances",
            index=revision_of(index),
            roots=tuple(sorted(map(revision_of, selected))),
        ),
    )
    assert len(selection.helpers) == len(selected)
    assert {call.state for call in selection.calls} == {"selected_concrete_instance"}
    build_behavior(corpus, behavior)
    _assert_results(corpus, behavior, selected)
    portable = tmp_path / "portable"
    export_view(corpus.reader(), portable)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, portable, head="analysis")
    _assert_results(restored, behavior, selected)
    assert build_behavior(restored, behavior).reused


def _check_compilation(corpus: Corpus) -> None:
    request = CompilationRequest(
        logical_id="concrete-unit-context",
        profile="behavior-instances",
        executables=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
    )
    build_compilation(corpus, request)
    population = corpus.reader().lookup(
        "compilation_populations", "compilation-population:" + request.logical_id, request.profile
    )
    assert isinstance(population, CompilationPopulation)
    assert len(population.units) == 1
    assert population.units[0].invocation
    assert population.units[0].invocation_source


def _assert_results(
    corpus: Corpus, behavior: BehaviorRequest, selected: tuple[NativeFact, ...]
) -> None:
    summaries = {
        item.program: item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary) and item.request == revision_of(behavior)
    }
    programs = {
        item.owner: revision_of(item)
        for item in corpus.reader().records("behavior_programs")
        if isinstance(item, BehaviorProgram) and item.request == revision_of(behavior)
    }
    by_name = {
        owner.symbol.rsplit("::", 1)[-1]: summaries[programs[revision_of(owner)]]
        for owner in selected
    }
    assert {
        by_name[name].terms[clause.result].value
        for name in ("three",)
        for clause in by_name[name].clauses
    } == {"3"}
    assert {
        by_name[name].terms[clause.result].value
        for name in ("five",)
        for clause in by_name[name].clauses
    } == {"5"}
    always_zero = by_name["select_five"]
    assert {always_zero.terms[clause.result].value for clause in always_zero.clauses} == {"0"}
    guarded = by_name["select_three"]
    assert {guarded.terms[clause.result].op for clause in guarded.clauses} == {
        "argument",
        "literal",
    }
    assert all(clause.guards for clause in guarded.clauses)


def test_instance_selection_failure_and_wrong_substitutions_remain_explicit(
    instance_cases: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """Depth/count bounds retain roots, while mismatched same-definition instances are rejected."""
    root, artifacts = instance_cases
    complete, bounded, shallow = (_records(root, artifact) for artifact in artifacts)
    assert sum(row["kind"] == "mir_instance" for row in complete) > 1
    assert sum(row["kind"] == "mir_instance" for row in bounded) == 1
    assert not any(row["kind"] == "mir_instance" for row in shallow)
    assert any(
        use["state"] == "instance_budget_exhausted"
        for row in bounded
        for use in row["execution"]["calls"]
    )
    assert any(
        use["state"] == "depth_budget_exhausted"
        for row in shallow
        for use in row["execution"]["calls"]
    )
    assert {row["symbol"] for row in complete if row["kind"] == "mir_owner"} == {
        row["symbol"] for row in shallow
    }
    bodies = {row["id"]: row for row in complete}
    for row in complete:
        mir_instances.qualify_calls(row, bodies, complete_catalog=True)
    caller = copy.deepcopy(next(row for row in complete if row["symbol"].endswith("::three")))
    wrong = next(row for row in complete if row["symbol"].endswith("width::<5>"))
    caller["execution"]["calls"][0]["instance"] = wrong["id"]
    with pytest.raises(CorpusError, match="substitutions differ"):
        mir_instances.qualify_calls(caller, bodies, complete_catalog=True)
    caller["execution"]["calls"][0]["instance"] = "mir-instance:" + "0" * 64 + ":" + "1" * 64
    with pytest.raises(CorpusError, match="cross-unit identity"):
        mir_instances.validate(caller)
