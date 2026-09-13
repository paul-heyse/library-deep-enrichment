"""Convergence and mutation controls for finite recursive value/effect envelopes."""

from __future__ import annotations

from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Limits, Outcome
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.fixedpoints import Atom, solve
from library_deep_enrichment.corpus.schemas import revision_of
from tests.test_behavior_engine import builder


def _recursive(name: str, callee: str, *, effect: bool) -> BehaviorProgram:
    graph = builder(name)
    condition = graph.term("local", value="flag", ty="python:bool")
    recurse, base = graph.block(), graph.block()
    graph.edge(recurse, condition=condition)
    graph.edge(base, condition=condition, positive=False)
    graph.current = base
    graph.emit("return", value=graph.term("literal", value="9", ty="python:int"))
    graph.current = recurse
    if effect:
        graph.emit("effect", call=("log_write", ()))
    graph.emit("call", destination="r", call=(callee, (condition,)))
    done = graph.block()
    graph.edge(done)
    graph.current = done
    graph.emit("return", value=graph.term("local", value="r"))
    return graph.finish(("flag",))


def test_mutual_recursion_reaches_checked_constant_and_effect_fixed_point() -> None:
    """A base return and an effect propagate through both members of a recursive SCC."""
    first = _recursive("first", "second", effect=False)
    second = _recursive("second", "first", effect=True)
    targets = {"first": first, "second": second}
    result = solve((first, second), targets, Limits())
    assert result.checked
    assert result.recursive == frozenset(map(revision_of, (first, second)))
    for envelope in result.envelopes.values():
        assert envelope.values == frozenset({Atom(kind="literal", value="9", ty="python:int")})
        assert any(effect.kind == "log_write" for effect in envelope.effects)
        assert {Outcome.RETURN, Outcome.RAISE, Outcome.DIVERGE} <= envelope.outcomes
    summary = Interpreter(Limits(), targets=targets, solution=result).summarize(first)
    returned = tuple(clause for clause in summary.clauses if clause.outcome == Outcome.RETURN)
    assert returned
    assert all(summary.terms[clause.result].value == "9" for clause in returned)
    assert any(clause.outcome == Outcome.DIVERGE for clause in summary.clauses)


def test_removed_recursive_effect_changes_both_envelopes() -> None:
    """A callee mutation invalidates the propagated caller effect without name-based reuse."""
    first = _recursive("first", "second", effect=False)
    second = _recursive("second", "first", effect=False)
    result = solve((first, second), {"first": first, "second": second}, Limits())
    assert all(not envelope.effects for envelope in result.envelopes.values())
