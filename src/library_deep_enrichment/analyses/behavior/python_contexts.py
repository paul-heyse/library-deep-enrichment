"""Context entry, LIFO exit, suppression and abrupt cleanup from owned Python facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.python_expr import store, suspend_value
from library_deep_enrichment.analyses.behavior.python_graph import Cleanup

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.python_graph import PythonGraph
    from library_deep_enrichment.analyses.behavior.python_nodes import Node


def _await(context: PythonGraph, node: Node, value: int) -> int:
    return suspend_value(context, node, value)


def exit_context(
    context: PythonGraph, node: Node, exit_value: int, exception: int, *, asynchronous: bool
) -> int:
    """Invoke the previously acquired exit operation with normal or exceptional arguments.

    Returns:
        Its possible suppression result, with errors routed to the enclosing handler.

    """
    graph = context.graph
    none = graph.term("literal", value="None", ty="python:none")
    error = none if exception < 0 else exception
    kind = none if exception < 0 else graph.term("field", (exception,), "exception_type")
    trace = none if exception < 0 else graph.term("field", (exception,), "traceback")
    value = context.invoke(
        node,
        (exit_value, kind, error, trace),
        "implicit:context_aexit" if asynchronous else "implicit:context_exit",
    )
    return _await(context, node, value) if asynchronous else value


def context_statement(context: PythonGraph, node: Node) -> None:
    """Lower nested context items with entry failures outside the new cleanup scope."""
    _items(context, node, node.children("items"))


def _items(context: PythonGraph, node: Node, items: tuple[Node, ...]) -> None:
    if not items:
        context.body(node.children("body"))
        return
    item = items[0]
    graph = context.graph
    asynchronous = node.value == "async"
    manager = context.expression(item.one("context"))
    enter = context.invoke(item, (manager,), "implicit:context_enter_lookup")
    exit_value = context.invoke(item, (manager,), "implicit:context_exit_lookup")
    entered = context.invoke(
        item,
        (enter, manager),
        "implicit:context_aenter" if asynchronous else "implicit:context_enter",
    )
    if asynchronous:
        entered = _await(context, item, entered)
    outer_error, outer_cleanups = context.error_target, context.cleanups
    failed, done = graph.block(), graph.block()
    context.cleanups = (
        *outer_cleanups,
        Cleanup(
            body=(),
            error_target=outer_error,
            exit_value=exit_value,
            node=item,
            asynchronous=asynchronous,
        ),
    )
    context.error_target = failed
    if item.children("target"):
        store(context, item.one("target"), entered)
    _items(context, node, items[1:])
    context.cleanup(len(outer_cleanups))
    context.jump(done)
    context.cleanups, context.error_target = outer_cleanups, outer_error
    context.enter(failed)
    exception = context.save(graph.term("local", value="$exception"), item)
    suppressed = exit_context(context, item, exit_value, exception, asynchronous=asynchronous)
    truth = context.evaluate(item, graph.term("truth", (suppressed,), ty="model:bool"), "truth")
    propagate = graph.block()
    graph.edge(done, condition=truth)
    graph.edge(propagate, condition=truth, positive=False)
    context.enter(propagate)
    context.terminate("raise", exception, item)
    context.enter(done)
