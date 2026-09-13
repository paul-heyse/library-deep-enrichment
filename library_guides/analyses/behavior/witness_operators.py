"""Correlate operator observations through source-derived value origins and finite operands."""

from __future__ import annotations

from attrs import frozen

from library_guides.analyses.behavior.contracts import BehaviorProgram, BehaviorSummary
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.origins import MODEL, BehaviorOrigins, ValueOrigin
from library_guides.analyses.behavior.witness_context import ObservedCall
from library_guides.analyses.behavior.witness_contracts import Observation
from library_guides.analyses.behavior.witness_values import Concrete, Unresolved, Value
from library_guides.corpus.schemas import revision_of

_MAX_OPERATIONS = 1000
_MAX_COMPARISON_PAIRS = 100_000


def same_operands(left: Value, right: Value) -> bool:
    """Correlate structured operands with explicit opaque identities and a finite graph bound.

    Returns:
        Whether every observed component corresponds; this is not an ownership proof.

    """
    pending = [(left, right)]
    seen: set[tuple[int, int]] = set()
    while pending:
        a, b = pending.pop()
        key = (id(a), id(b))
        if key in seen:
            continue
        seen.add(key)
        if len(seen) > _MAX_COMPARISON_PAIRS or not _compatible(a, b):
            return False
        assert isinstance(a, Concrete)
        assert isinstance(b, Concrete)
        pending.extend(zip(a.children, b.children, strict=True))
    return True


def _compatible(left: Value, right: Value) -> bool:
    if isinstance(left, Unresolved) or isinstance(right, Unresolved):
        return False
    if (left.identity or right.identity) and left.identity != right.identity:
        return False
    if left.kind in {"opaque", "reference"} and not left.identity:
        return False
    return (
        left.kind,
        left.scalar,
        left.definition,
        left.variant,
        left.labels,
        len(left.children),
    ) == (
        right.kind,
        right.scalar,
        right.definition,
        right.variant,
        right.labels,
        len(right.children),
    )


@frozen
class Operators:
    """Finite operator evidence; all potentially compatible origins of a shared value matter."""

    entries: dict[int, tuple[ValueOrigin, ...]]
    observed: dict[int, tuple[ObservedCall, ...]]
    assumptions: frozenset[str]

    def resolve(self, index: int, evaluated: list[Value]) -> Value:
        """Resolve an otherwise unknown operator value without overriding ordinary evaluation.

        Returns:
            A corresponding observed value, or uncertainty about any unexcluded origin.

        """
        results = []
        for entry in self.entries.get(index, ()):
            result = self._entry(entry, evaluated)
            if isinstance(result, Unresolved):
                return result
            if isinstance(result, Concrete):
                results.append(result)
        if not results:
            return Unresolved(reason="no corresponding source operator observation")
        if not all(same_operands(results[0], item) for item in results[1:]):
            return Unresolved(reason="shared value has conflicting observed operator results")
        return results[0]

    def _entry(self, entry: ValueOrigin, evaluated: list[Value]) -> Value | None:
        eligible = _guards(entry, evaluated)
        if eligible is not True:
            return (
                Unresolved(reason="operator origin guard is unresolved")
                if eligible is None
                else None
            )
        if not set(entry.assumptions) <= self.assumptions:
            return Unresolved(
                reason="operator origin assumptions were not qualified by the harness"
            )
        observations = self.observed.get(entry.instruction, ())
        if len(observations) != 1:
            return Unresolved(reason="operator site absent or observed more than once")
        observed = observations[0]
        if len(entry.arguments) != len(observed.arguments) or not all(
            index < len(evaluated) and same_operands(evaluated[index], value)
            for index, value in zip(entry.arguments, observed.arguments, strict=True)
        ):
            return Unresolved(reason="operator operands do not establish correspondence")
        return observed.result


def _guards(entry: ValueOrigin, evaluated: list[Value]) -> bool | None:
    unknown = False
    for guard in entry.guards:
        value = evaluated[guard.term] if guard.term < len(evaluated) else None
        if not isinstance(value, Concrete) or value.kind != "bool":
            unknown = True
        elif (value.scalar == "true") != guard.positive:
            return False
    return None if unknown else True


def context(
    program: BehaviorProgram,
    summary: BehaviorSummary,
    observation: Observation,
    values: tuple[Concrete, ...],
    origins: BehaviorOrigins | None,
) -> Operators:
    """Validate finite operator evidence against the selected instruction/value origin table.

    Returns:
        A bounded context; omitted provenance cannot authorize a value substitution.

    """
    require(
        "operator observations require an invocation identity and a finite event count",
        condition=len(observation.operations) <= _MAX_OPERATIONS
        and (not observation.operations or bool(observation.invocation)),
    )
    require(
        "operator observations require the exact summary origin table",
        condition=not observation.operations or origins is not None,
    )
    if origins is None:
        return Operators({}, {}, frozenset(observation.assumptions))
    require(
        "operator origins belong to another summary/request/profile",
        condition=origins.summary == revision_of(summary)
        and origins.request == summary.request
        and origins.profile == summary.profile
        and origins.model == MODEL,
    )
    entries: dict[int, tuple[ValueOrigin, ...]] = {}
    root = revision_of(program)
    for entry in origins.entries:
        require(
            "operator origin escapes its summary expression table",
            condition=all(
                0 <= index < len(summary.terms)
                for index in (
                    entry.result,
                    *entry.arguments,
                    *(guard.term for guard in entry.guards),
                )
            ),
        )
        if entry.program == root and entry.mode == "ordinary_evaluation":
            entries[entry.result] = (*entries.get(entry.result, ()), entry)
    instructions = {item.index: item for item in program.instructions}
    observed: dict[int, tuple[ObservedCall, ...]] = {}
    for item in observation.operations:
        instruction = instructions.get(item.instruction)
        require(
            "observed operator is not a selected evaluated source operation",
            condition=instruction is not None
            and instruction.op == "evaluate"
            and instruction.target not in {"local_lookup", "global_lookup"}
            and instruction.value >= 0
            and len(item.arguments) == len(program.terms[instruction.value].args),
        )
        require(
            "operator observation escapes its concrete table",
            condition=all(0 <= index < len(values) for index in (*item.arguments, item.result)),
        )
        value = ObservedCall(tuple(values[index] for index in item.arguments), values[item.result])
        observed[item.instruction] = (*observed.get(item.instruction, ()), value)
    return Operators(entries, observed, frozenset(observation.assumptions))
