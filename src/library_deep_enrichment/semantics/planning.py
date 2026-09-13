"""Bounded multi-input capability composition with explicit resource and semantic frontiers."""

from __future__ import annotations

from collections import deque
from itertools import islice, product
from typing import TYPE_CHECKING

from attrs import evolve, frozen

from library_deep_enrichment.corpus.contracts import Disposition, Operation, Scope
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.composition_models import evaluate_composition, invocations
from library_deep_enrichment.semantics.conditions import check_condition
from library_deep_enrichment.semantics.contracts import (
    Capability,
    Composition,
    Expression,
    PlanStep,
    Slot,
    State,
    Task,
)
from library_deep_enrichment.semantics.enrichment_contracts import (
    CompositionEvaluation,
    CompositionGoal,
    InvocationContract,
    StateTransfer,
)
from library_deep_enrichment.semantics.task_matching import compare

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_deep_enrichment.corpus.store import CorpusReader


@frozen(kw_only=True)
class PlanBudget:
    """Finite search bounds; exhaustion is never a proof that no composition exists."""

    max_steps: int = 3
    max_states: int = 1000
    max_bindings: int = 32
    max_plans: int = 32


@frozen(kw_only=True)
class AvailableValue:
    """A value's contextual carrier and resource identity, without invented semantic preservation."""

    identity: str
    slot: Slot
    profile: str


