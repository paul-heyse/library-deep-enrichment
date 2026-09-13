"""A bounded predicate helper; unencoded semantics never become unsatisfiable paths."""

from __future__ import annotations

from enum import StrEnum

import z3
from attrs import define, field, frozen

from library_guides.analyses.behavior.contracts import Guard, Term
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.numeric import bounds, integer_width
from library_guides.analyses.behavior.values import scalar

_BINARY_ARITY = 2
_MAX_TIMEOUT_MS = 30_000
_MAX_NODES = 100_000
_MAX_RESOURCES = 1_000_000
_ATOMS = frozenset({"argument", "field", "index", "deref", "global", "unknown", "discriminant"})


class Check(StrEnum):
    """Solver outcomes, separate from a program's execution outcomes."""

    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    BUDGET = "budget_exhausted"


@frozen(kw_only=True)
class QueryResult:
    """A finite predicate check, with a reason for every inconclusive state."""

    state: Check
    reason: str
    encoded_nodes: int


def width(ty: str) -> int | None:
    """Recognize only explicit machine integer widths, never guess usize from the host.

    Returns:
        A supported bit width, or no integer-width model.

    """
    return integer_width(ty)


def _atom(term: Term, index: int) -> z3.ExprRef | None:
    bits = width(term.ty)
    if term.ty.endswith(":bool"):
        return z3.Bool(f"v{index}")
    if bits is not None:
        return z3.BitVec(f"v{index}", bits)
    if term.ty == "python:int":
        return z3.Int(f"v{index}")
    return None


def _literal(term: Term) -> z3.ExprRef | None:
    value = scalar(term)
    if isinstance(value, bool):
        return z3.BoolVal(value)
    if value is None:
        return None
    bits = width(term.ty)
    if bits is not None:
        signed = term.ty.startswith("rust:i")
        if not (-(1 << (bits - 1)) if signed else 0) <= value < (1 << (bits - int(signed))):
            return None
        return z3.BitVecVal(value, bits)
    return z3.IntVal(value) if term.ty == "python:int" else None


@define
class Encoder:
    """Encode only the dependency slice needed by the finite selected guards."""

    terms: tuple[Term, ...]
    limit: int
    values: dict[int, z3.ExprRef | None] = field(factory=dict)
    exhausted: bool = False

    def get(self, index: int) -> z3.ExprRef | None:
        """Compile an acyclic term slice without evaluating source or recursing deeply.

        Returns:
            A typed formula, or an explicitly unsupported expression.

        """
        pending = [(index, False)]
        while pending:
            current, visited = pending.pop()
            require(
                "solver expression reference is outside the term table",
                condition=0 <= current < len(self.terms),
            )
            if current in self.values:
                continue
            if len(self.values) >= self.limit:
                self.exhausted = True
                return None
            term = self.terms[current]
            if not visited:
                require(
                    "solver requires acyclic expressions",
                    condition=all(0 <= child < current for child in term.args),
                )
                pending.append((current, True))
                pending.extend((child, False) for child in reversed(term.args))
            else:
                self.values[current] = self._expression(term, current)
        return self.values[index]

    def _expression(self, term: Term, index: int) -> z3.ExprRef | None:
        if term.op == "literal":
            return _literal(term)
        if term.op in _ATOMS:
            return _atom(term, index)
        arguments = tuple(self.values[child] for child in term.args)
        if len(arguments) == 1:
            return _unary(term, arguments[0])
        if len(arguments) != _BINARY_ARITY or any(item is None for item in arguments):
            return None
        left, right = arguments
        assert left is not None
        assert right is not None
        return self._binary_expression(term, left, right)

    def _binary_expression(
        self, term: Term, left: z3.ExprRef, right: z3.ExprRef
    ) -> z3.ExprRef | None:
        if term.op.startswith("overflow_"):
            return _overflow(term.op, left, right, self.terms[term.args[0]].ty)
        if term.op in {"eq", "ne"} and left.sort() == right.sort():
            return _expression_result(left == right if term.op == "eq" else left != right)
        unsigned = self.terms[term.args[0]].ty.startswith("rust:u")
        return _binary(term.op, left, right, unsigned=unsigned)


def _expression_result(value: object) -> z3.ExprRef | None:
    return value if isinstance(value, z3.ExprRef) else None


