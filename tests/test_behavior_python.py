"""Real pinned Ruff producer through guarded interpretation and independent Python controls."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from library_deep_enrichment.analyses.behavior import schemas
from library_deep_enrichment.analyses.behavior.builder import Origin
from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Language, Limits, Outcome
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.python import normalize
from library_deep_enrichment.analyses.behavior.python_nodes import read
from library_deep_enrichment.facts.contracts import Budget, FactArtifact, FileEntry
from library_deep_enrichment.processes import execute
from library_deep_enrichment.source_pipeline import SourceJob, extract
from library_deep_enrichment.store.digests import canonical_bytes, digest_file

from tests.test_native_lanes import SCHEMAS, TOOLING, _binary, _records


@pytest.fixture(scope="module")
def source_case(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, FactArtifact]:
    """Acquire real worker facts before interpreting any fixture.

    Returns:
        A real native artifact and its retained transport root.

    """
    assert schemas.TERMS is not None
    root = tmp_path_factory.mktemp("python-behavior")
    source = root / "subject.py"
    source.write_bytes((TOOLING / "tests/fixtures/python_behavior.txt").read_bytes())
    request = root / "request.json"
    request.write_bytes(
        canonical_bytes(
            {
                "root": str(source.parent),
                "profile": "behavior-controls",
                "python_minor": 14,
                "lexical": True,
                "execution": True,
                "files": [
                    {"path": source.name, "digest": digest_file(source), "language": "python"}
                ],
            }
        )
    )
    job = SourceJob(
        id="python-execution",
        kind="execution",
        input=str(request),
        helper=str(_binary("source-facts")),
        profile="behavior-controls",
        schema=str(SCHEMAS / "source-execution.v1.schema.json"),
        witnesses=(
            FileEntry(
                path=str(source),
                digest=digest_file(source),
                size=source.stat().st_size,
                kind="python",
            ),
        ),
    )
    artifact = extract(root, job, Budget())
    return root, artifact


@pytest.fixture(scope="module")
def programs(source_case: tuple[Path, FactArtifact]) -> dict[str, BehaviorProgram]:
    """Normalize the actual fixture population.

    Returns:
        Source-normalized programs keyed by their fixture name.

    """
    root, artifact = source_case
    source = root / "subject.py"
    result = {}
    for row in _records(root, artifact):
        if row["kind"] != "execution":
            continue
        raw = dict(row["payload"])
        raw.pop("family")
        if raw["kind"] != "function":
            continue
        node = read(raw, source_size=source.stat().st_size, node_limit=10000)
        origin = Origin(
            request="controls",
            owner=row["id"],
            artifact=artifact.id,
            context=artifact.context,
            profile=artifact.profile,
            symbol=node.value,
            language=Language.PYTHON,
        )
        result[node.value] = normalize(origin, node, Limits())
    (root / "population.json").write_text(json.dumps(sorted(result)))
    return result


@pytest.mark.parametrize(
    "name", ["final_override", "short_circuit", "break_finally", "ordinary_finally"]
)
def test_cleanup_and_evaluation_match_python(
    programs: dict[str, BehaviorProgram], name: str
) -> None:
    """Actual Python outcomes match all closed fixture outcomes after real extraction."""
    expected = _concrete()[name]
    summary = Interpreter(Limits()).summarize(programs[name])
    assert summary.clauses
    assert all(clause.outcome == Outcome.RETURN for clause in summary.clauses)
    values = {summary.terms[clause.result].value for clause in summary.clauses}
    assert values == {str(expected).lower()}


def test_cleanup_does_not_retroactively_change_return(programs: dict[str, BehaviorProgram]) -> None:
    """Returned values are evaluated before a finally assignment changes local state."""
    summary = Interpreter(Limits()).summarize(programs["guarded_cleanup"])
    outputs = {
        summary.terms[c.result].value for c in summary.clauses if c.outcome == Outcome.RETURN
    }
    expected = _concrete()
    assert outputs == {str(expected["guarded_true"]), str(expected["guarded_false"])}


def test_identity_condition_has_builtin_truth_but_object_truth_remains_dynamic(
    programs: dict[str, BehaviorProgram], source_case: tuple[Path, FactArtifact]
) -> None:
    """Identity yields a boolean without consulting an object's arbitrary truth protocol."""
    summary = Interpreter(Limits()).summarize(programs["identity_condition"])
    assert all(item.outcome == Outcome.RETURN for item in summary.clauses)
    assert all(item.code == "predicate_unsupported" for item in summary.frontier)
    dynamic = Interpreter(Limits()).summarize(programs["custom_condition"])
    assert any(item.outcome == Outcome.RAISE for item in dynamic.clauses)
    assert any(item.code == "python_dynamic_dispatch" for item in dynamic.frontier)
    root, _ = source_case
    script = """import runpy, json, sys
values = runpy.run_path(sys.argv[1])
class Subject:
    def __bool__(self):
        raise RuntimeError('truth consulted')
observed = [values['identity_condition'](None), values['identity_condition'](Subject())]
try:
    values['custom_condition'](Subject())
except RuntimeError:
    observed.append('raised')
print(json.dumps(observed))
"""
    result = execute((sys.executable, "-c", script, str(root / "subject.py")), cwd=root, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == [1, 2, "raised"]


def _concrete() -> dict:
    fixture = TOOLING / "tests/fixtures/python_behavior.txt"
    program = "import runpy,json,sys; m=runpy.run_path(sys.argv[1]); r={n:m[n]() for n in ('final_override','short_circuit','break_finally','ordinary_finally')}; r.update(guarded_true=m['guarded_cleanup'](enabled=True),guarded_false=m['guarded_cleanup'](enabled=False)); print(json.dumps(r))"
    result = execute(
        (sys.executable, "-c", program, str(fixture)), cwd=Path(__file__).parent, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", ["unbound_local", "deleted_local"])
def test_missing_local_raises_instead_of_becoming_a_closed_unknown(
    programs: dict[str, BehaviorProgram], name: str
) -> None:
    """Missing local bindings preserve an exceptional outcome with an explicit type."""
    summary = Interpreter(Limits()).summarize(programs[name])
    assert all(item.outcome == Outcome.RAISE for item in summary.clauses)
    assert {summary.terms[item.result].value for item in summary.clauses} == {"UnboundLocalError"}


def test_behavior_admission_replay_and_warm_reuse(
    source_case: tuple[Path, FactArtifact], tmp_path: Path
) -> None:
    """Admit real-source consequences, reject a forged result, and reuse unchanged work."""
    from attrs import evolve
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest, BehaviorSummary
    from library_deep_enrichment.analyses.behavior.service import validate
    from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
    from library_deep_enrichment.corpus.backend import CorpusError
    from library_deep_enrichment.corpus.native_contracts import NativeFact
    from library_deep_enrichment.corpus.schemas import revision_of
    from library_deep_enrichment.corpus.store import Corpus
    from library_deep_enrichment.native_admission import NativeInputs, admit_artifacts
    from library_deep_enrichment.workflows.behavior import build

    root, artifact = source_case
    corpus = Corpus(tmp_path / "corpus")
    admit_artifacts(corpus, NativeInputs(root=root, artifacts=(artifact,)))
    reader = corpus.reader()
    owners = tuple(
        item
        for item in reader.records("native_facts")
        if isinstance(item, NativeFact)
        and item.kind == "definition"
        and item.symbol
        in {
            "final_override",
            "short_circuit",
            "break_finally",
            "ordinary_finally",
            "guarded_cleanup",
            "decorated_extent",
        }
    )
    request = BehaviorRequest(
        logical_id="controls",
        profile=artifact.profile,
        owners=tuple(sorted(revision_of(item) for item in owners)),
        artifacts=tuple(sorted({item.artifact for item in owners})),
    )
    result = build(corpus, request)
    assert not result.reused
    assert build(corpus, request).reused
    reader = corpus.reader()
    summaries = tuple(
        item for item in reader.records("behavior_summaries") if isinstance(item, BehaviorSummary)
    )
    assert len(summaries) == len(owners)
    decorated = {
        item.program: item
        for item in summaries
        if any(frontier.code == "decorated_entry" for frontier in item.frontier)
    }
    assert len(decorated) == len({"FirstDecorated", "SecondDecorated"})
    observed = execute(
        (
            sys.executable,
            "-c",
            (
                "import runpy,json,sys; m=runpy.run_path(sys.argv[1]); "
                "print(json.dumps([m[n]().decorated_extent "
                "for n in ('FirstDecorated', 'SecondDecorated')]))"
            ),
            str(root / "subject.py"),
        ),
        cwd=root,
        timeout=10,
    )
    assert observed.returncode == 0, observed.stderr
    assert {
        int(item.terms[clause.result].value)
        for item in decorated.values()
        for clause in item.clauses
    } == set(json.loads(observed.stdout))
    summary = summaries[0]
    forged = evolve(summary, clauses=())
    predecessor = reader.manifest_id
    with pytest.raises(CorpusError, match="retained-source replay"):
        validate(reader, (forged,))
    with pytest.raises(CorpusError, match="cannot bypass its stage owner"):
        Coordinator(corpus, WriterIdentity(principal="forgery-control")).commit(
            (forged,), expected=predecessor
        )
    assert corpus.reader().manifest_id == predecessor
