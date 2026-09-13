"""Evaluated builtin sequence expansion with explicit mutation, failure and allocation facts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.behavior.contracts import Term
from library_guides.corpus.backend import BudgetExceededError

if TYPE_CHECKING:
    from library_guides.analyses.behavior.state import State
    from library_guides.analyses.behavior.values import Values

_NON_ITERABLE = frozenset(
    {"python:none", "python:bool", "python:int", "python:float_bits", "python:complex_bits"}
)


def expand(values: Values, state: State, source: int, point: str) -> int | None:
    """Snapshot an exact builtin input at its evaluation point, before later expressions run.

    Returns:
        Its ordered tuple contents, a modeled TypeError, or no qualified intrinsic transfer.

    Raises:
        BudgetExceededError: A known string expansion exceeds the finite value budget.

    """
    term = values.terms[source]
    region = state.regions.get(source)
    if region is not None and region.kind == "list":
        result = values.add(
            Term(op="sequence_snapshot", args=(region.contents,), ty="python:tuple")
        )
    elif term.op == "tuple":
        result = source
    elif term.op == "literal" and term.ty == "python:str":
        if len(term.value) > values.limit:
            message = "builtin string expansion exceeds value budget"
            raise BudgetExceededError(message)
        result = values.add(
            Term(
                op="tuple",
                args=tuple(
                    values.add(Term(op="literal", value=character, ty="python:str"))
                    for character in term.value
                ),
                ty="python:tuple",
            )
        )
    elif term.op == "literal" and term.ty in _NON_ITERABLE:
        result = values.add(Term(op="literal", value="TypeError", ty="python:builtin_exception"))
        state.locals["$exception"] = result
        state.flow = "error"
        return result
    else:
        return None
    state.assumptions = tuple(dict.fromkeys((*state.assumptions, "runtime:allocation_succeeds")))
    state.effect("sequence_snapshot", str(source), point)
    state.flow = "returned"
    return result
