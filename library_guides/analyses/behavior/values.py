"""Bounded symbolic terms with conservative constant and aggregate simplification."""

from __future__ import annotations

import operator
from typing import TYPE_CHECKING

from attrs import define, field

from library_guides.analyses.behavior.contracts import Term
from library_guides.analyses.behavior.numeric import bounds, ieee_literal, integer_width, wrap
from library_guides.analyses.behavior.sequence_values import fold as fold_sequence
from library_guides.corpus.backend import BudgetExceededError

if TYPE_CHECKING:
    from collections.abc import Callable

_BINARY: dict[str, Callable[[int, int], object]] = {
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "bit_and": operator.and_,
    "bit_or": operator.or_,
    "bit_xor": operator.xor,
}
_COMPARISONS = frozenset({"eq", "ne", "lt", "le", "gt", "ge"})
_IDENTITIES = frozenset({"eq", "le", "ge"})
_DISTINCT = frozenset({"ne", "lt", "gt"})
_MAX_INTEGER_BITS = 4096
_BINARY_ARITY = 2
_BOOL_VALUES = {"true": True, "True": True, "1": True, "false": False, "False": False, "0": False}


def integral_type(ty: str) -> bool:
    """Recognize modeled scalar semantics, never Python annotation guarantees.

    Returns:
        Whether a term has an explicit integral model.

    """
    rust = ty.removeprefix("rust:")
    return ty in {"model:bool", "python:bool", "python:int", "rust:bool"} or (
        ty.startswith("rust:")
        and rust[:1] in {"i", "u"}
        and (integer_width(ty) is not None or rust[1:] == "size")
    )


def scalar(term: Term) -> int | bool | None:
    """Read only explicitly modeled scalar constants.

    Returns:
        An integer/boolean, or no modeled scalar value.

    """
    if term.op != "literal":
        return None
    if term.ty.endswith(":bool"):
        return _BOOL_VALUES.get(term.value)
    if integral_type(term.ty):
        try:
            return int(term.value)
        except ValueError:
            return None
    return None


def _integer_result(value: int, ty: str) -> Term | None:
    if value.bit_length() > _MAX_INTEGER_BITS:
        return None
    if ty.startswith(("rust:i", "rust:u")):
        limits = bounds(ty)
        if limits is None:
            return None
        lower, upper = limits
        if not lower <= value <= upper:
            return None
    return Term(op="literal", value=str(value), ty=ty)


