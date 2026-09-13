"""Recompute value-scoped semantics along finite plans under approved reusable models."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import define, field

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.contracts import Policy
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.contracts import (
    Assignment,
    Capability,
    Composition,
    PlanStep,
    Slot,
    State,
    Task,
)
from library_guides.semantics.enrichment_contracts import (
    CompositionEvaluation,
    CompositionGoal,
    InvocationContract,
    StateTransfer,
    TransferMapping,
)
from library_guides.semantics.transfers import evaluate

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader


def invocations(reader: CorpusReader) -> dict[str, InvocationContract]:
    """Select unambiguous approved concrete invocation contracts.

    Returns:
        Exact capability revisions with one approved contextual specialization.

    Raises:
        CorpusError: Multiple active specializations would require an explicit choice.

    """
    approved = {
        item.subject
        for item in reader.records("policies")
        if isinstance(item, Policy) and item.kind == "invocation-approval"
    }
    selected: dict[str, InvocationContract] = {}
    for record in reader.records("invocation_contracts"):
        if not isinstance(record, InvocationContract) or revision_of(record) not in approved:
            continue
        if record.capability in selected:
            message = "multiple approved invocations need an explicit specialization scope"
            raise CorpusError(message)
        selected[record.capability] = record
    return selected


def _initial(task: Task) -> dict[str, tuple[Assignment, ...]]:
    return {
        f"input:{index}:{slot.role}": tuple(
            Assignment(variable=item.variable.removeprefix(f"input.{slot.role}."), value=item.value)
            for item in task.context
            if item.variable.startswith(f"input.{slot.role}.")
        )
        for index, slot in enumerate(task.inputs)
    }


@define(kw_only=True)
class EvaluationState:
    """Finite replay state; only explicit model outputs enter later argument properties."""

    task: Task
    values: dict[str, tuple[Assignment, ...]]
    slots: dict[str, Slot]
    transfers: list[StateTransfer] = field(factory=list)
    used: list[str] = field(factory=list)
    frontier: list[str] = field(factory=list)
    outputs: tuple[Assignment, ...] = ()


def _mapping(
    reader: CorpusReader, contract: InvocationContract, state: EvaluationState
) -> TransferMapping:
    capability = reader.get("capabilities", contract.capability)
    mapping = reader.get("transfer_mappings", contract.mapping)
    if not isinstance(capability, Capability) or not isinstance(mapping, TransferMapping):
        message = "invocation requires an exact capability and transfer mapping"
        raise CorpusError(message)
    if (
        mapping.operation != capability.operation
        or contract.profile != capability.profile
        or capability.profile not in state.task.profiles
    ):
        message = "composition invocation crosses its exact operation or profile"
        raise CorpusError(message)
    return mapping


def _bindings(state: EvaluationState, contract: InvocationContract, step: PlanStep) -> None:
    if len(step.inputs) != len(contract.inputs) or len(step.outputs) != len(contract.outputs):
        message = "composition invocation has invalid argument arity"
        raise CorpusError(message)
    if any(key not in state.values for key in step.inputs) or any(
        key in state.values for key in step.outputs
    ):
        message = "composition uses an unavailable value or overwrites an existing value"
        raise CorpusError(message)
    for key, slot in zip(step.inputs, contract.inputs, strict=True):
        current = state.slots[key]
        if current.type_expression != slot.type_expression:
            message = "concrete invocation has an incompatible carrier type"
            raise CorpusError(message)
        if slot.consumes and step.inputs.count(key) != 1:
            message = "consumed resource is aliased within an invocation"
            raise CorpusError(message)
        if slot.resource and slot.resource != current.resource:
            message = "invocation has an incompatible resource identity"
            raise CorpusError(message)


def _advance(
    reader: CorpusReader, state: EvaluationState, contract: InvocationContract, step: PlanStep
) -> None:
    mapping = _mapping(reader, contract, state)
    _bindings(state, contract, step)
    arguments = tuple(
        item for item in state.task.context if not item.variable.startswith("input.")
    ) + tuple(
        Assignment(variable=f"{slot.role}.{item.variable}", value=item.value)
        for key, slot in zip(step.inputs, contract.inputs, strict=True)
        for item in state.values[key]
    )
    transfer = evaluate(reader, mapping, arguments)
    state.used.append(revision_of(contract))
    state.transfers.append(transfer)
    state.frontier.extend(transfer.frontier)
    if transfer.condition_state != State.SUPPORTED:
        state.frontier.append("An intermediate model's applicability is unresolved or refuted")
    for key, slot in zip(step.outputs, contract.outputs, strict=True):
        state.values[key] = tuple(
            Assignment(variable=item.variable.removeprefix(f"{slot.role}."), value=item.value)
            for item in transfer.outputs
            if item.variable.startswith(f"{slot.role}.")
        )
        state.slots[key] = slot
    for key, slot in zip(step.inputs, contract.inputs, strict=True):
        if slot.consumes:
            del state.values[key]
    state.outputs = transfer.outputs


def _result(
    state: EvaluationState, composition: Composition, goal: CompositionGoal
) -> CompositionEvaluation:
    known = {item.variable: item.value for item in state.outputs}
    rejected = any(
        item.variable in known and known[item.variable] != item.value for item in goal.required
    )
    missing = any(item.variable not in known for item in goal.required)
    if missing:
        state.frontier.append(
            "The modeled final value does not establish every required semantic property"
        )
    disposition = (
        "rejected"
        if rejected
        else "unresolved"
        if missing or state.frontier
        else "modeled-requires-witness"
    )
    return CompositionEvaluation(
        logical_id=f"composition-evaluation:{revision_of(composition)}:{revision_of(goal)}",
        profile=composition.profile,
        composition=revision_of(composition),
        goal=revision_of(goal),
        invocations=tuple(state.used),
        transfers=tuple(revision_of(item) for item in state.transfers),
        outputs=state.outputs,
        disposition=disposition,
        frontier=tuple(sorted(set(state.frontier))),
    )


def evaluate_composition(
    reader: CorpusReader,
    composition: Composition,
    goal: CompositionGoal,
) -> tuple[CompositionEvaluation, tuple[StateTransfer, ...]]:
    """Propagate only modeled effects through explicit argument/value bindings.

    Returns:
        A checked modeled/rejected/unresolved result and every intermediate state transfer.

    Raises:
        CorpusError: A plan crosses task/profile boundaries or has invalid value bindings.

    """
    task = reader.get("tasks", goal.task)
    if (
        not isinstance(task, Task)
        or composition.task != goal.task
        or task.profile != goal.profile
        or composition.profile != task.profile
    ):
        message = "composition and semantic goal must share the exact task and profile"
        raise CorpusError(message)
    selected = invocations(reader)
    state = EvaluationState(
        task=task,
        values=_initial(task),
        slots={f"input:{index}:{slot.role}": slot for index, slot in enumerate(task.inputs)},
    )
    if not composition.steps:
        state.frontier.append("No operation was evaluated")
    for step in composition.steps:
        contract = selected.get(step.capability)
        if contract is None:
            state.frontier.append(
                "An operation has no unambiguous approved invocation/transfer mapping"
            )
            break
        _advance(reader, state, contract, step)
    return _result(state, composition, goal), tuple(state.transfers)
