"""Independent protocol results correlated through source instructions and derived value origins."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from attrs import evolve
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorSummary,
    Limits,
    Outcome,
)
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.witness_checks import check
from library_deep_enrichment.analyses.behavior.witness_contracts import (
    Cell,
    Input,
    Observation,
    OperationObservation,
    Verdict,
)
from library_deep_enrichment.analyses.behavior.witness_operators import same_operands
from library_deep_enrichment.analyses.behavior.witness_values import Concrete
from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.processes import execute

from tests import test_behavior_python as python_controls

source_case = python_controls.source_case
programs = python_controls.programs


def _observe(program: BehaviorProgram, summary: BehaviorSummary) -> Observation:
    fixture = Path(__file__).parent / "fixtures/python_behavior.txt"
    script = """import dis,json,runpy,sys
from pathlib import Path
module=runpy.run_path(sys.argv[1]); target=module[sys.argv[2]]; events=[]
source=Path(sys.argv[1]).read_bytes().splitlines(keepends=True)
positions={i.offset:i.positions for i in dis.get_instructions(target,show_caches=True)}
class Subject:
 def __init__(self): self.count=0
 def __getitem__(self,key):
  self.count+=1
  return key+7 if sys.argv[2]=='two_subscriptions' else self.count
subject=Subject()
def profile(frame,event,arg):
 if event=='return' and frame.f_back is not None and frame.f_back.f_code is target.__code__:
  pos=positions[frame.f_back.f_lasti]
  events.append({'start':sum(map(len,source[:pos.lineno-1]))+pos.col_offset,'end':sum(map(len,source[:pos.end_lineno-1]))+pos.end_col_offset,'key':frame.f_locals['key'],'result':arg})
sys.setprofile(profile)
try: result=target(subject)
finally: sys.setprofile(None)
print(json.dumps({'identity':str(id(subject)),'events':events,'result':result}))
"""
    output = execute(
        (sys.executable, "-c", script, str(fixture), program.symbol), cwd=fixture.parent, timeout=10
    )
    assert output.returncode == 0, output.stderr
    actual = json.loads(output.stdout)
    cells = [Cell(kind="opaque", identity=actual["identity"])]
    operations = []
    for event in actual["events"]:
        matching = [
            item
            for item in program.instructions
            if item.op == "evaluate"
            and item.target == "subscript"
            and (item.start, item.end) == (event["start"], event["end"])
        ]
        assert len(matching) == 1
        key = len(cells)
        cells.append(Cell(kind="int", scalar=str(event["key"])))
        result = len(cells)
        cells.append(Cell(kind="int", scalar=str(event["result"])))
        operations.append(
            OperationObservation(instruction=matching[0].index, arguments=(0, key), result=result)
        )
    children = []
    for value in actual["result"]:
        children.append(len(cells))
        cells.append(Cell(kind="int", scalar=str(value)))
    cells.append(Cell(kind="tuple", children=tuple(children)))
    return Observation(
        case=program.symbol,
        summary=revision_of(summary),
        values=tuple(cells),
        inputs=(Input(parameter="container", value=0),),
        outcome=Outcome.RETURN,
        result=len(cells) - 1,
        assumptions=(
            "python:ordinary_field_and_index_access",
            "python:ordinary_primitive:subscript",
        ),
        invocation="python-bytecode-profile:" + program.symbol,
        operations=tuple(operations),
    )


def test_operator_results_require_exact_sources_operands_and_event_denominator(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Whole __getitem__ returns match only their own bytecode/source operation and operands."""
    program = programs["two_subscriptions"]
    interpreter = Interpreter(Limits())
    summary = interpreter.summarize(program)
    origins = interpreter.origins.record(summary)
    observation = _observe(program, summary)
    assert check(program, summary, observation, origins=origins).verdict == Verdict.MATCHED
    assert summary.frontier
    missing = evolve(observation, operations=observation.operations[:1])
    assert check(program, summary, missing, origins=origins).verdict == Verdict.INCONCLUSIVE
    repeated = evolve(observation, operations=(*observation.operations, observation.operations[0]))
    assert check(program, summary, repeated, origins=origins).verdict == Verdict.INCONCLUSIVE
    first, second = observation.operations
    wrong = evolve(observation, operations=(evolve(first, arguments=second.arguments), second))
    assert check(program, summary, wrong, origins=origins).verdict == Verdict.INCONCLUSIVE
    with pytest.raises(CorpusError, match="exact summary origin table"):
        check(program, summary, observation)
    with pytest.raises(CorpusError, match="another summary/request/profile"):
        check(program, summary, observation, origins=evolve(origins, summary="another"))


def test_conflicting_observations_of_an_interned_value_remain_inconclusive(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Stateful protocol calls cannot be collapsed into an observed pure value relationship."""
    program = programs["repeated_subscription"]
    interpreter = Interpreter(Limits())
    summary = interpreter.summarize(program)
    observation = _observe(program, summary)
    results = {observation.values[item.result].scalar for item in observation.operations}
    assert results == {"1", "2"}
    origins = interpreter.origins.record(summary)
    assert check(program, summary, observation, origins=origins).verdict == Verdict.INCONCLUSIVE


def test_structured_operator_operands_preserve_opaque_identities() -> None:
    """Sequence shape and individual object identities both matter to argument correlation."""
    first = Concrete(kind="opaque", identity="first")
    second = Concrete(kind="opaque", identity="second")
    sequence = Concrete(kind="tuple", children=(first, second))
    assert same_operands(sequence, sequence)
    assert not same_operands(sequence, evolve(sequence, children=(second, first)))
    assert not same_operands(first, evolve(first, identity=""))
