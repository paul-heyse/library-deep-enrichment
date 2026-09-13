"""Bounded guard consistency; unsupported predicates remain possible rather than false."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define, field

from library_guides.analyses.behavior.contracts import Guard, Term
from library_guides.analyses.behavior.solver import Check, feasible
from library_guides.analyses.behavior.values import integral_type, scalar

if TYPE_CHECKING:
    from library_guides.analyses.behavior.state import State
    from library_guides.analyses.behavior.values import Values

_BINARY_ARITY = 2


@define
class PredicateChecks:
    """Bound solver work across all paths and callees in one interpretation."""

    maximum: int
    timeout_ms: int
    calls: int = 0
    outcomes: dict[Check, int] = field(factory=dict)

    def possible(self, values: Values, state: State) -> bool:
        """Refine only with a fully encoded contradiction.

        Returns:
            False exclusively when all guards were encoded and proved inconsistent.

        """
        if not state.guards:
            return True
        if self.calls >= self.maximum:
            outcome, reason = Check.BUDGET, "query_count"
        else:
            self.calls += 1
            result = feasible(tuple(values.terms), state.guards, timeout_ms=self.timeout_ms)
            outcome, reason = result.state, result.reason
        self.outcomes[outcome] = self.outcomes.get(outcome, 0) + 1
        if outcome not in {Check.FEASIBLE, Check.INFEASIBLE}:
            state.unknown("predicate_" + outcome.value, "predicate", "guard_set", reason)
        return outcome != Check.INFEASIBLE


def assume(
    values: Values, guards: tuple[Guard, ...], value: int, *, positive: bool
) -> tuple[Guard, ...] | None:
    """Refine a path using explicit boolean and identical-predicate contradictions.

    Returns:
        Refined guards, or no path when the modeled predicate is contradictory.

    """
    term = values.terms[value]
    constant = scalar(term)
    if isinstance(constant, bool):
        return guards if constant == positive else None
    if term.op == "not" and len(term.args) == 1:
        return assume(values, guards, term.args[0], positive=not positive)
    guard = Guard(term=value, positive=positive)
    if guard in guards:
        return guards
    return _refine(values, guards, guard)


def _refine(values: Values, guards: tuple[Guard, ...], guard: Guard) -> tuple[Guard, ...] | None:
    term = values.terms[guard.term]
    if Guard(term=guard.term, positive=not guard.positive) in guards:
        return None
    # Split only the logically conjunctive cases; disjunction keeps its explicit expression.
    if (term.op == "and" and guard.positive) or (term.op == "or" and not guard.positive):
        result = guards
        for child in term.args:
            result = assume(values, result, child, positive=guard.positive)
            if result is None:
                return None
        return result
    # Integer equality cases share a symbolic operand. Distinct known constants are incompatible.
    if guard.positive and term.op == "eq" and len(term.args) == _BINARY_ARITY:
        for previous in guards:
            other = values.terms[previous.term]
            if previous.positive and _different_constants(values, term, other):
                return None
    return (*guards, guard)


def _different_constants(values: Values, left: Term, right: Term) -> bool:
    if right.op != "eq" or len(right.args) != _BINARY_ARITY or left.args[0] != right.args[0]:
        return False
    if not integral_type(values.terms[left.args[0]].ty):
        return False
    a, b = scalar(values.terms[left.args[1]]), scalar(values.terms[right.args[1]])
    return a is not None and b is not None and a != b
