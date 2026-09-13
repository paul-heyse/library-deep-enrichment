"""Ordered match-case evaluation, capture binding and explicit dynamic pattern frontiers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_guides.analyses.behavior.python_graph import PythonGraph
    from library_guides.analyses.behavior.python_nodes import Node


def match_statement(context: PythonGraph, node: Node) -> None:
    """Evaluate a subject once and attempt cases and guards in source order."""
    graph = context.graph
    subject = context.save(context.expression(node.one("subject")), node)
    done = graph.block()
    for case in node.children("cases"):
        matched, following = graph.block(), graph.block()
        _pattern(context, case.one("pattern"), subject, matched, following)
        context.enter(matched)
        if case.children("guard"):
            condition = context.truth(case.one("guard"))
            accepted = graph.block()
            graph.edge(accepted, condition=condition)
            graph.edge(following, condition=condition, positive=False)
            context.enter(accepted)
        context.body(case.children("body"))
        context.jump(done)
        context.enter(following)
    context.jump(done)
    context.enter(done)


def _pattern(context: PythonGraph, node: Node, subject: int, matched: int, failed: int) -> None:
    graph = context.graph
    if node.kind in {"pattern_as", "pattern_star"}:
        if node.children("pattern"):
            bound = graph.block()
            _pattern(context, node.one("pattern"), subject, bound, failed)
            context.enter(bound)
        if node.value:
            graph.emit("assign", destination=node.value, value=subject, span=node.span)
        context.jump(matched)
        return
    if node.kind == "pattern_or":
        alternatives = node.children("patterns")
        for index, alternative in enumerate(alternatives):
            next_ = failed if index == len(alternatives) - 1 else graph.block()
            _pattern(context, alternative, subject, matched, next_)
            if next_ != failed:
                context.enter(next_)
        return
    if node.kind == "pattern_sequence":
        _sequence(context, node, subject, matched, failed)
        return
    if node.kind == "pattern_singleton":
        literal = graph.term(
            "literal", value=node.value, ty="python:none" if node.value == "None" else "python:bool"
        )
        condition = graph.term("is", (subject, literal), ty="model:bool")
    elif node.kind == "pattern_value":
        literal = context.expression(node.one("value"))
        condition = context.evaluate(
            node, graph.term("eq", (subject, literal), ty="model:bool"), "pattern_equality"
        )
    else:
        unknown = context.unknown(node, "pattern_dispatch")
        condition = context.evaluate(
            node, graph.term("truth", (unknown,), ty="model:bool"), "truth"
        )
    graph.edge(matched, condition=condition)
    graph.edge(failed, condition=condition, positive=False)
    context.active = False


def _sequence(context: PythonGraph, node: Node, subject: int, matched: int, failed: int) -> None:
    graph = context.graph
    patterns = node.children("patterns")
    condition = context.invoke(node, (subject,), "implicit:sequence_pattern_protocol")
    condition = context.evaluate(node, graph.term("truth", (condition,), ty="model:bool"), "truth")
    entered = graph.block()
    graph.edge(entered, condition=condition)
    graph.edge(failed, condition=condition, positive=False)
    context.enter(entered)
    length = context.evaluate(node, graph.term("length", (subject,), ty="python:int"), "length")
    starred = next(
        (index for index, item in enumerate(patterns) if item.kind == "pattern_star"), -1
    )
    expected = graph.term("literal", value=str(len(patterns) - int(starred >= 0)), ty="python:int")
    sufficient = graph.term("eq" if starred < 0 else "ge", (length, expected), ty="model:bool")
    unpack = graph.block()
    graph.edge(unpack, condition=sufficient)
    graph.edge(failed, condition=sufficient, positive=False)
    context.enter(unpack)
    for index, item in enumerate(patterns):
        next_ = matched if index == len(patterns) - 1 else graph.block()
        if index == starred:
            value = context.invoke(item, (subject,), "implicit:star_pattern_slice")
        else:
            offset = index if starred < 0 or index < starred else index - len(patterns)
            position = graph.term("literal", value=str(offset), ty="python:int")
            value = context.evaluate(item, graph.term("index", (subject, position)), "subscript")
        _pattern(context, item, value, next_, failed)
        if next_ != matched:
            context.enter(next_)
    if not patterns:
        context.jump(matched)