@frozen(kw_only=True)
class SearchState:
    """An AND-state containing every currently available input and produced value."""

    values: tuple[AvailableValue, ...]
    steps: tuple[PlanStep, ...]
    used: tuple[str, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class PlanResult:
    """Candidate compositions, independent operation population, and bounded search coverage."""

    scope: Scope
    plans: tuple[Composition, ...]
    visited: int
    disposition: str
    frontier: tuple[str, ...]
    evaluations: tuple[CompositionEvaluation, ...] = ()
    transfers: tuple[StateTransfer, ...] = ()


def _compatible(value: AvailableValue, slot: Slot, profile: str) -> bool:
    if value.profile and value.profile != profile:
        return False
    if slot.resource and value.slot.resource != slot.resource:
        return False
    if slot.representation not in {"", "unknown"} and value.slot.representation not in {
        "",
        "unknown",
        slot.representation,
    }:
        return False
    return (
        not slot.type_expression
        or not value.slot.type_expression
        or slot.type_expression == value.slot.type_expression
    )


def _bindings(
    state: SearchState, capability: Capability, budget: PlanBudget
) -> Iterator[tuple[AvailableValue, ...]]:
    alternatives = [
        tuple(value for value in state.values if _compatible(value, slot, capability.profile))
        for slot in capability.inputs
    ]
    for binding in islice(product(*alternatives), budget.max_bindings):
        consumed = [
            value.identity
            for value, slot in zip(binding, capability.inputs, strict=True)
            if slot.consumes
        ]
        # A consumed resource cannot simultaneously satisfy another argument in this call.
        if any(sum(value.identity == resource for value in binding) > 1 for resource in consumed):
            continue
        yield binding


def _advance(
    state: SearchState,
    capability: Capability,
    binding: tuple[AvailableValue, ...],
    invocation: InvocationContract | None = None,
) -> SearchState:
    ports = capability if invocation is None else invocation
    revision = revision_of(capability)
    inputs = tuple(value.identity for value in binding)
    key = digest([revision, inputs, len(state.steps)])
    outputs = tuple(
        AvailableValue(identity=f"value:{key}:{position}", slot=slot, profile=capability.profile)
        for position, slot in enumerate(ports.outputs)
    )
    consumed = {
        value.identity for value, slot in zip(binding, ports.inputs, strict=True) if slot.consumes
    }
    frontier = list(state.frontier)
    if invocation is not None:
        frontier.extend(invocation.frontier)
    if any(
        not value.slot.type_expression or not slot.type_expression
        for value, slot in zip(binding, ports.inputs, strict=True)
    ):
        frontier.append("An argument has an unresolved carrier type")
    if any(
        value.slot.representation in {"", "unknown"} or slot.representation in {"", "unknown"}
        for value, slot in zip(binding, ports.inputs, strict=True)
    ):
        frontier.append("Representation compatibility remains unresolved")
    return SearchState(
        values=tuple(value for value in state.values if value.identity not in consumed) + outputs,
        steps=(
            *state.steps,
            PlanStep(
                capability=revision,
                inputs=inputs,
                outputs=tuple(value.identity for value in outputs),
            ),
        ),
        used=(*state.used, revision),
        frontier=tuple(sorted(set(frontier))),
    )


def compose(reader: CorpusReader, task: Task, budget: PlanBudget = PlanBudget()) -> PlanResult:
    """Search an AND/OR capability hypergraph; type-compatible paths still need witnesses.

    Returns:
        Bounded candidate plans with exact bindings and unresolved semantic obligations.

    Raises:
        ValueError: A search boundary is nonpositive.

    """
    if min(budget.max_steps, budget.max_states, budget.max_bindings, budget.max_plans) <= 0:
        message = "composition budgets must be positive"
        raise ValueError(message)
    # Initial task values feed the whole graph, not necessarily its final call.
    # Bind each invocation at its actual step; only semantic requirements may
    # eliminate a final operation before intermediate values are constructed.
    scope, comparison = compare(reader, evolve(task, inputs=()))
    scope = evolve(scope, owner=revision_of(task))
    final_states = {item.operation: item.disposition for item in comparison.candidates}
    expressions = {
        revision_of(item): item
        for item in reader.records("expressions")
        if isinstance(item, Expression)
    }
    operations = {
        revision_of(item): item
        for item in reader.records("operations")
        if isinstance(item, Operation)
    }
    capabilities = tuple(
        sorted(
            (
                item
                for item in reader.records("capabilities")
                if isinstance(item, Capability) and item.profile in task.profiles
            ),
            key=revision_of,
        )
    )
    concrete = {
        key: item for key, item in invocations(reader).items() if item.profile in task.profiles
    }
    if concrete:
        capabilities = tuple(item for item in capabilities if revision_of(item) in concrete)
        scope = Scope(
            logical_id=f"invocation-universe:{task.logical_id}",
            profile=task.profile,
            owner=revision_of(task),
            query="Exact approved concrete invocation population in the task profiles",
            members=tuple(sorted({item.operation for item in capabilities})),
            sources=tuple(
                select(item, "/capability", "approved-invocation-population")
                for _, item in sorted(concrete.items())
            ),
            disposition=Disposition.COMPLETE,
            frontier=(
                "Specialization scope; no claim that unmodeled operations cannot provide another plan",
            ),
        )
    initial_profile = task.profiles[0] if len(task.profiles) == 1 else ""
    initial = SearchState(
        values=tuple(
            AvailableValue(
                identity=f"input:{index}:{slot.role}", slot=slot, profile=initial_profile
            )
            for index, slot in enumerate(task.inputs)
        ),
        steps=(),
        used=(),
        frontier=(
            "Native invocation, bounds, ownership, and effects require a matching witness or model",
            "Input semantic properties are not presumed preserved by type compatibility",
        ),
    )
    result = _search(
        PlanInputs(
            task=task,
            scope=scope,
            final_states=final_states,
            capabilities=capabilities,
            expressions=expressions,
            operations=operations,
            invocations=concrete,
        ),
        initial,
        budget,
    )
    return _modeled_results(reader, task, result)


def _modeled_results(reader: CorpusReader, task: Task, result: PlanResult) -> PlanResult:
    goals = tuple(
        item
        for item in reader.records("composition_goals")
        if isinstance(item, CompositionGoal) and item.task == revision_of(task)
    )
    evaluations = [
        evaluate_composition(reader, plan, goal) for plan in result.plans for goal in goals
    ]
    return evolve(
        result,
        evaluations=tuple(item for item, _ in evaluations),
        transfers=tuple(
            {
                revision_of(transfer): transfer
                for _, transfers in evaluations
                for transfer in transfers
            }.values()
        ),
    )


@frozen(kw_only=True)
class PlanInputs:
    """Pinned declarations, conditions, and final semantic assessments for one search."""

    task: Task
    scope: Scope
    final_states: dict[str, str]
    capabilities: tuple[Capability, ...]
    expressions: dict[str, Expression]
    operations: dict[str, Operation]
    invocations: dict[str, InvocationContract]


def _successors(
    inputs: PlanInputs, state: SearchState, budget: PlanBudget
) -> Iterator[tuple[Capability, SearchState]]:
    for capability in inputs.capabilities:
        operation = inputs.operations.get(capability.operation)
        if operation is None:
            continue
        # A syntax example or native catalog entry is not a zero-argument invocation.
        if operation.resolution in {
            "native-registry",
            "registered-syntax-example-not-complete-signature",
            "opaque-callable",
        }:
            continue
        condition = check_condition(
            capability.condition, inputs.expressions, inputs.task.context
        ).state
        if condition in {State.REFUTED, State.CONFLICTING}:
            continue
        invocation = inputs.invocations.get(revision_of(capability))
        callable_capability = (
            capability
            if invocation is None
            else evolve(capability, inputs=invocation.inputs, outputs=invocation.outputs)
        )
        for binding in _bindings(state, callable_capability, budget):
            advanced = _advance(state, capability, binding, invocation)
            if condition != State.SUPPORTED:
                advanced = SearchState(
                    values=advanced.values,
                    steps=advanced.steps,
                    used=advanced.used,
                    frontier=(
                        *advanced.frontier,
                        "Mode applicability is unresolved by known context",
                    ),
                )
            yield capability, advanced


def _connected(steps: tuple[PlanStep, ...]) -> bool:
    needed = set(steps[-1].inputs)
    for step in reversed(steps[:-1]):
        if not needed.intersection(step.outputs):
            return False
        needed.update(step.inputs)
    return True


def _search(inputs: PlanInputs, initial: SearchState, budget: PlanBudget) -> PlanResult:
    queue = deque([initial])
    plans: list[Composition] = []
    visited = 0
    while queue and visited < budget.max_states and len(plans) < budget.max_plans:
        state = queue.popleft()
        visited += 1
        if len(state.steps) >= budget.max_steps:
            continue
        for capability, advanced in _successors(inputs, state, budget):
            if (
                capability.schema == inputs.task.goal
                and inputs.final_states.get(capability.operation) != "rejected"
                and _connected(advanced.steps)
            ):
                binding_key = [
                    (step.capability, step.inputs, step.outputs) for step in advanced.steps
                ]
                plans.append(
                    Composition(
                        logical_id=f"composition:{inputs.task.logical_id}:{digest(binding_key)}",
                        profile=inputs.task.profile,
                        task=revision_of(inputs.task),
                        universe=revision_of(inputs.scope),
                        steps=advanced.steps,
                        assertions=capability.assertions,
                        witnesses=(),
                        disposition="candidate-requires-witness",
                        frontier=advanced.frontier,
                    )
                )
            if len(queue) + visited < budget.max_states:
                queue.append(advanced)
            if len(plans) >= budget.max_plans:
                break
    return PlanResult(
        scope=inputs.scope,
        plans=tuple(plans),
        visited=visited,
        disposition="bounded-candidate-search",
        frontier=(
            "Step, state, binding, and result bounds limit enumeration; an empty result does not establish impossibility",
            "No cross-profile bridge, implicit unwrap, conversion, or resource duplication is synthesized",
            "Registry entries without machine-bindable invocation contracts remain outside executable paths",
        ),
    )
