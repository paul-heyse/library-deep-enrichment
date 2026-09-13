"""Bounded applicability entailment over a partial, explicitly typed use context."""

from __future__ import annotations

from typing import TYPE_CHECKING

import z3
from attrs import frozen

from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.semantics.contracts import (
    Assignment,
    Expression,
    State,
    Value,
    ValueKind,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


MAX_CONDITION_DEPTH = 64


@frozen(kw_only=True)
class ConditionResult:
    """Entailment, not a satisfying assignment chosen to make an option work."""

    state: State
    reason: str
    expressions: tuple[str, ...]


def _constant(value: Value) -> z3.ExprRef:
    if value.kind == ValueKind.INTEGER:
        return z3.IntVal(value.text)
    if value.kind == ValueKind.BOOLEAN and value.text in {"true", "false"}:
        return z3.BoolVal(value.text == "true")
    return z3.StringVal(f"{value.kind}:{value.text}")


def _boolean(value: object) -> z3.BoolRef:
    if not isinstance(value, z3.BoolRef):
        message = "condition compilation did not produce a solver boolean"
        raise CorpusError(message)
    return value


class ConditionCompiler:
    """Compile a finite expression DAG; unknown inputs remain unconstrained."""

    def __init__(self, expressions: Mapping[str, Expression], *, max_nodes: int = 512) -> None:
        """Pin expression revisions and a finite expansion boundary."""
        self.expressions = expressions
        self.max_nodes = max_nodes
        self.visited: set[str] = set()
        self.active: set[str] = set()
        self.variables: dict[str, z3.ExprRef] = {}
        self.compiled: dict[str, z3.BoolRef] = {}

    def variable(self, name: str, value: Value) -> z3.ExprRef:
        """Resolve one consistently typed context variable.

        Returns:
            Its solver expression, without assigning an unobserved value.

        Raises:
            CorpusError: The same variable is used with incompatible scalar kinds.

        """
        expected = _constant(value).sort()
        variable = self.variables.setdefault(name, z3.Const(name, expected))
        if variable.sort() != expected:
            message = f"incompatible condition variable kinds: {name}"
            raise CorpusError(message)
        return variable

    def compile(self, revision: str) -> z3.BoolRef:
        """Compile a boolean condition without Python evaluation of supplied source.

        Returns:
            A finite solver formula.

        Raises:
            CorpusError: A condition is cyclic or uses an unsupported operator.
            BudgetExceededError: The requested DAG exceeds the expansion budget.

        """
        if revision in self.compiled:
            return self.compiled[revision]
        if len(self.active) >= MAX_CONDITION_DEPTH:
            message = "condition nesting exceeds its depth boundary"
            raise BudgetExceededError(message)
        if revision in self.active:
            message = "cyclic applicability expression"
            raise CorpusError(message)
        self.visited.add(revision)
        if len(self.visited) > self.max_nodes:
            message = f"condition expansion exceeds {self.max_nodes} nodes"
            raise BudgetExceededError(message)
        self.active.add(revision)
        node = self.expressions[revision]
        arguments = [self.compile(item) for item in node.arguments]
        self.active.remove(revision)
        result = self._operator(node, arguments)
        self.compiled[revision] = result
        return result

    def _operator(self, node: Expression, arguments: list[z3.BoolRef]) -> z3.BoolRef:
        if node.operator == "all":
            return _boolean(z3.And(*arguments))
        if node.operator == "any":
            return _boolean(z3.Or(*arguments))
        if node.operator == "not" and len(arguments) == 1:
            return _boolean(z3.Not(arguments[0]))
        if node.operator == "equal" and not arguments:
            return _boolean(self.variable(node.variable, node.value) == _constant(node.value))
        if node.operator in {"less", "less_equal", "greater", "greater_equal"} and not arguments:
            return self._ordered(node)
        if node.operator == "constant" and node.value.kind == ValueKind.BOOLEAN:
            return z3.BoolVal(node.value.text == "true")
        message = f"unsupported condition operator/arity: {node.operator}"
        raise CorpusError(message)

    def _ordered(self, node: Expression) -> z3.BoolRef:
        variable = self.variable(node.variable, node.value)
        value = _constant(node.value)
        if (
            node.value.kind != ValueKind.INTEGER
            or not isinstance(variable, z3.ArithRef)
            or not isinstance(value, z3.ArithRef)
        ):
            message = "ordered conditions require canonical integer operands"
            raise CorpusError(message)
        choices = {
            "less": variable < value,
            "less_equal": variable <= value,
            "greater": variable > value,
            "greater_equal": variable >= value,
        }
        return choices[node.operator]


def check_condition(
    revision: str,
    expressions: Mapping[str, Expression],
    context: tuple[Assignment, ...],
    *,
    timeout_ms: int = 2000,
) -> ConditionResult:
    """Prove or refute applicability from known assignments; SAT alone is insufficient.

    Returns:
        Supported, refuted, conflicting, or unknown with explicit solver limitations.

    """
    known: dict[str, Value] = {}
    for assignment in context:
        if assignment.variable in known and known[assignment.variable] != assignment.value:
            return ConditionResult(
                state=State.CONFLICTING,
                reason="Contradictory known context assignments",
                expressions=(),
            )
        known[assignment.variable] = assignment.value
    if not revision:
        return ConditionResult(
            state=State.SUPPORTED, reason="Unconditional model domain", expressions=()
        )
    compiler = ConditionCompiler(expressions)
    formula = compiler.compile(revision)
    solver = z3.Solver()
    solver.set(timeout=timeout_ms)
    for assignment in context:
        solver.add(
            compiler.variable(assignment.variable, assignment.value) == _constant(assignment.value)
        )
    if solver.check() == z3.unsat:
        return ConditionResult(
            state=State.CONFLICTING,
            reason="Contradictory known context assignments",
            expressions=tuple(sorted(compiler.visited)),
        )
    solver.push()
    solver.add(z3.Not(formula))
    counterexample = solver.check()
    solver.pop()
    solver.add(formula)
    feasible = solver.check()
    if counterexample == z3.unsat:
        state, reason = State.SUPPORTED, "Known context entails the condition"
    elif feasible == z3.unsat:
        state, reason = State.REFUTED, "Known context refutes the condition"
    else:
        state, reason = State.UNKNOWN, "Condition is unsettled by known context or solver budget"
    return ConditionResult(state=state, reason=reason, expressions=tuple(sorted(compiler.visited)))