def _overflow(op: str, left: z3.ExprRef, right: z3.ExprRef, ty: str) -> z3.ExprRef | None:
    limits = bounds(ty)
    if (
        limits is None
        or not isinstance(left, z3.BitVecRef)
        or not isinstance(right, z3.BitVecRef)
        or left.size() != right.size()
    ):
        return None
    a = z3.BV2Int(left, is_signed=ty.startswith("rust:i"))
    b = z3.BV2Int(right, is_signed=ty.startswith("rust:i"))
    result = _numeric(op.removeprefix("overflow_"), a, b)
    if not isinstance(result, z3.ArithRef):
        return None
    return _expression_result(z3.Or(result < limits[0], result > limits[1]))


def _unary(term: Term, value: z3.ExprRef | None) -> z3.ExprRef | None:
    if term.op == "not" and isinstance(value, z3.BoolRef):
        return _expression_result(z3.Not(value))
    if term.op == "truth":
        if isinstance(value, z3.BoolRef):
            return value
        if isinstance(value, (z3.ArithRef, z3.BitVecRef)):
            return _expression_result(value != 0)
    if term.op == "neg" and isinstance(value, (z3.ArithRef, z3.BitVecRef)):
        return -value
    if term.op == "invert" and isinstance(value, z3.BitVecRef):
        return ~value
    return None


def _binary(op: str, left: z3.ExprRef, right: z3.ExprRef, *, unsigned: bool) -> z3.ExprRef | None:
    if isinstance(left, z3.BoolRef) and isinstance(right, z3.BoolRef):
        return _expression_result(
            {"and": lambda: z3.And(left, right), "or": lambda: z3.Or(left, right)}.get(
                op, lambda: None
            )()
        )
    if (
        isinstance(left, z3.BitVecRef)
        and isinstance(right, z3.BitVecRef)
        and left.size() == right.size()
    ):
        if unsigned and op in {"lt", "le", "gt", "ge"}:
            return {"lt": z3.ULT, "le": z3.ULE, "gt": z3.UGT, "ge": z3.UGE}[op](left, right)
        return _numeric(op, left, right)
    if isinstance(left, z3.ArithRef) and isinstance(right, z3.ArithRef):
        return _numeric(op, left, right)
    return None


def _numeric(
    op: str, left: z3.ArithRef | z3.BitVecRef, right: z3.ArithRef | z3.BitVecRef
) -> z3.ExprRef | None:
    operations = {
        "add": lambda: left + right,
        "sub": lambda: left - right,
        "mul": lambda: left * right,
        "lt": lambda: left < right,
        "le": lambda: left <= right,
        "gt": lambda: left > right,
        "ge": lambda: left >= right,
    }
    return _expression_result(operations.get(op, lambda: None)())


def feasible(
    terms: tuple[Term, ...],
    guards: tuple[Guard, ...],
    *,
    timeout_ms: int,
    node_limit: int = 10000,
    resource_limit: int = 100000,
) -> QueryResult:
    """Check supported guard constraints under independent finite solver budgets.

    Returns:
        Feasible/infeasible only for a fully encoded query; all other states stay explicit.

    """
    require(
        "solver budgets must be positive",
        condition=0 < timeout_ms <= _MAX_TIMEOUT_MS
        and 0 < node_limit <= _MAX_NODES
        and 0 < resource_limit <= _MAX_RESOURCES,
    )
    encoder = Encoder(terms, node_limit)
    constraints = []
    for guard in guards:
        value = encoder.get(guard.term)
        if not isinstance(value, z3.BoolRef):
            return QueryResult(
                state=Check.BUDGET if encoder.exhausted else Check.UNSUPPORTED,
                reason="node_limit" if encoder.exhausted else "predicate_not_encoded",
                encoded_nodes=len(encoder.values),
            )
        constraints.append(value if guard.positive else z3.Not(value))
    solver = z3.Solver()
    solver.set(timeout=timeout_ms, rlimit=resource_limit)
    solver.add(*constraints)
    state = solver.check()
    result = (
        Check.INFEASIBLE
        if state == z3.unsat
        else Check.FEASIBLE
        if state == z3.sat
        else Check.UNKNOWN
    )
    return QueryResult(
        state=result,
        reason=solver.reason_unknown() if result == Check.UNKNOWN else "",
        encoded_nodes=len(encoder.values),
    )
