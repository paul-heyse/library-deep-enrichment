"""Mutation, reconstruction and alias controls for the owned location domain."""

from __future__ import annotations

from attrs import evolve
from library_deep_enrichment.analyses.behavior.contracts import Language, Limits, Outcome
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.values import scalar

from tests.test_behavior_engine import builder


def test_owned_nested_write_preserves_the_separate_field() -> None:
    """A Rust by-value record update changes precisely the selected nested field."""
    graph = builder("nested_write")
    graph.origin = evolve(graph.origin, language=Language.RUST)
    root = graph.term("local", value="record", ty="rust:record")
    nested = graph.term("field", (root,), "0", "rust:record")
    changed = graph.term("field", (nested,), "1", "rust:u32")
    sibling = graph.term("field", (nested,), "0", "rust:u32")
    new = graph.term("literal", value="9", ty="rust:u32")
    graph.emit("write", value=new, call=("", (changed,)))
    graph.emit("return", value=graph.term("tuple", (changed, sibling)))
    summary = Interpreter(Limits()).summarize(graph.finish(("record",)))
    clause = summary.clauses[0]
    result = summary.terms[clause.result]
    assert result.op == "tuple"
    assert summary.terms[result.args[0]].value == "9"
    assert summary.terms[result.args[1]].op == "field"
    assert summary.terms[result.args[1]].value == "0"
    assert clause.memory[0].strong
    assert not clause.frontier


def test_input_pointer_write_does_not_prove_non_aliasing() -> None:
    """Two caller-owned references may designate the same memory."""
    graph = builder("aliased_write")
    graph.origin = evolve(graph.origin, language=Language.RUST)
    first = graph.term("deref", (graph.term("local", value="first", ty="rust:ref"),))
    second = graph.term("deref", (graph.term("local", value="second", ty="rust:ref"),))
    graph.emit("write", value=graph.term("literal", value="3", ty="rust:u32"), call=("", (first,)))
    graph.emit("return", value=second)
    summary = Interpreter(Limits()).summarize(graph.finish(("first", "second")))
    clause = summary.clauses[0]
    assert summary.terms[clause.result].op == "unknown"
    assert not clause.memory[0].strong
    assert any(item.code == "may_alias_write" for item in clause.frontier)


def test_unknown_effect_cannot_preserve_a_previously_updated_record() -> None:
    """An unmodeled call invalidates a reachable object relationship even on normal return."""
    graph = builder("opaque_after_write")
    graph.origin = evolve(graph.origin, language=Language.RUST)
    root = graph.term("local", value="record", ty="rust:record")
    field = graph.term("field", (root,), "0", "rust:u32")
    graph.emit("write", value=graph.term("literal", value="3", ty="rust:u32"), call=("", (field,)))
    graph.emit("call", destination="ignored", call=("", (root,)))
    continuation = graph.block()
    graph.edge(continuation)
    graph.current = continuation
    graph.emit("return", value=root)
    summary = Interpreter(Limits()).summarize(graph.finish(("record",)))
    returned = next(clause for clause in summary.clauses if clause.outcome == Outcome.RETURN)
    assert not returned.memory
    assert summary.terms[returned.result].op == "unknown"
    assert returned.frontier


def test_fresh_allocations_have_distinct_handles_and_shared_element_values() -> None:
    """Two new containers can retain the same input without aliasing each other's storage."""
    graph = builder("fresh_containers")
    item = graph.term("local", value="item")
    allocation = graph.term("list", (item,))
    graph.emit("assign", destination="first", value=allocation)
    graph.emit("assign", destination="second", value=allocation)
    result = graph.term(
        "tuple", (graph.term("local", value="first"), graph.term("local", value="second"))
    )
    graph.emit("return", value=result)
    summary = Interpreter(Limits()).summarize(graph.finish(("item",)))
    clause = summary.clauses[0]
    first, second = summary.terms[clause.result].args
    assert first != second
    regions = {region.root: region for region in clause.regions}
    assert regions[first].contents == regions[second].contents
    assert regions[first].unique
    assert regions[second].unique
    contents = summary.terms[regions[first].contents]
    assert summary.terms[contents.args[0]].value == "item"


def test_unexposed_collection_survives_an_unrelated_opaque_call() -> None:
    """Unknown external work cannot reach a private accumulator that was never passed to it."""
    graph = builder("private_collection")
    graph.emit("assign", destination="collected", value=graph.term("list"))
    collection = graph.term("local", value="collected")
    graph.emit("call", destination="ignored")
    following = graph.block()
    graph.edge(following)
    graph.current = following
    graph.emit(
        "call",
        destination="ignored",
        call=(
            "internal:list_append",
            (collection, graph.term("literal", value="7", ty="python:int")),
        ),
    )
    returned = graph.block()
    graph.edge(returned)
    graph.current = returned
    graph.emit("return", value=collection)
    summary = Interpreter(Limits()).summarize(graph.finish(()))
    clause = next(item for item in summary.clauses if item.outcome == Outcome.RETURN)
    region = next(item for item in clause.regions if item.root == clause.result)
    assert not region.escaped
    assert scalar(summary.terms[region.extent]) == 1
    contents = summary.terms[region.contents]
    expected_item = 7
    assert scalar(summary.terms[contents.args[0]]) == expected_item


def test_exposed_collection_loses_contents_without_losing_handle_identity() -> None:
    """Passing the container to unknown code invalidates contents and uniqueness evidence."""
    graph = builder("escaped_collection")
    graph.emit("assign", destination="container", value=graph.term("list"))
    container = graph.term("local", value="container")
    graph.emit("call", destination="ignored", call=("", (container,)))
    returned = graph.block()
    graph.edge(returned)
    graph.current = returned
    graph.emit("return", value=container)
    summary = Interpreter(Limits()).summarize(graph.finish(()))
    clause = next(item for item in summary.clauses if item.outcome == Outcome.RETURN)
    region = next(item for item in clause.regions if item.root == clause.result)
    assert region.escaped
    assert not region.unique
    assert summary.terms[region.contents].op == "unknown"
    assert summary.terms[clause.result].op == "allocation"
