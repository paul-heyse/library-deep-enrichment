"""Actual Ruff/Python controls for comprehension scope, iteration and deferred construction."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from library_guides.analyses.behavior.contracts import BehaviorProgram, Limits, Outcome, Term
from library_guides.analyses.behavior.engine import Interpreter
from library_guides.processes import execute

from tests import test_behavior_python as python_controls

source_case = python_controls.source_case
programs = python_controls.programs


def test_comprehension_bindings_preserve_parent_and_walrus_targets(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Iteration targets are private; assignment expressions bind the containing function."""
    expected = {"comprehension_shadow": 99, "comprehension_walrus": 2}
    for name, value in expected.items():
        summary = Interpreter(Limits(widen_after=12)).summarize(programs[name])
        assert {item.outcome for item in summary.clauses} == {Outcome.RETURN}
        assert {summary.terms[item.result].value for item in summary.clauses} == {str(value)}
    actual = execute_expression(
        "{name:m[name]() for name in ('comprehension_shadow','comprehension_walrus')}"
    )
    assert actual == expected


def test_comprehension_private_accumulator_preserves_element_order(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Known builtin iteration and append preserve the observed finite sequence."""
    for name in ("comprehension_values", "comprehension_filter", "comprehension_nested"):
        summary = Interpreter(Limits(widen_after=16)).summarize(programs[name])
        assert {item.outcome for item in summary.clauses} == {Outcome.RETURN}
        assert len(summary.clauses) == 1
        clause = summary.clauses[0]
        region = next(item for item in clause.regions if item.root == clause.result)
        contents = summary.terms[region.contents]
        assert contents.op == "list"
        actual = execute_expression(f"m['{name}']()")
        expected = _list(summary.terms, contents.args)
        assert expected == actual


def _list(terms: tuple[Term, ...], indices: tuple[int, ...]) -> list[object]:
    result: list[object] = []
    for index in indices:
        term = terms[index]
        if term.op == "tuple":
            result.append(_list(terms, term.args))
        else:
            assert term.op == "literal"
            result.append(
                term.value.lower() == "true" if term.ty.endswith(":bool") else int(term.value)
            )
    return result


def test_generator_expression_acquires_outer_iterator_without_executing_body(
    programs: dict[str, BehaviorProgram],
) -> None:
    """Generator creation calls iter(source) now and defers per-element work."""
    program = programs["generator_outer_order"]
    assert any(item.target == "implicit:iter" for item in program.instructions)
    assert not any(item.target == "implicit:next" for item in program.instructions)
    assert any(item.op == "deferred" and item.args for item in program.terms)
    script = "class Source:\n def __iter__(self):\n  log.append('iter')\n  return iter([1])\nlog=[]\ng=m['generator_outer_order'](log,Source())\ncreated=list(log)\nnext(g)\nprint(json.dumps([created,log]))"
    assert execute_script(script) == [["iter"], ["iter", 1]]


def execute_expression(expression: str) -> object:
    """Evaluate a concrete fixture expression in a separate Python process.

    Returns:
        Its JSON-serializable observed value.

    """
    return execute_script("print(json.dumps(" + expression + "))")


def execute_script(script: str) -> object:
    """Run an independent concrete control against the retained fixture source.

    Returns:
        The emitted JSON observation after a successful process exit.

    """
    fixture = Path(__file__).parent / "fixtures/python_behavior.txt"
    result = execute(
        (
            sys.executable,
            "-c",
            "import json,runpy,sys\nm=runpy.run_path(sys.argv[1])\n" + script,
            str(fixture),
        ),
        cwd=fixture.parent,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)
