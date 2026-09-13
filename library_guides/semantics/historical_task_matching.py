"""Constraint-first task matching over an independent operation universe."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.contracts import Disposition, Operation, Scope
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.conditions import check_condition
from library_guides.semantics.contracts import (
    Assertion,
    CandidateResult,
    Capability,
    Comparison,
    Expression,
    Predicate,
    Requirement,
    RequirementResult,
    State,
    Task,
)
from library_guides.semantics.historical_realization import qualified_assertions

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader


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
    matching = [
        cap
        for cap in capabilities
        if cap.operation == revision_of(operation) and cap.schema == task.goal
    ]
    disposition = (
        "rejected" if failures else "conditional" if unknowns or not matching else "eligible"
    )
    return CandidateResult(
        operation=revision_of(operation),
        capability=revision_of(matching[0]) if matching else "",
        disposition=disposition,
        requirements=requirements,
        reversing_conditions=tuple(
            f"Re-evaluate {result.predicate} when required value or applicability changes"
            for result in requirements
            if result.state in {State.SUPPORTED, State.REFUTED}
        ),
    )


def compare(reader: CorpusReader, task: Task) -> tuple[Scope, Comparison]:
    """Compare every profile-selected operation independently of retrieval ranking.

    Returns:
        The exact candidate universe and a constraint-first comparison. Unmapped
        operations remain in the denominator with unresolved dimensions.

    """
    operations = tuple(
        item
        for item in reader.records("operations")
        if isinstance(item, Operation) and item.profile in task.profiles
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
    assertions = qualified_assertions(reader)
    candidates: list[CandidateResult] = []
    for operation in operations:
        applicable = tuple(
            item
            for item in assertions
            if item.subject == revision_of(operation)
            and check_condition(item.condition, expressions, task.context).state == State.SUPPORTED
        )
        results = tuple(
            assess_requirement(item, applicable, predicates[item.predicate])
            for item in task.requirements
        )
        candidates.append(_candidate(operation, task, capabilities, results))
    universe = Scope(
        logical_id=f"universe:{task.logical_id}",
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
    comparison = Comparison(
        logical_id=f"comparison:{task.logical_id}",
        profile=task.profile,
        task=revision_of(task),
        universe=revision_of(universe),
        candidates=tuple(sorted(candidates, key=lambda item: item.operation)),
        disposition="partial",
        preferred=(),
        unresolved=(
            "No universal optimum is asserted; preferences and incomplete semantic coverage are explicit",
            f"Candidate membership digest: {digest(universe.members)}",
        ),
    )
    return universe, comparison
