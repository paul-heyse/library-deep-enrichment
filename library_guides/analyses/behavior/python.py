"""Normalize source-backed Ruff owners without executing or importing their source."""

from __future__ import annotations

from library_guides.analyses.behavior.builder import GraphBuilder, Origin
from library_guides.analyses.behavior.contracts import BehaviorProgram, Limits
from library_guides.analyses.behavior.integrity import program_valid, require
from library_guides.analyses.behavior.python_graph import PythonGraph
from library_guides.analyses.behavior.python_nodes import Node, walk

MODEL = "ruff-owned-python-execution.v1"


def _locals(root: Node) -> frozenset[str]:
    result = {item.value for item in root.children("parameters")}
    excluded = set()
    for item in walk(root, descend_functions=False):
        if item.kind in {"global", "nonlocal"}:
            excluded.update(node.value for node in item.children("names"))
        elif (
            item.kind in {"handler", "pattern_as", "pattern_star", "function", "class"}
            and item is not root
        ):
            result.add(item.value)
        for role in ("target", "targets"):
            if item.kind == "generator":
                continue
            for target in item.children(role):
                result.update(_target_names(target))
    return frozenset(result - excluded)


def _target_names(target: Node) -> set[str]:
    if target.kind == "name":
        return {target.value}
    if target.kind in {"tuple", "list"}:
        return set().union(*(_target_names(child) for child in target.children("items")))
    return set()


def normalize(
    origin: Origin, node: Node, limits: Limits, *, phase: str = "invoke"
) -> BehaviorProgram:
    """Project a complete selected owner, keeping unsupported operations explicit.

    Returns:
        An owned graph whose source and context must be checked by admission.

    """
    require("Python behavior requires a function owner", condition=node.kind == "function")
    graph = GraphBuilder(origin, MODEL, limits=limits)
    graph.phase = phase
    if node.children("decorators"):
        graph.unknown(
            "decorated_entry",
            "call_targets",
            str(node.start),
            "this is the source body; decorator application and descriptor dispatch require a binding",
        )
    context = PythonGraph(graph, limits, _locals(node))
    parameters = tuple(item.value for item in node.children("parameters"))
    mode = node.one("mode").kind
    deferred = mode == "async" or any(
        item.kind in {"yield", "yield_from"} for item in walk(node, descend_functions=False)
    )
    if deferred and phase == "invoke":
        graph.unknown(
            "deferred_activation",
            "lifecycle",
            str(node.start),
            "function invocation constructs a deferred owner; activation summary is separate",
        )
        captured = tuple(graph.term("local", value=name) for name in parameters)
        graph.emit("effect", call=("descriptor_allocation", ()), span=node.span)
        graph.emit(
            "return",
            value=graph.term("deferred", captured, value=origin.owner + ":activate"),
            span=node.span,
        )
    else:
        if phase == "activate":
            require("activation requires an async or generator body", condition=deferred)
            graph.unknown(
                "activation_inputs",
                "lifecycle",
                str(node.start),
                "send, throw, cancellation and scheduler conditions remain explicit resumption inputs",
            )
        context.body(node.children("body"))
        if context.active:
            graph.emit(
                "return",
                value=graph.term("literal", value="None", ty="python:none"),
                span=node.span,
            )
    program = graph.finish(parameters)
    program_valid(program, limits)
    return program
