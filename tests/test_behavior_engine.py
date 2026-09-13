"""Independent concrete controls for guarded value, failure and call propagation."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from library_deep_enrichment.analyses.behavior import schemas
from library_deep_enrichment.analyses.behavior.builder import GraphBuilder, Origin
from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    Language,
    Limits,
    Outcome,
    Precision,
    Term,
)
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.values import Values
from library_deep_enrichment.corpus.backend import BudgetExceededError


def builder(name: str = "choose") -> GraphBuilder:
    """Prepare an execution graph unrelated to any pilot task.

    Returns:
        An owned graph builder with explicit contextual identity.

    """
    assert schemas.CLAUSES is not None
    return GraphBuilder(
        Origin(
            request="r",
            owner=name,
            artifact="a",
            context="c",
            profile="p",
            symbol=name,
            language=Language.PYTHON,
        ),
        "fixture",
    )


def choose() -> BehaviorProgram:
    """Represent a two-way value transform.

    Returns:
        A body equivalent to returning the input when enabled and zero otherwise.

    """
    graph = builder()
    flag = graph.term("local", value="enabled", ty="python:bool")
    value = graph.term("local", value="value", ty="python:int")
    true, false = graph.block(), graph.block()
    graph.edge(true, condition=flag)
    graph.edge(false, condition=flag, positive=False)
    graph.current = true
    graph.emit("return", value=value)
    graph.current = false
    graph.emit("return", value=graph.term("literal", value="0", ty="python:int"))
    return graph.finish(("enabled", "value"))


@given(enabled=st.booleans(), value=st.integers(min_value=-10000, max_value=10000))
def test_guarded_summary_matches_independent_concrete_choice(*, enabled: bool, value: int) -> None:
    """All generated values satisfy the original Python conditional function."""
    summary = Interpreter(Limits()).summarize(choose())
    clause = next(c for c in summary.clauses if c.guards[0].positive == enabled)
    output = summary.terms[clause.result]
    actual = value if enabled else 0
    observed = value if output.op == "argument" and output.value == "value" else int(output.value)
    assert observed == actual
    assert summary.precision == Precision.CLOSED


def test_mutated_branch_guard_changes_the_derived_relation() -> None:
    """A guard mutation cannot reuse the old relationship under a new body."""
    from attrs import evolve

    original = choose()
    modified = evolve(
        original, edges=tuple(evolve(e, positive=not e.positive) for e in original.edges)
    )
    before = Interpreter(Limits()).summarize(original)
    after = Interpreter(Limits()).summarize(modified)
    assert before.clauses != after.clauses
    assert before.program != after.program


def test_indirect_call_preserves_possible_unhandled_failure() -> None:
    """An opaque callee has both a normal and an exceptional outcome."""
    graph = builder()
    successor = graph.block()
    graph.emit("call", destination="r")
    graph.edge(successor)
    graph.current = successor
    graph.emit("return", value=graph.term("local", value="r"))
    summary = Interpreter(Limits()).summarize(graph.finish(()))
    assert {c.outcome for c in summary.clauses} == {Outcome.RETURN, Outcome.RAISE, Outcome.UNKNOWN}
    assert summary.precision == Precision.CONSERVATIVE
    assert all(c.frontier for c in summary.clauses)


def test_opaque_return_retains_evaluated_call_provenance_after_its_effects() -> None:
    """Returning an unknown callee result still preserves the call/input relationship."""
    graph = builder("forward_callback")
    value = graph.term("local", value="value", ty="python:int")
    graph.emit("call", destination="result", call=("unresolved-callback", (value,)))
    successor = graph.block()
    graph.edge(successor)
    graph.current = successor
    graph.emit("return", value=graph.term("local", value="result"))
    summary = Interpreter(Limits()).summarize(graph.finish(("value",)))
    returned = next(item for item in summary.clauses if item.outcome == Outcome.RETURN)
    result = summary.terms[returned.result]
    assert result.op == "call"
    assert result.value == "unresolved-callback"
    assert summary.terms[result.args[0]].value.startswith("call_result:")
    assert summary.terms[result.args[1]].value == "value"
    assert returned.frontier


def test_callee_substitution_preserves_input_guard_and_output() -> None:
    """A public wrapper inherits relationships through the exact selected call."""
    graph = builder("wrapper")
    a = graph.term("local", value="flag", ty="python:bool")
    b = graph.term("local", value="number", ty="python:int")
    graph.emit("call", destination="result", call=("compiler-target", (a, b)))
    successor = graph.block()
    graph.edge(successor)
    graph.current = successor
    graph.emit("return", value=graph.term("local", value="result"))
    summary = Interpreter(Limits(), targets={"compiler-target": choose()}).summarize(
        graph.finish(("flag", "number"))
    )
    expected_count = 2
    assert len(summary.clauses) == expected_count
    assert all(c.outcome == Outcome.RETURN for c in summary.clauses)
    assert any(summary.terms[c.result].value == "number" for c in summary.clauses)
    assert len(summary.dependencies) == expected_count


def test_cycle_does_not_disappear_when_another_path_returns() -> None:
    """A possible infinite branch remains a termination frontier."""
    graph = builder()
    flag = graph.term("local", value="enabled", ty="python:bool")
    loop, done = graph.block(), graph.block()
    graph.edge(loop, condition=flag)
    graph.edge(done, condition=flag, positive=False)
    graph.current = loop
    graph.edge(loop)
    graph.current = done
    graph.emit("return", value=graph.term("literal", value="1", ty="python:int"))
    summary = Interpreter(Limits()).summarize(graph.finish(("enabled",)))
    assert {c.outcome for c in summary.clauses} == {Outcome.RETURN, Outcome.DIVERGE}
    assert any(f.code == "abstract_cycle" for f in summary.frontier)


def test_budget_failure_is_not_a_completed_empty_analysis() -> None:
    """Exhaustion raises before producing a misleading closed consequence."""
    with pytest.raises(BudgetExceededError):
        Interpreter(Limits(states=1)).summarize(choose())


def test_constant_pool_does_not_assume_integer_object_identity() -> None:
    """Value equality cannot silently become Python object identity."""
    values = Values(100)
    argument = values.add(Term(op="argument", value="n", ty="python:int"))
    identity = values.add(Term(op="is", args=(argument, argument), ty="python:bool"))
    assert values.terms[identity].op == "is"


def test_field_projection_recovers_forwarded_aggregate_input() -> None:
    """A constructed record's component follows the primitive aggregate transfer."""
    graph = builder()
    source = graph.term("local", value="metadata")
    aggregate = graph.term("aggregate", (source,), "record")
    field = graph.term("field", (aggregate,), "0")
    graph.emit("return", value=field)
    summary = Interpreter(Limits()).summarize(graph.finish(("metadata",)))
    assert summary.terms[summary.clauses[0].result].value == "metadata"


def test_separate_unknown_evaluations_do_not_imply_value_equality() -> None:
    """Nondeterministic results at the same source point need distinct evaluation identities."""
    values = Values(100)
    first = values.unknown("same_callsite", "rust:u32", fresh=True)
    second = values.unknown("same_callsite", "rust:u32", fresh=True)
    comparison = values.add(Term(op="eq", args=(first, second), ty="rust:bool"))
    assert first != second
    assert values.terms[comparison].op == "eq"
