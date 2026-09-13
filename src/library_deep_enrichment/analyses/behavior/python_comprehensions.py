"""Comprehension evaluation order, private bindings, implicit iteration and accumulation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.python_expr import store, suspend_value

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.python_graph import PythonGraph
    from library_deep_enrichment.analyses.behavior.python_nodes import Node


def comprehension(context: PythonGraph, node: Node) -> int:
    """Lower an owned comprehension without leaking its target bindings into its parent.

    Returns:
        Its private accumulator or a deferred handle retaining the outer iterator.

    """
    generators = node.children("generators")
    require("comprehension has no generator", condition=bool(generators))
    first = generators[0]
    outer = context.expression(first.one("iter"))
    iterator = context.invoke(
        first, (outer,), "implicit:aiter" if first.value == "async" else "implicit:iter"
    )
    graph = context.graph
    if node.kind == "generator_expression":
        graph.unknown(
            "deferred_activation",
            "lifecycle",
            str(node.start),
            "only the outer iterable and iterator are evaluated at construction; body activation requires a separate owner",
        )
        graph.emit("effect", call=("descriptor_allocation", ()), span=node.span)
        return context.save(
            graph.term("deferred", (iterator,), value=f"generator_expression:{node.start}"), node
        )
    names, slots = context.local_names, context.local_slots
    bound = set().union(*(_bindings(generator.one("target")) for generator in generators))
    context.local_names = names | bound
    context.local_slots = {
        **slots,
        **{name: f"$comprehension:{node.start}:{name}" for name in bound},
    }
    kind = node.kind.removesuffix("_comprehension")
    accumulator = context.save(graph.term(kind, value=f"comprehension:{node.start}"), node)
    try:
        _generator(context, node, generators, iterator, accumulator)
    finally:
        context.local_names, context.local_slots = names, slots
    return accumulator


def _bindings(target: Node) -> set[str]:
    if target.kind == "name":
        return {target.value}
    if target.kind in {"tuple", "list"}:
        return set().union(*(_bindings(item) for item in target.children("items")))
    if target.kind == "starred":
        return _bindings(target.one("value"))
    return set()


def _generator(
    context: PythonGraph, node: Node, generators: tuple[Node, ...], iterator: int, accumulator: int
) -> None:
    graph, generator = context.graph, generators[0]
    again, failed, exhausted, other = (graph.block() for _ in range(4))
    context.jump(again)
    context.enter(again)
    error = context.error_target
    context.error_target = failed
    value = context.invoke(
        generator, (iterator,), "implicit:anext" if generator.value == "async" else "implicit:next"
    )
    if generator.value == "async":
        value = suspend_value(context, generator, value)
    context.error_target = error
    store(context, generator.one("target"), value)
    for condition in generator.children("ifs"):
        passed = graph.block()
        test = context.truth(condition)
        graph.edge(passed, condition=test)
        graph.edge(again, condition=test, positive=False)
        context.enter(passed)
    if len(generators) > 1:
        nested = generators[1]
        iterable = context.expression(nested.one("iter"))
        inner = context.invoke(
            nested, (iterable,), "implicit:aiter" if nested.value == "async" else "implicit:iter"
        )
        _generator(context, node, generators[1:], inner, accumulator)
    else:
        _accumulate(context, node, accumulator)
    context.jump(again)
    context.enter(failed)
    exception = graph.term("local", value="$exception")
    stop = graph.term(
        "exception_matches",
        (exception,),
        "StopAsyncIteration" if generator.value == "async" else "StopIteration",
        "model:bool",
    )
    graph.edge(exhausted, condition=stop)
    graph.edge(other, condition=stop, positive=False)
    context.enter(other)
    context.terminate("raise", exception, node)
    context.enter(exhausted)


def _accumulate(context: PythonGraph, node: Node, accumulator: int) -> None:
    if node.kind == "dict_comprehension":
        key = context.expression(node.one("key"))
        value = context.expression(node.one("element"))
        context.invoke(node, (accumulator, key, value), "internal:dict_insert")
    else:
        value = context.expression(node.one("element"))
        context.invoke(
            node,
            (accumulator, value),
            "internal:list_append" if node.kind == "list_comprehension" else "internal:set_insert",
        )