@define
class Values:
    """A finite interned expression DAG shared by one root analysis and its callees."""

    limit: int
    terms: list[Term] = field(factory=list)
    _indices: dict[Term, int] = field(factory=dict)
    _unknown_events: int = 0

    def add(self, term: Term) -> int:
        """Intern a value after safe, language-aware simplification.

        Returns:
            Its analysis-local expression index.

        Raises:
            BudgetExceededError: The finite term budget is exhausted.

        """
        simplified = fold_sequence(self, term)
        if simplified is None:
            simplified = self._simplify(term)
        if isinstance(simplified, int):
            return simplified
        if simplified not in self._indices:
            if len(self.terms) >= self.limit:
                message = "behavior symbolic term limit exhausted"
                raise BudgetExceededError(message)
            self._indices[simplified] = len(self.terms)
            self.terms.append(simplified)
        return self._indices[simplified]

    def unknown(self, reason: str, ty: str = "unknown", *, fresh: bool = False) -> int:
        """Intern an unknown term; unknown is not unreachable.

        Returns:
            An unknown expression index; fresh evaluations do not share value identity.

        """
        if fresh:
            self._unknown_events += 1
            reason += f"#event:{self._unknown_events}"
        return self.add(Term(op="unknown", value=reason, ty=ty))

    def boolean(self, *, value: bool) -> int:
        """Intern an explicit boolean constant.

        Returns:
            The boolean expression index.

        """
        return self.add(Term(op="literal", value="true" if value else "false", ty="model:bool"))

    def immutable(self, index: int) -> bool:
        """Recognize scalar snapshots and by-value aggregates containing only such snapshots.

        Returns:
            Whether an unknown heap mutation cannot change this already evaluated value.

        """
        pending, seen = [index], set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            term = self.terms[current]
            if term.op in {"literal", "function"} or integral_type(term.ty):
                continue
            if term.op == "tuple" or (term.op == "aggregate" and term.ty.startswith("rust:")):
                pending.extend(term.args)
            else:
                return False
        return True

    def _simplify(self, term: Term) -> Term | int:
        if term.op == "exception_matches" and len(term.args) == 1:
            exception = self.terms[term.args[0]]
            if (
                exception.op == "literal"
                and exception.ty == "python:builtin_exception"
                and term.value in {"StopIteration", "StopAsyncIteration"}
            ):
                return Term(
                    op="literal", value=str(exception.value == term.value).lower(), ty="model:bool"
                )
        if (
            term.op in {"checked_add", "checked_sub", "checked_mul"}
            and len(term.args) == _BINARY_ARITY
        ):
            operation = term.op.removeprefix("checked_")
            result = self.add(Term(op=operation, args=term.args, ty=term.ty))
            overflow = self.add(Term(op="overflow_" + operation, args=term.args, ty="model:bool"))
            return Term(op="tuple", args=(result, overflow), ty="model:checked_pair")
        if term.op == "truth" and len(term.args) == 1:
            value = self._truth(term)
            return term if value is None else value
        if term.op in {"field", "index", "downcast"} and term.args:
            updated = self._updated(term)
            if updated is not None:
                return updated
        if len(term.args) == 1:
            projection = self._projection(term)
            if projection is not None:
                return projection
        return self._operation(term)

    def _updated(self, term: Term) -> Term | int | None:
        current = term.args[0]
        while True:
            source = self.terms[current]
            if source.op == "update_" + term.op:
                same = source.value == term.value and source.args[2:] == term.args[1:]
                if same:
                    return source.args[1]
                if term.op == "field":
                    current = source.args[0]
                    continue
            break
        return (
            self.add(Term(op=term.op, args=(current, *term.args[1:]), value=term.value, ty=term.ty))
            if current != term.args[0]
            else None
        )

    def _projection(self, term: Term) -> Term | int | None:
        if term.op == "deref" and len(term.args) == 1:
            source = self.terms[term.args[0]]
            if source.op in {"borrow", "address"} and len(source.args) == 1:
                return source.args[0]
        if term.op == "field" and len(term.args) == 1:
            source = self.terms[term.args[0]]
            if source.op in {"tuple", "aggregate"} and term.value.isdecimal():
                index = int(term.value)
                if index < len(source.args):
                    return source.args[index]
        if term.op == "length" and len(term.args) == 1:
            source = self.terms[term.args[0]]
            if source.op in {"tuple", "list"}:
                return Term(op="literal", value=str(len(source.args)), ty="python:int")
        # A constructor carries a variant index, which is not its discriminant.
        # Explicit repr values and niche layouts forbid folding an index into a tag.
        return None

    def _truth(self, term: Term) -> Term | int | None:
        source = self.terms[term.args[0]]
        if source.ty.endswith(":bool"):
            return term.args[0]
        constant = scalar(source)
        if constant is not None:
            return Term(op="literal", value=str(bool(constant)).lower(), ty="model:bool")
        if source.op == "literal" and source.ty in {"python:none", "python:str"}:
            value = source.ty == "python:str" and bool(source.value)
            return Term(op="literal", value=str(value).lower(), ty="model:bool")
        return None

    def _operation(self, term: Term) -> Term | int:
        if term.op == "not" and len(term.args) == 1:
            source = scalar(self.terms[term.args[0]])
            if isinstance(source, bool):
                return Term(op="literal", value=str(not source).lower(), ty="model:bool")
        if len(term.args) != _BINARY_ARITY:
            return term
        left, right = (self.terms[index] for index in term.args)
        special = self._scalar_special(term, left, right)
        if special is not None:
            return special
        # Reflexivity is unsafe for NaN and arbitrary Python comparison dispatch.
        if (
            term.args[0] == term.args[1]
            and integral_type(left.ty)
            and term.op in _IDENTITIES | _DISTINCT
        ):
            return Term(op="literal", value=str(term.op in _IDENTITIES).lower(), ty="model:bool")
        a, b = scalar(left), scalar(right)
        if term.op in {"and", "or"} and isinstance(a, bool):
            selects_right = a if term.op == "and" else not a
            return term.args[int(selects_right)]
        return self._binary(term, a=a, b=b)

    @staticmethod
    def _scalar_special(term: Term, left: Term, right: Term) -> Term | None:
        if (
            term.op in {"is", "is_not"}
            and left.op == right.op == "literal"
            and left.ty in {"python:none", "python:bool"}
            and right.ty in {"python:none", "python:bool"}
        ):
            identity = left.ty == right.ty and (
                left.ty == "python:none" or scalar(left) == scalar(right)
            )
            return Term(
                op="literal",
                value=str(identity if term.op == "is" else not identity).lower(),
                ty="model:bool",
            )
        if term.op in _COMPARISONS and left.op == right.op == "literal":
            first, second = ieee_literal(left.value, left.ty), ieee_literal(right.value, right.ty)
            if first is not None and second is not None:
                result = {
                    "eq": operator.eq,
                    "ne": operator.ne,
                    "lt": operator.lt,
                    "le": operator.le,
                    "gt": operator.gt,
                    "ge": operator.ge,
                }[term.op](first, second)
                return Term(op="literal", value=str(result).lower(), ty="model:bool")
        a, b = scalar(left), scalar(right)
        operation = term.op.removeprefix("overflow_")
        if a is not None and b is not None and operation in {"add", "sub", "mul"}:
            result = {"add": operator.add, "sub": operator.sub, "mul": operator.mul}[operation](
                a, b
            )
            machine = wrap(result, left.ty)
            if machine is not None:
                value, overflow = machine
                return Term(
                    op="literal",
                    value=str(overflow).lower() if term.op.startswith("overflow_") else str(value),
                    ty=term.ty,
                )
        return None

    @staticmethod
    def _binary(term: Term, *, a: int | bool | None, b: int | bool | None) -> Term:
        if a is None or b is None or term.op not in _BINARY:
            return term
        if max(a.bit_length(), b.bit_length()) > _MAX_INTEGER_BITS:
            return term
        result = _BINARY[term.op](a, b)
        if isinstance(result, bool):
            return Term(op="literal", value=str(result).lower(), ty="model:bool")
        if isinstance(result, int) and term.op not in _COMPARISONS:
            return _integer_result(result, term.ty) or term
        return term

    def render(self, index: int, *, depth: int = 12) -> str:
        """Render a bounded explanation without evaluating source expressions.

        Returns:
            An unambiguous diagnostic expression, never executable source.

        """
        term = self.terms[index]
        if depth <= 0:
            return f"#{index}"
        if not term.args:
            return f"{term.op}({term.value!r}:{term.ty})"
        args = ", ".join(self.render(item, depth=depth - 1) for item in term.args)
        return f"{term.op}[{term.value}]({args})"
