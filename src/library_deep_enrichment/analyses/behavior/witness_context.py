"""Correlate finite invocation observations without promoting them to static bindings."""

from __future__ import annotations

from attrs import frozen

from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Term
from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.witness_contracts import Observation
from library_deep_enrichment.analyses.behavior.witness_values import (
    Concrete,
    Unresolved,
    Value,
    equality,
)


@frozen
class ObservedCall:
    """An observed call entry/result pair; effects and callee behavior remain unqualified."""

    arguments: tuple[Concrete, ...]
    result: Concrete


@frozen
class Invocation:
    """Finite runtime evidence scoped to one source-backed program invocation."""

    globals: dict[str, Concrete]
    calls: dict[str, tuple[ObservedCall, ...]]

    def call(self, term: Term, arguments: tuple[Value, ...]) -> Value:
        """Correlate only a single observed execution of an explicit unresolved call site.

        Returns:
            Its separately observed result, or uncertainty about event/argument alignment.

        """
        candidates = self.calls.get(term.value, ())
        if len(candidates) != 1:
            return Unresolved(reason="call site absent or executed more than once")
        candidate = candidates[0]
        if len(arguments) != len(candidate.arguments) or not all(
            _same_argument(left, right)
            for left, right in zip(arguments, candidate.arguments, strict=True)
        ):
            return Unresolved(reason="observed call arguments do not establish correspondence")
        return candidate.result


def _same_argument(left: Value, right: Concrete) -> bool:
    if isinstance(left, Unresolved):
        return False
    # Identity is used only to correlate an opaque argument. It does not check its
    # contents, and does not establish an alias/ownership or lifetime guarantee.
    if left.kind == right.kind == "opaque":
        return bool(left.identity) and left.identity == right.identity
    if (left.identity or right.identity) and left.identity != right.identity:
        return False
    return equality(left, right) is True


def context(
    program: BehaviorProgram, observation: Observation, values: tuple[Concrete, ...]
) -> Invocation:
    """Validate optional dynamic observations against the exact selected source program.

    Returns:
        A finite context; repeated call sites retain ambiguity rather than choosing an event.

    """
    require(
        "runtime observations require an invocation identity",
        condition=not (observation.globals or observation.calls) or bool(observation.invocation),
    )
    names = [item.name for item in observation.globals]
    available = {term.value for term in program.terms if term.op == "global"}
    require(
        "runtime globals repeat or escape the selected program",
        condition=len(names) == len(set(names)) and set(names) <= available,
    )
    indices = [item.value for item in observation.globals]
    indices.extend(index for item in observation.calls for index in (*item.arguments, item.result))
    require(
        "runtime observation escapes its concrete value table",
        condition=all(0 <= index < len(values) for index in indices),
    )
    instructions = {item.index: item for item in program.instructions}
    calls: dict[str, tuple[ObservedCall, ...]] = {}
    for item in observation.calls:
        instruction = instructions.get(item.instruction)
        require(
            "observed call is not an explicit unresolved source call",
            condition=instruction is not None
            and instruction.op == "call"
            and not instruction.target
            and len(item.arguments) == len(instruction.arguments),
        )
        point = f"{program.owner}:{item.instruction}"
        call = ObservedCall(tuple(values[index] for index in item.arguments), values[item.result])
        calls[point] = (*calls.get(point, ()), call)
    return Invocation({item.name: values[item.value] for item in observation.globals}, calls)
