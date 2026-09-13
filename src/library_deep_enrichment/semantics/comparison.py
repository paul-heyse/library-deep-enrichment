"""Constraint-preserving preference selection and finite counterfactual reevaluation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve

from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.semantics.contracts import (
    Assertion,
    CandidateResult,
    Predicate,
    State,
    Value,
    ValueKind,
)
from library_deep_enrichment.semantics.decision_contracts import Counterfactual, Objective, PreferencePolicy

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader
    from library_deep_enrichment.semantics.contracts import Task

MAX_COUNTERFACTUALS = 64
MAX_PARETO_CANDIDATES = 500


def _score(objective: Objective, assertions: tuple[Assertion, ...]) -> int | None:
    relevant = [
        item
        for item in assertions
        if item.predicate == objective.predicate
        and item.interpretation in objective.interpretations
    ]
    if not relevant or any(item.state != State.SUPPORTED for item in relevant):
        return None
    values = {item.value for item in relevant}
    if len(values) != 1:
        return None
    value = next(iter(values))
    if objective.direction == "ordered":
        return objective.order.index(value) if value in objective.order else None
    if value.kind == ValueKind.INTEGER and objective.direction in {"minimize", "maximize"}:
        return int(value.text) * (1 if objective.direction == "minimize" else -1)
    return None


def choose(
    reader: CorpusReader,
    task: Task,
    candidates: tuple[CandidateResult, ...],
    assertions: Mapping[str, tuple[Assertion, ...]],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Select only demonstrably non-dominated eligible candidates under explicit objectives.

    Returns:
        A frontier and unresolved tradeoffs. Unknown objective values cannot be optimized away.

    """
    if not task.preferences:
        return (), ()
    if len(task.preferences) != 1:
        return (), (
            "Provide one exact preference-policy revision; opaque preference text is unresolved",
        )
    try:
        policy = reader.get("preference_policies", task.preferences[0])
    except CorpusError:
        return (), ("The requested preference policy is not admitted",)
    if not isinstance(policy, PreferencePolicy) or policy.strategy not in {
        "lexicographic",
        "pareto",
    }:
        return (), ("Unsupported preference strategy",)
    eligible = [item.operation for item in candidates if item.disposition == "eligible"]
    scores = {
        operation: tuple(
            _score(objective, assertions.get(operation, ())) for objective in policy.objectives
        )
        for operation in eligible
    }
    unknown = [operation for operation, values in scores.items() if None in values]
    complete = {
        operation: tuple(value for value in values if value is not None)
        for operation, values in scores.items()
        if None not in values
    }
    if policy.strategy == "pareto" and len(complete) > MAX_PARETO_CANDIDATES:
        return tuple(sorted(eligible)), (
            "Pareto comparison exceeds 500 fully comparable candidates; refine the task constraints",
        )

    if policy.strategy == "lexicographic":
        best = min(complete.values(), default=())
        preferred = [operation for operation, values in complete.items() if values == best]
    else:
        preferred = [
            operation
            for operation, values in complete.items()
            if not any(
                all(a <= b for a, b in zip(other, values, strict=True))
                and any(a < b for a, b in zip(other, values, strict=True))
                for other in complete.values()
            )
        ]
    frontier = tuple(sorted((*unknown, *preferred)))
    unresolved = (
        (
            f"{len(unknown)} eligible candidates lack comparable objective support and remain on the frontier",
        )
        if unknown
        else ()
    )
    return frontier, unresolved


def counterfactuals(reader: CorpusReader, task: Task, *, limit: int = 16) -> Iterator[Record]:
    """Reevaluate declared finite predicate domains with exact alternative comparisons.

    Yields:
        Baseline and alternative tasks, scopes, comparisons, and computed deltas.

    Raises:
        BudgetExceededError: The complete declared adjacent domain exceeds the requested bound.

    """
    from library_deep_enrichment.semantics.task_matching import compare

    changes = []
    for index, requirement in enumerate(task.requirements):
        predicate = reader.get("predicates", requirement.predicate)
        if isinstance(predicate, Predicate):
            changes.extend(
                (index, Value(kind=predicate.value_kind, text=value))
                for value in predicate.allowed_values
                if value != requirement.value.text
            )
    if len(changes) > limit or limit > MAX_COUNTERFACTUALS or limit < 1:
        message = f"adjacent task domain has {len(changes)} cases; explicit counterfactual limit is {limit}"
        raise BudgetExceededError(message)
    scope, baseline = compare(reader, task)
    yield task
    yield scope
    yield baseline
    before = {item.operation for item in baseline.candidates if item.disposition == "eligible"}
    for index, value in changes:
        requirements = list(task.requirements)
        old = requirements[index].value
        requirements[index] = evolve(requirements[index], value=value)
        alternative_task = evolve(
            task,
            logical_id=f"{task.logical_id}:adjacent:{digest([index, value.text])}",
            requirements=tuple(requirements),
        )
        alternative_scope, alternative = compare(reader, alternative_task)
        after = {
            item.operation for item in alternative.candidates if item.disposition == "eligible"
        }
        yield alternative_task
        yield alternative_scope
        yield alternative
        yield Counterfactual(
            logical_id=f"delta:{revision_of(task)}:{index}:{digest(value.text)}",
            profile=task.profile,
            task=revision_of(task),
            baseline=revision_of(baseline),
            alternative_task=revision_of(alternative_task),
            alternative=revision_of(alternative),
            requirement=index,
            before=old,
            after=value,
            became_eligible=tuple(sorted(after - before)),
            ceased_eligible=tuple(sorted(before - after)),
        )
