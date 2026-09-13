"""Python expression order and implicit operations over retained Ruff roles."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from library_guides.analyses.behavior.python_graph import PythonGraph
    from library_guides.analyses.behavior.python_nodes import Node

OPERATORS = {
    "+": "add",
    "-": "sub",
    "*": "mul",
    "/": "div",
    "//": "floor_div",
    "%": "mod",
    "**": "pow",
    "&": "bit_and",
    "|": "bit_or",
    "^": "bit_xor",
    "<<": "shl",
    ">>": "shr",
    "==": "eq",
    "!=": "ne",
    "<": "lt",
    "<=": "le",
    ">": "gt",
    ">=": "ge",
    "is": "is",
    "is not": "is_not",
    "in": "in",
    "not in": "not_in",
    "not": "not",
    "~": "invert",
}
LITERALS = {
    "boolean": "bool",
    "integer": "int",
    "none": "none",
    "string": "str",
    "float_bits": "float_bits",
    "complex_bits": "complex_bits",
}


def expression(context: PythonGraph, node: Node) -> int:
    """Lower one expression to evaluated slots and explicit call/error boundaries.

    Returns:
        The expression's value on its normal continuation.

    """
    graph = context.graph
    if node.kind in LITERALS:
        return graph.term("literal", value=node.value, ty="python:" + LITERALS[node.kind])
    if node.kind == "name":
        op = "local" if node.value in context.local_names else "global"
        value = graph.term(op, value=context.slot(node.value) if op == "local" else node.value)
        return context.evaluate(node, value, "local_lookup" if op == "local" else "global_lookup")
    if node.kind in {
        "list_comprehension",
        "set_comprehension",
        "dict_comprehension",
        "generator_expression",
    }:
        from library_guides.analyses.behavior.python_comprehensions import comprehension

        return comprehension(context, node)
    handlers = {
        "call": _call,
        "binary": _binary,
        "unary": _unary,
        "boolean_op": _boolean,
        "compare": _compare,
        "if_expression": _conditional,
        "named": _named,
        "attribute": _attribute,
        "subscript": _subscript,
        "tuple": _sequence,
        "list": _sequence,
        "set": _sequence,
        "dict": _dictionary,
        "slice": _slice,
        "lambda": _deferred,
        "yield": _suspend,
        "await": _suspend,
        "yield_from": _suspend,
    }
    handler = handlers.get(node.kind)
    return handler(context, node) if handler else context.unknown(node, "execution")


def _call(context: PythonGraph, node: Node) -> int:
    callee = context.expression(node.one("callee"))
    arguments = tuple(context.expression(item) for item in node.children("arguments"))
    keywords = tuple(context.expression(item.one("value")) for item in node.children("keywords"))
    target = context.call_bindings.get(node.span, "")
    if keywords or any(item.kind == "starred" for item in node.children("arguments")):
        context.graph.unknown(
            "python_argument_binding",
            "calls",
            str(node.start),
            "expanded or keyword binding requires invocation contract",
        )
        target = ""
    # A resolved target uses the exact call contract; otherwise retain the callable value too.
    return context.invoke(node, arguments if target else (callee, *arguments, *keywords), target)


def _binary(context: PythonGraph, node: Node) -> int:
    left = context.expression(node.one("left"))
    right = context.expression(node.one("right"))
    op = OPERATORS.get(node.value)
    if op is None:
        return context.unknown(node, "operator")
    result = context.graph.term(op, (left, right))
    return context.evaluate(node, result, "binary:" + node.value)


def _unary(context: PythonGraph, node: Node) -> int:
    value = context.expression(node.one("value"))
    op = {"-": "neg", "+": "positive", "not": "not", "~": "invert"}[node.value]
    if op == "not":
        value = context.graph.term("truth", (value,), ty="model:bool")
    result = context.graph.term(op, (value,), ty="model:bool" if op == "not" else "unknown")
    return context.evaluate(node, result, "unary:" + node.value)


def _boolean(context: PythonGraph, node: Node) -> int:
    graph = context.graph
    done = graph.block()
    slot = context.temporary()
    items = node.children("values")
    for index, item in enumerate(items):
        value = context.expression(item)
        graph.emit("assign", destination=slot, value=value, span=item.span)
        if index == len(items) - 1:
            context.jump(done)
        else:
            condition = context.evaluate(
                item, graph.term("truth", (value,), ty="model:bool"), "truth"
            )
            again = graph.block()
            graph.edge(again, condition=condition, positive=node.value == "and")
            graph.edge(done, condition=condition, positive=node.value != "and")
            context.enter(again)
    context.enter(done)
    return graph.term("local", value=slot)


def _compare(context: PythonGraph, node: Node) -> int:
    graph = context.graph
    left = context.expression(node.one("left"))
    slot, done = context.temporary(), graph.block()
    items = node.children("comparators")
    for index, item in enumerate(items):
        right = context.expression(item.one("value"))
        comparison = graph.term(OPERATORS[item.value], (left, right), ty="model:bool")
        value = (
            comparison
            if item.value in {"is", "is not"}
            else context.evaluate(item, comparison, "comparison:" + item.value)
        )
        graph.emit("assign", destination=slot, value=value, span=item.span)
        left = right
        if index == len(items) - 1:
            context.jump(done)
        else:
            condition = context.evaluate(
                item, graph.term("truth", (value,), ty="model:bool"), "truth"
            )
            again = graph.block()
            graph.edge(again, condition=condition)
            graph.edge(done, condition=condition, positive=False)
            context.enter(again)
    context.enter(done)
    return graph.term("local", value=slot)


def _conditional(context: PythonGraph, node: Node) -> int:
    graph = context.graph
    condition = context.truth(node.one("test"))
    true, false, done = graph.block(), graph.block(), graph.block()
    graph.edge(true, condition=condition)
    graph.edge(false, condition=condition, positive=False)
    slot = context.temporary()
    for block, role in ((true, "body"), (false, "else")):
        context.enter(block)
        value = context.expression(node.one(role))
        graph.emit("assign", destination=slot, value=value, span=node.span)
        context.jump(done)
    context.enter(done)
    return graph.term("local", value=slot)


def _named(context: PythonGraph, node: Node) -> int:
    value = context.expression(node.one("value"))
    store(context, node.one("target"), value)
    return value


def _attribute(context: PythonGraph, node: Node) -> int:
    base = context.expression(node.one("value"))
    value = context.graph.term("field", (base,), node.value)
    return context.evaluate(node, value, "attribute")


def _subscript(context: PythonGraph, node: Node) -> int:
    base = context.expression(node.one("value"))
    index = context.expression(node.one("index"))
    value = context.graph.term("index", (base, index))
    return context.evaluate(node, value, "subscript")


def _sequence(context: PythonGraph, node: Node) -> int:
    if node.kind in {"tuple", "list"} and any(
        item.kind == "starred" for item in node.children("items")
    ):
        return _expanded_sequence(context, node)
    values = tuple(context.expression(item) for item in node.children("items"))
    result = context.graph.term(node.kind, values)
    return (
        context.evaluate(node, result, "set_construction")
        if node.kind == "set"
        else context.save(result, node)
    )


def _expanded_sequence(context: PythonGraph, node: Node) -> int:
    segments = []
    for item in node.children("items"):
        if item.kind == "starred":
            value = context.expression(item.one("value"))
            snapshot = context.graph.term("sequence_snapshot", (value,), ty="python:tuple")
            segments.append(context.evaluate(item, snapshot, "sequence_expansion"))
        else:
            value = context.expression(item)
            segments.append(context.graph.term("tuple", (value,), ty="python:tuple"))
    result = context.graph.term("sequence_concat", tuple(segments), ty="python:tuple")
    if node.kind == "list":
        result = context.graph.term("list_from_sequence", (result,), ty="python:list")
    return context.save(result, node)


def _dictionary(context: PythonGraph, node: Node) -> int:
    items = []
    for item in node.children("items"):
        if not item.children("key"):
            context.unknown(item, "mapping_expansion")
        items.append(context.optional(item, "key"))
        items.append(context.expression(item.one("value")))
    return context.evaluate(
        node, context.graph.term("dict", tuple(items)), "dictionary_construction"
    )


def _slice(context: PythonGraph, node: Node) -> int:
    values = tuple(context.optional(node, role) for role in ("lower", "upper", "step"))
    return context.save(context.graph.term("slice_descriptor", values), node)


def _deferred(context: PythonGraph, node: Node) -> int:
    for parameter in node.children("parameters"):
        if parameter.children("default"):
            context.optional(parameter, "default")
    context.graph.unknown(
        "deferred_activation",
        "lifecycle",
        str(node.start),
        "construction does not activate the retained body",
    )
    return context.save(context.graph.term("deferred", value=f"{node.kind}:{node.start}"), node)


def _suspend(context: PythonGraph, node: Node) -> int:
    value = context.optional(node, "value")
    if node.kind in {"await", "yield_from"}:
        value = context.invoke(node, (value,), "implicit:" + node.kind)
    return suspend_value(context, node, value)


def suspend_value(context: PythonGraph, node: Node, value: int) -> int:
    """Suspend an evaluated await/yield operation with explicit injected-error cleanup.

    Returns:
        The unresolved resume value under its activation obligation.

    """
    context.graph.emit("suspend", value=value, span=node.span)
    successor = context.graph.block()
    context.graph.edge(successor, kind="resume")
    cancelled = context.graph.block()
    context.graph.edge(cancelled, kind="cancel")
    context.enter(cancelled)
    error = context.graph.unknown(
        "injected_exception",
        "lifecycle",
        str(node.start),
        "throw, close or cancellation can inject an exception",
    )
    context.terminate("raise", error, node)
    context.enter(successor)
    return context.graph.unknown(
        "resumption_input",
        "value",
        str(node.start),
        "send/throw/cancellation values require activation context",
    )


def store(context: PythonGraph, node: Node, value: int) -> None:
    """Evaluate assignment targets after the RHS, retaining implicit mutation boundaries."""
    graph = context.graph
    if node.kind == "name" and node.value in context.local_names:
        graph.emit("assign", destination=context.slot(node.value), value=value, span=node.span)
    elif node.kind in {"tuple", "list"}:
        context.evaluate(node, graph.term("length", (value,)), "unpack")
        for index, item in enumerate(node.children("items")):
            part = graph.term("field", (value,), str(index))
            store(context, item, part)
    elif node.kind in {"attribute", "subscript"}:
        base = context.expression(node.one("value"))
        if node.kind == "attribute":
            target = graph.term("field", (base,), node.value)
        else:
            target = graph.term("index", (base, context.expression(node.one("index"))))
        context.evaluate(node, value, "assignment:" + node.kind)
        graph.emit("write", value=value, call=("", (target,)), span=node.span)
    else:
        context.unknown(node, "assignment")
