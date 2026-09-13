"""Real-source context, pattern and deferred-body controls with independent execution traces."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from library_guides.analyses.behavior.builder import Origin
from library_guides.analyses.behavior.contracts import Language, Limits, Outcome
from library_guides.analyses.behavior.engine import Interpreter
from library_guides.analyses.behavior.python import normalize
from library_guides.analyses.behavior.python_nodes import read
from library_guides.facts.contracts import FactArtifact
from library_guides.processes import execute

from tests import test_behavior_python as python_controls
from tests.test_native_lanes import TOOLING, _records

source_case = python_controls.source_case
programs = python_controls.programs


@pytest.fixture(scope="module")
def traces() -> dict:
    """Run ordinary Python code in a separate bounded process.

    Returns:
        Context-return and generator creation/resume/close traces from the real runtime.

    """
    script = """import runpy,json,sys
m=runpy.run_path(sys.argv[1]); log=[]
class Manager:
    def __enter__(self): log.append('enter'); return 5
    def __exit__(self,*error): log.append('exit'); return False
value=m['context_return'](Manager()); context=list(log); log.clear()
generator=m['deferred_cleanup'](log); created=list(log)
yielded=next(generator); advanced=list(log)
generator.close(); closed=list(log)
print(json.dumps(dict(context=context,value=value,created=created,advanced=advanced,closed=closed,yielded=yielded,match=m['singleton_match']())))
"""
    result = execute(
        (sys.executable, "-c", script, str(TOOLING / "tests/fixtures/python_behavior.txt")),
        cwd=TOOLING,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_singleton_pattern_keeps_only_the_matching_case(programs: dict, traces: dict) -> None:
    """Non-overridable None identity selects one actual match case."""
    summary = Interpreter(Limits()).summarize(programs["singleton_match"])
    assert all(clause.outcome == Outcome.RETURN for clause in summary.clauses)
    assert {summary.terms[clause.result].value for clause in summary.clauses} == {
        str(traces["match"])
    }


def test_context_return_keeps_exit_before_the_pending_value(programs: dict, traces: dict) -> None:
    """Normal return executes exit; an unknown exit may also fail or never return."""
    summary = Interpreter(Limits(clauses=1000)).summarize(programs["context_return"])
    returned = tuple(clause for clause in summary.clauses if clause.outcome == Outcome.RETURN)
    assert traces["context"] == ["enter", "exit"]
    assert returned
    assert all(summary.terms[clause.result].value == str(traces["value"]) for clause in returned)
    assert all(
        any(effect.target == "implicit:context_exit" for effect in clause.effects)
        for clause in returned
    )
    assert any(clause.outcome == Outcome.UNKNOWN for clause in summary.clauses)


def test_deferred_construction_and_activation_have_distinct_effects(
    source_case: tuple[Path, FactArtifact], programs: dict, traces: dict
) -> None:
    """Creating a generator has no body log effect; resuming and closing can run cleanup."""
    root, artifact = source_case
    raw = next(
        row
        for row in _records(root, artifact)
        if row["kind"] == "execution"
        and row["payload"]["kind"] == "function"
        and row["payload"]["value"] == "deferred_cleanup"
    )
    payload = dict(raw["payload"])
    payload.pop("family")
    node = read(payload, source_size=(root / "subject.py").stat().st_size, node_limit=10000)
    origin = Origin(
        request="activation",
        owner=raw["id"],
        artifact=artifact.id,
        context=artifact.context,
        profile=artifact.profile,
        symbol=node.value,
        language=Language.PYTHON,
    )
    active = normalize(origin, node, Limits(), phase="activate")
    created = Interpreter(Limits()).summarize(programs["deferred_cleanup"])
    assert traces["created"] == []
    assert traces["advanced"] == ["started"]
    assert traces["closed"] == ["started", "cleaned"]
    assert all(
        effect.kind == "descriptor_allocation"
        for clause in created.clauses
        for effect in clause.effects
    )
    assert any(instruction.op == "suspend" for instruction in active.instructions)
    assert any(edge.kind == "cancel" for edge in active.edges)
    summary = Interpreter(Limits(clauses=1000)).summarize(active)
    assert any(clause.outcome == Outcome.SUSPEND for clause in summary.clauses)
    assert any(effect.phase == "cancel" for clause in summary.clauses for effect in clause.effects)
