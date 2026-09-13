"""Independent callback traces check result forwarding without proving callback semantics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from attrs import evolve
from library_guides.analyses.behavior.contracts import BehaviorProgram, Limits, Outcome, Term
from library_guides.analyses.behavior.engine import Interpreter
from library_guides.analyses.behavior.witness_checks import check
from library_guides.analyses.behavior.witness_contracts import (
    CallObservation,
    Cell,
    GlobalBinding,
    Input,
    Observation,
    Projection,
    Verdict,
)
from library_guides.analyses.behavior.witness_eval import Evaluation
from library_guides.analyses.behavior.witness_values import Concrete, Unresolved
from library_guides.corpus.backend import CorpusError
from library_guides.corpus.schemas import revision_of
from library_guides.processes import execute

from tests import test_behavior_python as python_controls
from tests.test_behavior_comprehensions import execute_script
from tests.test_behavior_witnesses import identity

source_case = python_controls.source_case
programs = python_controls.programs


def test_identity_projection_checks_only_observed_identity() -> None:
    """Opaque contents remain unknown even when a finite output identity matches."""
    program, summary = identity()
    observation = Observation(
        case="opaque-identity",
        summary=revision_of(summary),
        values=(Cell(kind="opaque", identity="object:1"), Cell(kind="str", scalar="object:1")),
        inputs=(Input(parameter="x", value=0),),
        outcome=Outcome.RETURN,
        result=1,
        projection=(Projection(kind="identity"),),
    )
    assert check(program, summary, observation).verdict == Verdict.MATCHED
    changed = evolve(
        observation, values=(*observation.values[:1], Cell(kind="str", scalar="object:2"))
    )
    assert check(program, summary, changed).verdict == Verdict.DISAGREEMENT
    unobserved = evolve(observation, values=(Cell(kind="opaque"), observation.values[1]))
    assert check(program, summary, unobserved).verdict == Verdict.INCONCLUSIVE
    full = evolve(observation, result=0, projection=())
    assert check(program, summary, full).verdict == Verdict.INCONCLUSIVE


def test_none_identity_preserves_opaque_uncertainty() -> None:
    """Observed concrete categories exclude None; an opaque value may still conceal it."""
    terms = (
        Term(op="argument", value="x"),
        Term(op="literal", ty="python:none"),
        Term(op="is_not", args=(0, 1)),
    )
    record = Evaluation({"x": Concrete(kind="record", identity="object:1")}, ()).run(terms)
    assert record[-1] == Concrete(kind="bool", scalar="true")
    opaque = Evaluation({"x": Concrete(kind="opaque")}, ()).run(terms)
    assert isinstance(opaque[-1], Unresolved)
    legacy = Evaluation(
        {"x": Concrete(kind="record", identity="object:1")}, (), category_identity=False
    ).run(terms)
    assert isinstance(legacy[-1], Unresolved)


def test_negated_collection_guard_controls_returned_object_identity(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Python not converts sequence truth before negating; identity is independently observed."""
    actual = execute_script(
        "value=object()\n"
        "print(json.dumps([m['witness_empty_branch'](value,[]) is value, "
        "m['witness_empty_branch'](value,[1]) is None]))"
    )
    assert actual == [True, True]
    program = programs["witness_empty_branch"]
    summary = Interpreter(Limits()).summarize(program)
    for items in ((), (0,)):
        observation = Observation(
            case=str(items),
            summary=revision_of(summary),
            values=(
                Cell(kind="int", scalar="1"),
                Cell(kind="list", children=items),
                Cell(kind="opaque", identity="returned-object"),
                Cell(kind="str", scalar="returned-object") if not items else Cell(kind="none"),
            ),
            inputs=(Input(parameter="value", value=2), Input(parameter="items", value=1)),
            outcome=Outcome.RETURN,
            result=3,
            projection=(Projection(kind="identity"),) if not items else (),
            assumptions=("python:ordinary_primitive:unary:not",),
        )
        assert check(program, summary, observation).verdict == Verdict.MATCHED


def _trace(name: str) -> dict:
    fixture = Path(__file__).parent / "fixtures/python_behavior.txt"
    script = """import json,runpy,sys
m=runpy.run_path(sys.argv[1]); target=m[sys.argv[2]]; events=[]
def callback(value):
    return value * 7
def profile(frame,event,arg):
    if event=='return' and frame.f_back is not None and frame.f_back.f_code is target.__code__:
        events.append({'input':frame.f_locals['value'],'result':arg})
sys.setprofile(profile)
try:
    result=target(3) if sys.argv[2]=='witness_global' else target(True,callback,3)
finally:
    sys.setprofile(None)
print(json.dumps({'result':result,'events':events}))
"""
    result = execute(
        (sys.executable, "-c", script, str(fixture), name), cwd=fixture.parent, timeout=10
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", ["witness_forward", "witness_global"])
def test_real_call_return_and_arguments_correlate_at_one_source_site(
    programs: dict[str, BehaviorProgram], name: str
) -> None:
    """A caller relationship is checked against independently traced helper entry and return."""
    program = programs[name]
    summary = Interpreter(Limits()).summarize(program)
    actual = _trace(name)
    assert len(actual["events"]) == 1
    event = actual["events"][0]
    call = next(item for item in program.instructions if item.op == "call")
    assert call.start < call.end
    values = (
        Cell(kind="bool", scalar="true"),
        Cell(kind="opaque", identity="callable:1"),
        Cell(kind="int", scalar=str(event["input"])),
        Cell(kind="int", scalar=str(event["result"])),
        Cell(kind="int", scalar=str(actual["result"])),
    )
    indices = (2,) if name == "witness_global" else (0, 1, 2)
    observation = Observation(
        case=name,
        summary=revision_of(summary),
        values=values,
        inputs=tuple(
            Input(parameter=parameter, value=index)
            for parameter, index in zip(program.parameters, indices, strict=True)
        ),
        outcome=Outcome.RETURN,
        result=4,
        assumptions=(
            "python:ordinary_primitive:truth",
            "python:ordinary_primitive:global_lookup",
            "python:separation_excludes_reflective_frame_mutation",
        ),
        globals=(GlobalBinding(name="witness_helper", value=1),)
        if name == "witness_global"
        else (),
        calls=(CallObservation(instruction=call.index, arguments=(1, 2), result=3),),
        invocation="independent-python-profile:" + name,
    )
    assert check(program, summary, observation).verdict == Verdict.MATCHED
    assert summary.frontier
    assert check(program, summary, evolve(observation, calls=())).verdict == Verdict.INCONCLUSIVE
    repeated = evolve(observation, calls=observation.calls * 2)
    assert check(program, summary, repeated).verdict == Verdict.INCONCLUSIVE
    wrong = evolve(observation, calls=(evolve(observation.calls[0], arguments=(1, 3)),))
    assert check(program, summary, wrong).verdict == Verdict.INCONCLUSIVE
    with pytest.raises(CorpusError, match="explicit unresolved source call"):
        check(
            program,
            summary,
            evolve(observation, calls=(evolve(observation.calls[0], instruction=-1),)),
        )
    with pytest.raises(CorpusError, match="invocation identity"):
        check(program, summary, evolve(observation, invocation=""))
    with pytest.raises(CorpusError, match="globals repeat or escape"):
        check(
            program, summary, evolve(observation, globals=(GlobalBinding(name="absent", value=1),))
        )
