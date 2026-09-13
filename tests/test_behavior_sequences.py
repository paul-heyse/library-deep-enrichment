"""Real Python controls for ordered expansion, snapshots, allocation and invalid iterables."""

from __future__ import annotations

from library_guides.analyses.behavior.contracts import BehaviorProgram, Limits, Outcome, Term
from library_guides.analyses.behavior.engine import Interpreter
from library_guides.analyses.behavior.values import Values
from library_guides.analyses.behavior.witness_eval import Evaluation
from library_guides.analyses.behavior.witness_values import Concrete, Value

from tests import test_behavior_comprehensions as concrete_controls
from tests import test_behavior_python as python_controls

source_case = python_controls.source_case
programs = python_controls.programs


def test_expansion_ordered_contents_match_independent_python(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Builtin expansion copies the sequence at its evaluation point before later rebinding."""
    names = ("expanded_tuple", "expanded_list", "expanded_string", "expansion_before_rebinding")
    actual = concrete_controls.execute_expression(
        "{name:m[name]() for name in " + repr(names) + "}"
    )
    assert isinstance(actual, dict)
    for name in names:
        program = programs[name]
        summary = Interpreter(Limits()).summarize(program)
        assert len(summary.clauses) == 1
        clause = summary.clauses[0]
        assert clause.outcome == Outcome.RETURN
        assert not clause.frontier
        values = Evaluation({}, program.nominals).run(summary.terms)
        region = next((item for item in clause.regions if item.root == clause.result), None)
        result = values[region.contents if region is not None else clause.result]
        assert _plain(result) == actual[name]
        if region is not None:
            assert region.unique
            assert not region.escaped
            assert _plain(values[region.extent]) == len(actual[name])


def _plain(value: Value) -> object:
    assert isinstance(value, Concrete)
    if value.kind in {"tuple", "list"}:
        return [_plain(child) for child in value.children]
    return int(value.scalar) if value.kind == "int" else value.scalar


def test_noniterable_expansion_retains_typeerror(programs: dict[str, BehaviorProgram]) -> None:
    """An exact non-iterable does not produce a fabricated successful sequence."""
    summary = Interpreter(Limits()).summarize(programs["expanded_noniterable"])
    assert {clause.outcome for clause in summary.clauses} == {Outcome.RAISE}
    assert {summary.terms[clause.result].value for clause in summary.clauses} == {"TypeError"}
    assert (
        concrete_controls.execute_script(
            "try:\n m['expanded_noniterable']()\nexcept TypeError:\n print(json.dumps('TypeError'))"
        )
        == "TypeError"
    )


def test_custom_iteration_is_ordered_and_remains_an_opaque_protocol(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Expansion runs between surrounding expressions; user iteration is not a builtin binding."""
    program = programs["expansion_order"]
    expansions = [item for item in program.instructions if item.target == "sequence_expansion"]
    assert len(expansions) == 1
    calls = [item for item in program.instructions if item.op == "call"]
    assert (
        min(item.index for item in calls) < expansions[0].index < max(item.index for item in calls)
    )
    script = """log = []
class Source:
    def __iter__(self):
        log.append('iter')
        return iter((2, 3))
result = m['expansion_order'](log, Source())
print(json.dumps([log, result]))
"""
    assert concrete_controls.execute_script(script) == [
        ["before", "iter", "after"],
        [None, 2, 3, None],
    ]
    summary = Interpreter(Limits(clauses=4096)).summarize(program)
    assert any(item.code == "python_dynamic_dispatch" for item in summary.frontier)
    assert any(item.outcome == Outcome.RAISE for item in summary.clauses)


def test_symbolic_sequence_length_and_witness_order_use_segments() -> None:
    """Unknown cardinality remains symbolic while prefix, suffix and element order survive."""
    values = Values(100)
    source = values.add(Term(op="argument", value="items"))
    snapshot = values.add(Term(op="sequence_snapshot", args=(source,), ty="python:tuple"))
    first = values.add(Term(op="literal", value="1", ty="python:int"))
    prefix = values.add(Term(op="tuple", args=(first,)))
    result = values.add(
        Term(op="sequence_concat", args=(prefix, snapshot, prefix), ty="python:tuple")
    )
    length = values.add(Term(op="length", args=(result,), ty="python:int"))
    assert values.terms[result].op == "sequence_concat"
    assert values.terms[length].op == "add"
    observed = Concrete(
        kind="list", children=(Concrete(kind="int", scalar="2"), Concrete(kind="int", scalar="3"))
    )
    evaluated = Evaluation({"items": observed}, ()).run(tuple(values.terms))
    assert _plain(evaluated[result]) == [1, 2, 3, 1]
    assert _plain(evaluated[length]) == len([1, 2, 3, 1])


def test_successful_truth_conversion_is_boolean_but_rich_comparison_need_not_be(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Language-enforced result types survive dynamic calls without constraining rich comparison."""
    boolean = Interpreter(Limits()).summarize(programs["negated_value"])
    assert all(
        boolean.terms[clause.result].ty == "model:bool"
        for clause in boolean.clauses
        if clause.outcome == Outcome.RETURN
    )
    comparison = Interpreter(Limits()).summarize(programs["equality_value"])
    assert any(
        comparison.terms[clause.result].ty == "unknown"
        for clause in comparison.clauses
        if clause.outcome == Outcome.RETURN
    )
    script = """class Subject:
    def __bool__(self):
        return True
    def __eq__(self, other):
        return [7]
print(json.dumps([m['negated_value'](Subject()), m['equality_value'](Subject())]))
"""
    assert concrete_controls.execute_script(script) == [False, [7]]
