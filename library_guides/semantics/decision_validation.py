"""Independent scope and recomputation checks for preferences and counterfactuals."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.contracts import Comparison, Task
from library_guides.semantics.decision_contracts import Counterfactual, PreferencePolicy

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MAX_OBJECTIVES = 16
REVISION_HEX_LENGTH = 64


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return exact dependencies for portable decisions.

    Returns:
        Typed foreign keys, independent of policy descriptions.

    """
    if isinstance(record, PreferencePolicy):
        return tuple(("predicates", item.predicate) for item in record.objectives)
    if isinstance(record, Counterfactual):
        return (
            ("tasks", record.task),
            ("tasks", record.alternative_task),
            ("comparisons", record.baseline),
            ("comparisons", record.alternative),
        )
    if isinstance(record, Task):
        return tuple(
            ("preference_policies", item)
            for item in record.preferences
            if len(item) == REVISION_HEX_LENGTH and all(char in "0123456789abcdef" for char in item)
        )
    return ()


def validate(reader: CorpusReader, record: Record, *, checker: str = "current") -> None:
    """Reject unsupported objective definitions and fabricated comparison deltas.

    Raises:
        CorpusError: A policy or delta does not match the declared computation.

    """
    if isinstance(record, PreferencePolicy):
        if (
            record.strategy not in {"lexicographic", "pareto"}
            or not 1 <= len(record.objectives) <= MAX_OBJECTIVES
        ):
            message = "preference policy needs a supported strategy and 1..16 explicit objectives"
            raise CorpusError(message)
        for objective in record.objectives:
            if objective.direction not in {"minimize", "maximize", "ordered"} or (
                objective.direction == "ordered"
                and (not objective.order or len(set(objective.order)) != len(objective.order))
            ):
                message = "preference objective has an invalid direction or finite ordering"
                raise CorpusError(message)
    if isinstance(record, Counterfactual):
        _delta(reader, record)
    if isinstance(record, Comparison):
        from library_guides.corpus.checker_epochs import HISTORICAL
        from library_guides.semantics.historical_replay import replay as historical_replay
        from library_guides.semantics.task_matching import replay

        task = reader.get("tasks", record.task)
        compute = historical_replay if checker == HISTORICAL else replay
        if not isinstance(task, Task) or compute(reader, task, record) != record:
            message = "comparison differs from its versioned task and exact candidate population"
            raise CorpusError(message)


def _delta(reader: CorpusReader, record: Counterfactual) -> None:
    from library_guides.semantics.task_matching import replay

    task = reader.get("tasks", record.task)
    alternative_task = reader.get("tasks", record.alternative_task)
    if (
        not isinstance(task, Task)
        or not isinstance(alternative_task, Task)
        or not 0 <= record.requirement < len(task.requirements)
    ):
        message = "counterfactual task or requirement is invalid"
        raise CorpusError(message)
    requirements = list(task.requirements)
    if requirements[record.requirement].value != record.before:
        message = "counterfactual input value differs from its baseline"
        raise CorpusError(message)
    requirements[record.requirement] = evolve(requirements[record.requirement], value=record.after)
    if (
        evolve(task, logical_id=alternative_task.logical_id, requirements=tuple(requirements))
        != alternative_task
    ):
        message = "counterfactual silently changed additional task context"
        raise CorpusError(message)
    retained_baseline = reader.get("comparisons", record.baseline)
    retained_alternative = reader.get("comparisons", record.alternative)
    if not isinstance(retained_baseline, Comparison) or not isinstance(
        retained_alternative, Comparison
    ):
        message = "counterfactual requires exact retained comparisons"
        raise CorpusError(message)
    baseline = replay(reader, task, retained_baseline)
    alternative = replay(reader, alternative_task, retained_alternative)
    before = {item.operation for item in baseline.candidates if item.disposition == "eligible"}
    after = {item.operation for item in alternative.candidates if item.disposition == "eligible"}
    if (
        revision_of(baseline) != record.baseline
        or revision_of(alternative) != record.alternative
        or tuple(sorted(after - before)) != record.became_eligible
        or tuple(sorted(before - after)) != record.ceased_eligible
    ):
        message = "counterfactual delta differs from the recomputed candidate comparisons"
        raise CorpusError(message)
