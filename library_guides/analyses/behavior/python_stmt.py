"""Owned Python control flow; cleanup and exception paths are explicit graph edges."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.behavior.python_contexts import context_statement
from library_guides.analyses.behavior.python_expr import OPERATORS, store, suspend_value
from library_guides.analyses.behavior.python_graph import Cleanup, Loop
from library_guides.analyses.behavior.python_match import match_statement

if TYPE_CHECKING:
    from library_guides.analyses.behavior.python_graph import PythonGraph
    from library_guides.analyses.behavior.python_nodes import Node


def statement(context: PythonGraph, node: Node) -> None:
    """Compile a statement without conflating lexical successors with execution order."""
    handlers = {
        "assign": _assign,
        "annotated_assign": _annotated,
        "augmented_assign": _augmented,
        "expression": _expression,
        "return": _return,
        "raise": _raise,
        "if": _if,
        "while": _while,
        "for": _for,
        "break": _loop_transfer,
        "continue": _loop_transfer,
        "try": _try,
        "assert": _assert,
        "delete": _delete,
        "function": _function,
        "with": context_statement,
        "match": match_statement,
    }
    if node.kind in {"pass", "global", "nonlocal"}:
        return
    handler = handlers.get(node.kind)
    if handler:
        handler(context, node)
    else:
        context.unknown(node, "control")


def _assign(context: PythonGraph, node: Node) -> None:
    value = context.expression(node.one("value"))
    for target in node.children("targets"):
        store(context, target, value)


def _annotated(context: PythonGraph, node: Node) -> None:
    if node.children("value"):
        store(context, node.one("target"), context.expression(node.one("value")))


def _augmented(context: PythonGraph, node: Node) -> None:
    target = node.one("target")
    if target.kind != "name":
        context.unknown(node, "augmented_assignment")
        return
    previous = context.expression(target)
    value = context.expression(node.one("value"))
    combined = context.graph.term(OPERATORS[node.value], (previous, value))
    result = context.evaluate(node, combined, "inplace:" + node.value)
    store(context, target, result)


def _expression(context: PythonGraph, node: Node) -> None:
    context.expression(node.one("value"))


def _return(context: PythonGraph, node: Node) -> None:
    value = context.save(context.optional(node, "value"), node)
    context.terminate("return", value, node)


def _raise(context: PythonGraph, node: Node) -> None:
    value = (
        context.optional(node, "exception")
        if node.children("exception")
        else context.exceptions[-1]
        if context.exceptions
        else context.graph.term("aggregate", value="RuntimeError")
    )
    context.optional(node, "cause")
    context.terminate("raise", value, node)


def _if(context: PythonGraph, node: Node) -> None:
    graph = context.graph
    done = graph.block()
    for arm in (node, *node.children("alternatives")):
        if arm.children("test"):
            value = context.truth(arm.one("test"))
            yes, no = graph.block(), graph.block()
            graph.edge(yes, condition=value)
            graph.edge(no, condition=value, positive=False)
            context.enter(yes)
            context.body(arm.children("body"))
            context.jump(done)
            context.enter(no)
        else:
            context.body(arm.children("body"))
    context.jump(done)
    context.enter(done)


def _while(context: PythonGraph, node: Node) -> None:
    graph = context.graph
    test, body, exhausted, done = (graph.block() for _ in range(4))
    context.jump(test)
    context.enter(test)
    condition = context.truth(node.one("test"))
    graph.edge(body, condition=condition)
    graph.edge(exhausted, condition=condition, positive=False)
    context.loops = (
        *context.loops,
        Loop(again=test, done=done, cleanup_depth=len(context.cleanups)),
    )
    context.enter(body)
    context.body(node.children("body"))
    context.jump(test)
    context.loops = context.loops[:-1]
    context.enter(exhausted)
    context.body(node.children("else"))
    context.jump(done)
    context.enter(done)


def _for(context: PythonGraph, node: Node) -> None:
    graph = context.graph
    iterable = context.expression(node.one("iter"))
    iterator = context.invoke(
        node, (iterable,), "implicit:aiter" if node.value == "async" else "implicit:iter"
    )
    again, failed, exhausted, done, other = (graph.block() for _ in range(5))
    context.jump(again)
    context.enter(again)
    error = context.error_target
    context.error_target = failed
    value = context.invoke(
        node, (iterator,), "implicit:anext" if node.value == "async" else "implicit:next"
    )
    if node.value == "async":
        value = suspend_value(context, node, value)
    context.error_target = error
    store(context, node.one("target"), value)
    context.loops = (
        *context.loops,
        Loop(again=again, done=done, cleanup_depth=len(context.cleanups)),
    )
    context.body(node.children("body"))
    context.jump(again)
    context.loops = context.loops[:-1]
    context.enter(failed)
    exception = graph.term("local", value="$exception")
    stop = graph.term(
        "exception_matches",
        (exception,),
        "StopAsyncIteration" if node.value == "async" else "StopIteration",
        "model:bool",
    )
    graph.edge(exhausted, condition=stop)
    graph.edge(other, condition=stop, positive=False)
    context.enter(other)
    context.terminate("raise", exception, node)
    context.enter(exhausted)
    context.body(node.children("else"))
    context.jump(done)
    context.enter(done)


def _loop_transfer(context: PythonGraph, node: Node) -> None:
    if not context.loops:
        context.unknown(node, "invalid_loop_transfer")
        return
    loop = context.loops[-1]
    context.cleanup(loop.cleanup_depth)
    context.jump(loop.done if node.kind == "break" else loop.again)


def _try(context: PythonGraph, node: Node) -> None:
    if node.value == "exception_group":
        context.unknown(node, "exception_group_partition")
        return
    graph = context.graph
    dispatch, failed, normal, done = (graph.block() for _ in range(4))
    outer_error, outer_cleanups = context.error_target, context.cleanups
    cleanup = Cleanup(body=node.children("finally"), error_target=outer_error)
    context.cleanups = (*outer_cleanups, cleanup)
    context.error_target = dispatch
    context.body(node.children("body"))
    context.error_target = failed
    context.body(node.children("else"))
    context.jump(normal)
    context.enter(dispatch)
    _handlers(context, node, normal, failed)
    context.error_target = outer_error
    context.enter(failed)
    exception = context.save(graph.term("local", value="$exception"), node)
    exceptions = context.exceptions
    context.exceptions = (*exceptions, exception)
    context.cleanup(len(outer_cleanups))
    context.exceptions = exceptions
    context.cleanups = outer_cleanups
    if context.active:
        context.terminate("raise", exception, node)
    context.enter(normal)
    context.body(cleanup.body)
    context.jump(done)
    context.cleanups, context.error_target = outer_cleanups, outer_error
    context.enter(done)


def _handlers(context: PythonGraph, node: Node, normal: int, failed: int) -> None:
    graph = context.graph
    for handler in node.children("handlers"):
        body, next_handler = graph.block(), graph.block()
        if handler.children("type"):
            kind = context.expression(handler.one("type"))
            match = graph.term(
                "exception_matches",
                (graph.term("local", value="$exception"), kind),
                ty="model:bool",
            )
            graph.edge(body, condition=match)
            graph.edge(next_handler, condition=match, positive=False)
        else:
            graph.edge(body)
        context.enter(body)
        outer_cleanups, outer_exceptions = context.cleanups, context.exceptions
        failed_handler = graph.block()
        context.error_target = failed_handler
        exception = context.save(graph.term("local", value="$exception"), handler)
        context.exceptions = (*outer_exceptions, exception)
        if handler.value:
            graph.emit(
                "assign",
                destination=handler.value,
                value=graph.term("local", value="$exception"),
                span=handler.span,
            )
            context.cleanups = (
                *outer_cleanups,
                Cleanup(body=(), error_target=failed, clear_name=handler.value),
            )
        context.body(handler.children("body"))
        context.cleanup(len(outer_cleanups))
        context.jump(normal)
        context.cleanups, context.exceptions, context.error_target = (
            outer_cleanups,
            outer_exceptions,
            failed,
        )
        context.enter(failed_handler)
        if handler.value:
            graph.emit("storage_dead", destination=handler.value, span=handler.span)
        context.jump(failed)
        context.enter(next_handler)
    context.jump(failed)


def _assert(context: PythonGraph, node: Node) -> None:
    graph = context.graph
    condition = context.truth(node.one("test"))
    good, bad = graph.block(), graph.block()
    graph.edge(good, condition=condition)
    graph.edge(bad, condition=condition, positive=False)
    context.enter(bad)
    message = context.optional(node, "message")
    exception = graph.term("aggregate", (message,), "AssertionError")
    context.terminate("raise", exception, node)
    context.enter(good)


def _delete(context: PythonGraph, node: Node) -> None:
    for target in node.children("targets"):
        if target.kind == "name" and target.value in context.local_names:
            context.graph.emit("storage_dead", destination=target.value, span=target.span)
        else:
            context.unknown(target, "deletion")


def _function(context: PythonGraph, node: Node) -> None:
    decorators = tuple(context.expression(decorator) for decorator in node.children("decorators"))
    for parameter in node.children("parameters"):
        context.optional(parameter, "default")
    value = context.graph.term("deferred", value=str(node.start))
    for decorator in reversed(decorators):
        value = context.invoke(node, (decorator, value), "implicit:decorator_application")
    context.graph.emit("assign", destination=node.value, value=value, span=node.span)
