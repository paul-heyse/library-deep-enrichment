"""Evaluated Python construction state with explicit error, loop and cleanup targets."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define, field, frozen

from library_deep_enrichment.analyses.behavior.builder import GraphBuilder
from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.python_nodes import Node

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import Limits


@frozen(kw_only=True)
class Cleanup:
    """A lexical cleanup with the exception destination outside its own handler."""

    body: tuple[Node, ...]
    error_target: int
    clear_name: str = ""
    exit_value: int = -1
    node: Node | None = None
    asynchronous: bool = False


@frozen(kw_only=True)
class Loop:
    """Loop transfer destinations and the cleanup depth at loop entry."""

    again: int
    done: int
    cleanup_depth: int


@define
class PythonGraph:
    """Compile evaluated operations; this class never imports the analyzed module."""

    graph: GraphBuilder
    limits: Limits
    local_names: frozenset[str]
    error_target: int = -1
    cleanups: tuple[Cleanup, ...] = ()
    loops: tuple[Loop, ...] = ()
    active: bool = True
    call_bindings: dict[tuple[int, int], str] = field(factory=dict)
    exceptions: tuple[int, ...] = ()
    local_slots: dict[str, str] = field(factory=dict)

    def slot(self, name: str) -> str:
        """Resolve an identifier to its lexical storage slot.

        Returns:
            A private comprehension slot or the containing function's local name.

        """
        return self.local_slots.get(name, name)

    def temporary(self) -> str:
        """Allocate a deterministic evaluated-value slot.

        Returns:
            A name that cannot collide with a Python identifier.

        """
        return "$value:" + str(len(self.graph.instructions))

    def save(self, value: int, node: Node) -> int:
        """Capture an expression before later argument or target evaluation.

        Returns:
            A stable local reference to the evaluated value.

        """
        name = self.temporary()
        self.graph.emit("assign", destination=name, value=value, span=node.span)
        return self.graph.term("local", value=name)

    def expression(self, node: Node) -> int:
        """Compile a Ruff expression in Python evaluation order.

        Returns:
            The evaluated result slot.

        """
        from library_deep_enrichment.analyses.behavior.python_expr import expression

        self.check_budget()
        return expression(self, node)

    def optional(self, node: Node, role: str) -> int:
        """Evaluate an optional expression or the language's None value.

        Returns:
            The resulting symbolic expression.

        """
        children = node.children(role)
        return (
            self.expression(children[0])
            if children
            else self.graph.term("literal", value="None", ty="python:none")
        )

    def body(self, nodes: tuple[Node, ...]) -> None:
        """Compile a suite until a definite lexical transfer leaves it."""
        from library_deep_enrichment.analyses.behavior.python_stmt import statement

        for node in nodes:
            if self.active:
                self.check_budget()
                statement(self, node)

    def check_budget(self) -> None:
        """Bound code expansion, including repeated cleanup paths."""
        require(
            "Python execution normalization budget exceeded",
            condition=len(self.graph.instructions) <= self.limits.steps
            and len(self.graph.terms) <= self.limits.terms,
        )

    def enter(self, block: int) -> None:
        """Start constructing a block with an explicit incoming control path."""
        self.graph.current = block
        self.active = True

    def jump(self, block: int) -> None:
        """Add a normal transfer only while a path remains active."""
        if self.active:
            self.graph.edge(block)
        self.active = False

    def invoke(self, node: Node, arguments: tuple[int, ...], target: str = "") -> int:
        """Represent a call and its exceptional continuation.

        Returns:
            A value available only on the call's normal continuation.

        """
        name = self.temporary()
        self.graph.emit("call", destination=name, call=(target, arguments), span=node.span)
        self.continuation()
        return self.graph.term("local", value=name)

    def evaluate(self, node: Node, value: int, operation: str) -> int:
        """Retain a conditional primitive result plus dynamic-dispatch alternatives.

        Returns:
            The result slot with operation semantics still explicitly conditional.

        """
        name = self.temporary()
        self.graph.emit(
            "evaluate", destination=name, value=value, call=(operation, ()), span=node.span
        )
        self.continuation()
        return self.graph.term("local", value=name)

    def continuation(self) -> None:
        """Route successful calls separately from Python exception handling."""
        successor = self.graph.block()
        self.graph.edge(successor)
        if self.error_target >= 0:
            self.graph.edge(self.error_target, kind="error")
        self.enter(successor)

    def truth(self, node: Node) -> int:
        """Evaluate truth conversion, including its possible implicit call.

        Returns:
            A boolean guard expression on the ordinary modeled continuation.

        """
        value = self.expression(node)
        if node.kind in {"boolean", "none", "integer", "string"}:
            return self.graph.term("truth", (value,), ty="model:bool")
        return self.evaluate(node, self.graph.term("truth", (value,), ty="model:bool"), "truth")

    def cleanup(self, depth: int) -> None:
        """Run exited cleanups with correct outer exception and cleanup contexts."""
        original, error = self.cleanups, self.error_target
        for index in reversed(range(depth, len(original))):
            if not self.active:
                break
            item = original[index]
            self.cleanups = original[:index]
            self.error_target = item.error_target
            if item.clear_name:
                self.graph.emit("storage_dead", destination=item.clear_name)
            elif item.exit_value >= 0 and item.node is not None:
                from library_deep_enrichment.analyses.behavior.python_contexts import exit_context

                exit_context(self, item.node, item.exit_value, -1, asynchronous=item.asynchronous)
            else:
                self.body(item.body)
        self.cleanups, self.error_target = original, error

    def terminate(self, kind: str, value: int, node: Node) -> None:
        """Respect finally overrides on returns and route explicit exceptions."""
        if kind == "raise" and self.error_target >= 0:
            self.graph.emit("assign", destination="$exception", value=value, span=node.span)
            self.jump(self.error_target)
            return
        self.cleanup(0)
        if self.active:
            self.graph.emit(kind, value=value, span=node.span)
            self.active = False

    def unknown(self, node: Node, dimension: str) -> int:
        """Retain an unsupported construct with conservative effects and errors.

        Returns:
            An unresolved value on its possible ordinary continuation.

        """
        self.graph.unknown(
            "python_" + node.kind, dimension, str(node.start), "unsupported executable construct"
        )
        return self.invoke(node, (), "unresolved:" + node.kind)
