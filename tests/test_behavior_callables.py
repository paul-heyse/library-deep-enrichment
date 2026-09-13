"""Independent compiler controls for callable values, guarded dispatch and open target sets."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from attrs import evolve
from library_deep_enrichment.analyses.behavior import mir_callables
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
    Outcome,
)
from library_deep_enrichment.analyses.behavior.witness_checks import CheckPolicy, compare
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    BehaviorWitnessCheck,
    BehaviorWitnessRequest,
    Cell,
    Input,
    Observation,
    ObservationSet,
    Verdict,
)
from library_deep_enrichment.analyses.call_graph.contracts import (
    CallableClosure,
    CallClosureRequest,
    CallIndexRequest,
)
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import CONVERTER
from library_deep_enrichment.corpus.native_contracts import NativeFact
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.staging import ObservationBuilder
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.facts.compiler_invocation import read as read_invocation
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
from library_deep_enrichment.processes import execute
from library_deep_enrichment.publication.export import export_view, import_view
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import digest_file
from library_deep_enrichment.workflows.behavior import build
from library_deep_enrichment.workflows.behavior_witnesses import build as build_witnesses
from library_deep_enrichment.workflows.call_graph import build as build_calls

from tests.test_call_graph import _index
from tests.test_native_lanes import SCHEMAS, _binary, _records

MINIMUM_COMPOSED_BODIES = 3

SOURCE = """
pub fn identity(x: u8) -> u8 { x }
pub fn invert(x: u8) -> u8 { !x }
pub fn apply(f: fn(u8) -> u8, x: u8) -> u8 { f(x) }
pub fn select(flag: bool, x: u8) -> u8 { apply(if flag { identity } else { invert }, x) }
pub fn relay(flag: bool) -> fn(u8) -> u8 { if flag { identity } else { invert } }
pub fn through_return(flag: bool, x: u8) -> u8 { apply(relay(flag), x) }
pub struct Slot { pub call: fn(u8) -> u8 }
pub fn through_field(flag: bool, x: u8) -> u8 {
    let mut slot = Slot { call: identity };
    if !flag { slot.call = invert; }
    apply(slot.call, x)
}
pub fn pick<const N: u8>(x: u8) -> u8 { if N == 1 { x } else { !x } }
pub fn through_const(flag: bool, x: u8) -> u8 { apply(if flag { pick::<1> } else { pick::<2> }, x) }
pub fn recursive(x: u8) -> u8 { if x == 0 { x } else { apply(recursive, x) } }
"""


@pytest.fixture(scope="module")
def callable_cases(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[Path, tuple[FactArtifact, ...]]:
    """Capture callable item operands and independently execute a finite input grid.

    Returns:
        Complete and zero-depth original compiler artifacts.

    """
    root = tmp_path_factory.mktemp("callable-flow")
    source = root / "subject.rs"
    source.write_text(SOURCE)
    sysroot = Path(
        json.loads(execute((str(_binary("mir-facts")), "toolchain"), cwd=root).stdout)["sysroot"]
    )
    artifacts = tuple(_capture(root, source, sysroot, depth) for depth in (3, 0))
    oracle = root / "oracle.rs"
    oracle.write_text(
        'extern crate callable_subject as s; fn main() { for flag in [false,true] { for x in [0,1,17,127,255] { println!("{} {} {} {}",s::select(flag,x),s::through_return(flag,x),s::through_field(flag,x),s::through_const(flag,x)); } } }'
    )
    # Compile source with the ordinary compiler, independently of wrapper-generated objects.
    compiled = execute(
        (
            str(sysroot / "bin/rustc"),
            str(source),
            "--crate-name",
            "callable_subject",
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
            f"callable_subject={root}/liboracle_subject.rlib",
            "-o",
            str(root / "oracle"),
        ),
        cwd=root,
        timeout=120,
    )
    assert compiled.returncode == 0, compiled.stderr
    observed = execute((str(root / "oracle"),), cwd=root, timeout=10)
    expected = [
        [x if flag else 255 - x] * 4 for flag in (False, True) for x in (0, 1, 17, 127, 255)
    ]
    assert [list(map(int, line.split())) for line in observed.stdout.splitlines()] == expected
    (root / "oracle-results.json").write_text(json.dumps(expected))
    return root, artifacts


def _capture(root: Path, source: Path, sysroot: Path, depth: int) -> FactArtifact:
    output = root / f"frames-{depth}"
    with pytest.MonkeyPatch.context() as patch:
        for name, value in {
            "CONTEXT": "callable-value-controls",
            "BEHAVIOR": "1",
            "INSTANCES": "32",
            "INSTANCE_DEPTH": str(depth),
            "OUTPUT": str(output),
            "CALLABLES": "1",
        }.items():
            patch.setenv("LDE_MIR_" + name, value)
        patch.delenv("LDE_MIR_PACKAGES", raising=False)
        result = execute(
            (
                str(_binary("mir-facts")),
                str(sysroot / "bin/rustc"),
                "--crate-name",
                "callable_subject",
                "--crate-type=lib",
                "--edition=2024",
                str(source),
                "-o",
                str(root / "libcallable_subject.rlib"),
            ),
            cwd=root,
            timeout=120,
        )
        assert result.returncode == 0, result.stderr
    invocation_path = next(output.glob("*.invocation.json"))
    invocation = read_invocation(json.loads(invocation_path.read_bytes()))
    assert invocation.execution is not None
    assert invocation.execution.schema == mir_callables.SCHEMA
    assert invocation.execution.instance_options is not None
    assert invocation.execution.instance_options.callable_references
    return extract(
        root,
        SourceJob(
            id=f"callables-{depth}",
            kind="mir_callables",
            input=str(next(output.glob("*.frames"))),
            helper=str(_binary("mir-facts")),
            profile="behavior-callables",
            schema=str(SCHEMAS / "mir-callables.v1.schema.json"),
            witnesses=tuple(
                FileEntry(
                    path=str(path), size=path.stat().st_size, digest=digest_file(path), kind=kind
                )
                for path, kind in ((source, "rust"), (invocation_path, "compiler_invocation"))
            ),
        ),
        Budget(),
    )


def _summaries(corpus: Corpus, request: BehaviorRequest) -> dict[str, BehaviorSummary]:
    programs = {
        revision_of(item): item
        for item in corpus.reader().records("behavior_programs")
        if isinstance(item, BehaviorProgram) and item.request == revision_of(request)
    }
    return {
        programs[item.program].symbol: item
        for item in corpus.reader().records("behavior_summaries")
        if isinstance(item, BehaviorSummary) and item.request == revision_of(request)
    }


def test_callable_values_compose_across_guards_returns_fields_and_const_instances(
    callable_cases: tuple[Path, tuple[FactArtifact, ...]],
    tmp_path: Path,
) -> None:
    """Derived relations match an ordinary executable and survive admission/archive replay."""
    root, artifacts = callable_cases
    raw = _records(root, artifacts[0])
    bodies = {row["id"]: row for row in raw}
    for row in raw:
        mir_callables.qualify(row, bodies, complete_catalog=True)
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifacts[0],)))
    owners = tuple(
        item for item in corpus.reader().records("native_facts") if isinstance(item, NativeFact)
    )
    request = BehaviorRequest(
        logical_id="callable-value-flow",
        profile="behavior-callables",
        owners=tuple(revision_of(item) for item in owners),
        artifacts=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
    )
    build(corpus, request)
    summaries = _summaries(corpus, request)
    programs = {
        item.symbol: item
        for item in corpus.reader().records("behavior_programs")
        if isinstance(item, BehaviorProgram) and item.request == revision_of(request)
    }
    (tmp_path / "summaries.json").write_text(
        json.dumps(
            {
                name: {
                    "clauses": len(item.clauses),
                    "ops": [item.terms[c.result].op for c in item.clauses],
                    "frontier": [f.code for f in item.frontier],
                }
                for name, item in summaries.items()
            },
            indent=2,
        )
    )
    for name in ("select", "through_return", "through_field", "through_const"):
        summary = summaries["callable_subject::" + name]
        assert summary.model == "guarded-executable-transfer.v2"
        assert {summary.terms[clause.result].op for clause in summary.clauses} == {
            "argument",
            "invert",
        }
        assert all(clause.guards for clause in summary.clauses)
        assert not any(
            effect.kind == "unknown_call" for clause in summary.clauses for effect in clause.effects
        )
        assert len(summary.dependencies) >= MINIMUM_COMPOSED_BODIES
        _check_observations(programs["callable_subject::" + name], summary)
    # An externally supplied pointer has an open target set; recursive dispatch terminates analysis.
    assert any(
        effect.kind == "unknown_call"
        for clause in summaries["callable_subject::apply"].clauses
        for effect in clause.effects
    )

    assert summaries["callable_subject::recursive"].frontier
    portable = tmp_path / "portable"
    export_view(corpus.reader(), portable)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, portable, head="analysis")
    assert build(restored, request).reused
    assert _summaries(restored, request) == summaries
    # Removing a target from the selected body set cannot preserve a false exact result.
    selected = tuple(revision_of(item) for item in owners if "invert" not in item.symbol)
    partial = evolve(request, logical_id="callable-body-unavailable", owners=selected)
    build(corpus, partial)
    incomplete = _summaries(corpus, partial)["callable_subject::select"]
    assert any(
        effect.kind == "unknown_call" for clause in incomplete.clauses for effect in clause.effects
    )


def _check_observations(program: BehaviorProgram, summary: BehaviorSummary) -> None:
    for flag in (False, True):
        for value in (0, 1, 17, 127, 255):
            expected = value if flag else 255 - value
            observation = Observation(
                case=f"{flag}-{value}",
                summary=revision_of(summary),
                values=(
                    Cell(kind="bool", scalar=str(flag).lower()),
                    Cell(kind="int", scalar=str(value)),
                    Cell(kind="int", scalar=str(expected)),
                ),
                inputs=(
                    Input(parameter=program.parameters[0], value=0),
                    Input(parameter=program.parameters[1], value=1),
                ),
                result=2,
                outcome=Outcome.RETURN,
            )
            assert (
                compare(program, summary, observation, CheckPolicy(primitive_unary=True)).verdict
                == Verdict.MATCHED
            )
            wrong = evolve(
                observation,
                values=(*observation.values[:2], Cell(kind="int", scalar=str(255 - expected))),
            )
            assert (
                compare(program, summary, wrong, CheckPolicy(primitive_unary=True)).verdict
                == Verdict.DISAGREEMENT
            )


def test_callable_helper_selection_tracks_references_separately_from_calls(
    callable_cases: tuple[Path, tuple[FactArtifact, ...]],
    tmp_path: Path,
) -> None:
    """A public root automatically selects passed functions and preserves reference budgets."""
    root, artifacts = callable_cases
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=artifacts[:1]))
    index = _index(
        corpus,
        CallIndexRequest(
            logical_id="callable-catalog",
            profile="behavior-callables",
            artifacts=tuple(map(revision_of, corpus.reader().records("native_artifacts"))),
        ),
    )
    owner = next(
        item
        for item in corpus.reader().records("native_facts")
        if isinstance(item, NativeFact)
        and item.kind == "mir_owner"
        and item.symbol == "callable_subject::through_field"
    )
    request = CallClosureRequest(
        logical_id="callable-root",
        profile="behavior-callables",
        index=revision_of(index),
        roots=(revision_of(owner),),
    )
    build_calls(corpus, request)
    selection = next(
        item
        for item in corpus.reader().records("callable_closures")
        if isinstance(item, CallableClosure)
    )
    assert selection.references
    assert {item.role for item in selection.references} >= {"event_value", "callee"}
    assert any(
        item.selection.state == "selected_concrete_instance" for item in selection.references
    )
    behavior = corpus.reader().get("behavior_requests", selection.behavior)
    assert isinstance(behavior, BehaviorRequest)
    build(corpus, behavior)
    summary = _summaries(corpus, behavior)[owner.symbol]
    assert not any(
        effect.kind == "unknown_call" for clause in summary.clauses for effect in clause.effects
    )
    witness = _admit_witnesses(corpus, root, summary)
    portable = tmp_path / "portable"
    export_view(corpus.reader(), portable)
    restored = Corpus(tmp_path / "restored")
    import_view(restored, portable, head="analysis")
    assert build_calls(restored, request).reused
    assert build(restored, behavior).reused
    assert build_witnesses(restored, witness).reused
    assert restored.reader().get("callable_closures", revision_of(selection)) == selection
    bounded = evolve(request, logical_id="callable-depth-zero", max_depth=0)
    build_calls(corpus, bounded)
    selection = next(
        item
        for item in corpus.reader().records("callable_closures")
        if isinstance(item, CallableClosure) and item.request == revision_of(bounded)
    )
    assert not selection.helpers
    assert any(item.selection.state == "depth_budget_exhausted" for item in selection.references)


def _admit_witnesses(
    corpus: Corpus, root: Path, summary: BehaviorSummary
) -> BehaviorWitnessRequest:
    program = corpus.reader().get("behavior_programs", summary.program)
    assert isinstance(program, BehaviorProgram)
    outputs = json.loads((root / "oracle-results.json").read_text())
    cases = tuple(
        Observation(
            case=f"{flag}-{value}-{mutated}",
            summary=revision_of(summary),
            values=(
                Cell(kind="bool", scalar=str(flag).lower()),
                Cell(kind="int", scalar=str(value)),
                Cell(
                    kind="int",
                    scalar=str(255 - outputs[index][2] if mutated else outputs[index][2]),
                ),
            ),
            inputs=(
                Input(parameter=program.parameters[0], value=0),
                Input(parameter=program.parameters[1], value=1),
            ),
            result=2,
            outcome=Outcome.RETURN,
        )
        for index, (flag, value) in enumerate(
            (flag, value) for flag in (False, True) for value in (0, 1, 17, 127, 255)
        )
        for mutated in (False, True)
    )
    builder = ObservationBuilder("ordinary-rust-callable-oracle.v1")
    raw = builder.observe(
        "callable-witness",
        {
            "observations": CONVERTER.unstructure(
                ObservationSet(
                    version="library-guides.behavior-observations.v4",
                    observations=cases,
                    seed=0,
                    generation="10 ordinary-executable observations plus 10 explicitly labeled output mutations",
                )
            ),
            "execution": {
                "source": (root / "subject.rs").read_text(),
                "oracle": (root / "oracle.rs").read_text(),
                "outputs": outputs,
                "binary_sha256": digest_file(root / "oracle"),
                "mutation": "case suffix True denotes deliberately complemented output",
            },
        },
        profile=summary.profile,
        kind="concrete-witness",
    )
    Coordinator(corpus, WriterIdentity(principal="callable-witness-control")).commit(
        tuple(builder.records.values()), expected=corpus.reader().manifest_id
    )
    request = BehaviorWitnessRequest(
        logical_id="callable-observations",
        profile=summary.profile,
        summaries=(revision_of(summary),),
        observations=builder.select(raw, "/observations", "finite-observations"),
        evidence=(builder.select(raw, "/execution", "ordinary-compiler-and-mutation-evidence"),),
    )
    build_witnesses(corpus, request)
    checked = next(
        item
        for item in corpus.reader().records("behavior_witness_checks")
        if isinstance(item, BehaviorWitnessCheck) and item.request == revision_of(request)
    )
    expected_count = 10
    assert checked.matched == checked.disagreements == expected_count
    assert checked.inconclusive == 0
    assert checked.model == "finite-guarded-result-observation-check.v4"
    return request


def test_callable_reference_rejections_and_bounded_capture(
    callable_cases: tuple[Path, tuple[FactArtifact, ...]],
) -> None:
    """Reference denominator, contextual identity and count/depth frontiers remain explicit."""
    root, artifacts = callable_cases
    complete, shallow = (_records(root, artifact) for artifact in artifacts)
    assert not any(row["kind"] == "mir_instance" for row in shallow)
    assert any(
        item["selection"]["state"] == "depth_budget_exhausted"
        for row in shallow
        for item in row["callables"]
    )
    original = next(row for row in complete if row["symbol"] == "callable_subject::select")
    omitted = copy.deepcopy(original)
    omitted["callables"].pop()
    with pytest.raises(CorpusError, match="denominator is incomplete"):
        mir_callables.validate(omitted)
    wrong = copy.deepcopy(original)
    wrong["callables"][0]["selection"]["instance"] = "mir-instance:" + "0" * 64 + ":" + "1" * 64
    with pytest.raises(CorpusError, match="cross-unit identity"):
        mir_callables.validate(wrong)
    assert {row["symbol"] for row in complete if row["kind"] == "mir_owner"} == {
        row["symbol"] for row in shallow
    }
