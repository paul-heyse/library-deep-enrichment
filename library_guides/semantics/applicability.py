"""Finite call-input compatibility; unspecified semantics remain explicit unknowns."""

from __future__ import annotations

from attrs import frozen

from library_guides.semantics.contracts import Capability, Slot, State, Task

MAX_INPUTS = 32
MAX_BINDING_STATES = 4096
UNKNOWN = frozenset({"", "unknown", "Any", "typing.Any"})


@frozen(kw_only=True)
class Applicability:
    """An exact finite matching outcome, never a runtime invocation guarantee."""

    state: State
    reasons: tuple[str, ...]


def _pair(available: Slot, required: Slot) -> State:
    unknown = False
    for actual, expected in (
        (available.type_expression, required.type_expression),
        (available.representation, required.representation),
    ):
        if actual in UNKNOWN or expected in UNKNOWN:
            unknown = True
        elif actual != expected:
            return State.REFUTED
    if required.resource:
        if not available.resource:
            unknown = True
        elif available.resource != required.resource:
            return State.REFUTED
    if required.consumes and not available.consumes:
        return State.REFUTED
    return State.UNKNOWN if unknown else State.SUPPORTED


def _reused_consumption(ports: tuple[Slot, ...], used: tuple[int, ...], index: int) -> bool:
    prior = [port for port, source in enumerate(used) if source == index]
    return bool(prior) and (
        ports[len(used)].consumes or any(ports[port].consumes for port in prior)
    )


def inputs(task: Task, capability: Capability) -> Applicability:
    """Check all required inputs together, including duplicate consumed resources.

    Returns:
        Supported, refuted, or unknown structural applicability with a finite-search reason.

    """
    if not task.inputs:
        return Applicability(
            state=State.SUPPORTED,
            reasons=("No concrete call inputs requested; eligibility is a semantic choice only",),
        )
    if max(len(task.inputs), len(capability.inputs)) > MAX_INPUTS:
        return Applicability(state=State.UNKNOWN, reasons=("Input matching exceeds 32 slots",))
    if not capability.inputs:
        return Applicability(
            state=State.UNKNOWN,
            reasons=("No required input contract maps the supplied task values",),
        )
    return _search(task, capability)


def _search(task: Task, capability: Capability) -> Applicability:
    # State retains every use, so a consumed value cannot also satisfy another port.
    pending: list[tuple[int, tuple[int, ...], bool]] = [(0, (), False)]
    visited, possible = 0, False
    while pending:
        position, used, uncertain = pending.pop()
        visited += 1
        if visited > MAX_BINDING_STATES:
            return Applicability(
                state=State.UNKNOWN,
                reasons=("Input binding exceeded 4096 states; refine the task input contract",),
            )
        if position == len(capability.inputs):
            if not uncertain:
                return Applicability(
                    state=State.SUPPORTED,
                    reasons=(
                        "Every required port has a compatible type, representation, and resource binding",
                    ),
                )
            possible = True
            continue
        required = capability.inputs[position]
        for index, available in enumerate(task.inputs):
            if _reused_consumption(capability.inputs, used, index):
                continue
            state = _pair(available, required)
            if state != State.REFUTED:
                pending.append((position + 1, (*used, index), uncertain or state == State.UNKNOWN))
    return Applicability(
        state=State.UNKNOWN if possible else State.REFUTED,
        reasons=(
            "Input type or representation remains unresolved"
            if possible
            else "No binding satisfies all required types, representations, ownership, and resource identities",
        ),
    )
