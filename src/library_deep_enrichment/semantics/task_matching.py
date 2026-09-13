"""Constraint-first task matching over an independent operation universe."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.contracts import Disposition, Operation, Scope
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.evidence import select
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.applicability import inputs as assess_inputs
from library_deep_enrichment.semantics.comparison import choose
from library_deep_enrichment.semantics.conditions import check_condition
from library_deep_enrichment.semantics.contracts import (
    Assertion,
    CandidateResult,
    Capability,
    Comparison,
    Expression,
    Interpretation,
    Predicate,
    Requirement,
    RequirementResult,
    State,
    Task,
)
from library_deep_enrichment.semantics.realization import qualified_assertions

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader


def assess_requirement(
    requirement: Requirement,
    assertions: tuple[Assertion, ...],
    predicate: Predicate,
) -> RequirementResult:
    """Evaluate positive, negative, conflicting, and missing qualified support.

    Returns:
        A typed result; absent observations never become favorable assignments.

    """
    relevant = [
        item
        for item in assertions
        if item.predicate == requirement.predicate
        and item.interpretation in requirement.interpretations
    ]
    positive = [item for item in relevant if item.state == State.SUPPORTED]
    matched = [item for item in positive if item.value == requirement.value]
    different = [item for item in positive if item.value != requirement.value]
    negative = [
        item for item in relevant if item.value == requirement.value and item.state == State.REFUTED
    ]
    if requirement.operator != "equal":
        state, reason = State.UNKNOWN, "Requirement operator needs a qualified comparison model"
    elif any(item.state == State.CONFLICTING for item in relevant):
        state, reason = State.CONFLICTING, "An applicable evidence assessment retains a conflict"
    elif relevant and all(item.state == State.NOT_APPLICABLE for item in relevant):
        state, reason = State.NOT_APPLICABLE, "The qualified assessments exclude this context"
    elif matched and (negative or (predicate.exclusive and different)):
        state, reason = State.CONFLICTING, "Qualified support and incompatible evidence coexist"
    elif matched:
        state, reason = (
            State.SUPPORTED,
            "An applicable qualified assertion satisfies the requirement",
        )
    elif negative or (predicate.exclusive and different):
        state, reason = (
            State.REFUTED,
            "An applicable qualified assertion excludes the required value",
        )
    else:
        state, reason = State.UNKNOWN, "No adequate applicable support or refutation"
    return RequirementResult(
        predicate=requirement.predicate,
        required=requirement.value,
        state=state,
        assertions=tuple(sorted(revision_of(item) for item in relevant)),
        reason=reason,
    )


def _candidate(
    operation: Operation,
    task: Task,
    capabilities: tuple[Capability, ...],
    requirements: tuple[RequirementResult, ...],
) -> CandidateResult:
    failures = [
        result
        for requirement, result in zip(task.requirements, requirements, strict=True)
        if requirement.mandatory and result.state == State.REFUTED
    ]
    unknowns = [
        result
        for requirement, result in zip(task.requirements, requirements, strict=True)
        if requirement.mandatory and result.state != State.SUPPORTED
    ]
    matching = [cap for cap in capabilities if cap.schema == task.goal]
    checked = [(cap, assess_inputs(task, cap)) for cap in matching]
    order = {State.SUPPORTED: 0, State.UNKNOWN: 1, State.REFUTED: 2}
    checked.sort(key=lambda item: (order[item[1].state], revision_of(item[0])))
    selected = checked[0] if checked else None
    input_state = State.UNKNOWN if selected is None else selected[1].state
    disposition = (
        "rejected"
        if failures or input_state == State.REFUTED
        else "conditional"
        if unknowns or input_state != State.SUPPORTED
        else "eligible"
    )
    return CandidateResult(
        operation=revision_of(operation),
        capability=revision_of(selected[0]) if selected else "",
        disposition=disposition,
        requirements=requirements,
        reversing_conditions=tuple(
            f"Re-evaluate {result.predicate} when required value or applicability changes"
            for result in requirements
            if result.state in {State.SUPPORTED, State.REFUTED}
        )
        + (() if selected is None else selected[1].reasons),
    )


def compare(reader: CorpusReader, task: Task) -> tuple[Scope, Comparison]:
    """Compare every profile-selected operation independently of retrieval ranking.

    Returns:
        The exact candidate universe and a constraint-first comparison. Unmapped
        operations remain in the denominator with unresolved dimensions.

    """
    operations = tuple(
        sorted(
            (
                item
                for item in reader.records("operations")
                if isinstance(item, Operation) and item.profile in task.profiles
            ),
            key=revision_of,
        )
    )
    predicates = {
        revision_of(item): item
        for item in reader.records("predicates")
        if isinstance(item, Predicate)
    }
    expressions = {
        revision_of(item): item
        for item in reader.records("expressions")
        if isinstance(item, Expression)
    }
    capabilities = tuple(
        item for item in reader.records("capabilities") if isinstance(item, Capability)
    )
    assertions: dict[str, list[Assertion]] = defaultdict(list)
    for assertion in qualified_assertions(reader):
        assertions[assertion.subject].append(assertion)
    available: dict[str, list[Capability]] = defaultdict(list)
    for capability in capabilities:
        if (
            check_condition(capability.condition, expressions, task.context).state
            == State.SUPPORTED
        ):
            available[capability.operation].append(capability)
    for values in available.values():
        values.sort(key=revision_of)
    witnessed_scopes = {
        item.value.text for item in task.context if item.variable == "witness_scope"
    }
    candidates: list[CandidateResult] = []
    applicable_by_operation: dict[str, tuple[Assertion, ...]] = {}
    for operation in operations:
        applicable = tuple(
            item
            for item in assertions[revision_of(operation)]
            if check_condition(item.condition, expressions, task.context).state == State.SUPPORTED
            and (item.interpretation != Interpretation.WITNESSED or item.scope in witnessed_scopes)
        )
        results = tuple(
            assess_requirement(item, applicable, predicates[item.predicate])
            for item in task.requirements
        )
        applicable_by_operation[revision_of(operation)] = applicable
        candidates.append(
            _candidate(operation, task, tuple(available[revision_of(operation)]), results)
        )
    universe = Scope(
        logical_id=f"universe.v2:{task.logical_id}",
        profile=task.profile,
        owner=revision_of(task),
        query=f"all admitted operations in exact profiles {task.profiles!r}",
        members=tuple(sorted(revision_of(item) for item in operations)),
        sources=tuple(select(item, "/profile", "candidate-universe") for item in operations),
        disposition=Disposition.PARTIAL,
        frontier=(
            "Scope is complete for admitted interfaces; upstream acquisition and unmapped semantics remain independent",
        ),
    )
    preferred, preference_gaps = choose(reader, task, tuple(candidates), applicable_by_operation)
    comparison = Comparison(
        logical_id=f"comparison.v2:{task.logical_id}",
        profile=task.profile,
        task=revision_of(task),
        universe=revision_of(universe),
        candidates=tuple(sorted(candidates, key=lambda item: item.operation)),
        disposition="partial",
        preferred=preferred,
        unresolved=(
            "No universal optimum is asserted; preferences and incomplete semantic coverage are explicit",
            f"Candidate membership digest: {digest(universe.members)}",
            *preference_gaps,
        ),
    )
    return universe, comparison


def replay(reader: CorpusReader, task: Task, comparison: Comparison) -> Comparison:
    """Replay the versioned comparison without changing a published historical computation.

    Returns:
        The reconstructed result under its retained algorithm identity.

    Raises:
        CorpusError: The comparison has no recognized version identity.

    """
    from library_deep_enrichment.corpus.backend import CorpusError
    from library_deep_enrichment.semantics.task_matching_v1 import compare as compare_v1

    if comparison.logical_id == f"comparison:{task.logical_id}":
        return compare_v1(reader, task)[1]
    if comparison.logical_id == f"comparison.v2:{task.logical_id}":
        return compare(reader, task)[1]
    message = "comparison has no supported versioned checker identity"
    raise CorpusError(message)
