"""Exact objective evidence and counterfactual inputs for portable decision views."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.schemas import revision_of
from library_guides.semantics.conditions import check_condition
from library_guides.semantics.contracts import (
    Assertion,
    Comparison,
    Expression,
    Interpretation,
    State,
    Task,
)
from library_guides.semantics.decision_contracts import Counterfactual, PreferencePolicy
from library_guides.semantics.realization import qualified_assertions

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader


def policies(reader: CorpusReader, comparison: Comparison) -> tuple[PreferencePolicy, ...]:
    """Resolve only explicitly selected policies; unresolved preference text stays unresolved.

    Returns:
        Exact admitted policy revisions used to assess the task.

    """
    task = reader.get("tasks", comparison.task)
    assert isinstance(task, Task)
    result = []
    for revision in task.preferences:
        try:
            policy = reader.get("preference_policies", revision)
        except CorpusError:
            continue
        if isinstance(policy, PreferencePolicy):
            result.append(policy)
    return tuple(result)


def evidence(reader: CorpusReader, comparison: Comparison) -> tuple[Assertion, ...]:
    """Select objective support and refutation with the same applicability boundaries as matching.

    Returns:
        Every comparable or conflicting observation, including evidence outside capability mappings.

    """
    objectives = {
        (objective.predicate, interpretation)
        for policy in policies(reader, comparison)
        for objective in policy.objectives
        for interpretation in objective.interpretations
    }
    if not objectives:
        return ()
    task = reader.get("tasks", comparison.task)
    assert isinstance(task, Task)
    candidates = {
        item.operation for item in comparison.candidates if item.disposition == "eligible"
    }
    expressions = {
        revision_of(item): item
        for item in reader.records("expressions")
        if isinstance(item, Expression)
    }
    witnessed = {item.value.text for item in task.context if item.variable == "witness_scope"}
    return tuple(
        item
        for item in qualified_assertions(reader)
        if item.subject in candidates
        and (item.predicate, item.interpretation) in objectives
        and check_condition(item.condition, expressions, task.context).state == State.SUPPORTED
        and (item.interpretation != Interpretation.WITNESSED or item.scope in witnessed)
    )


def deltas(reader: CorpusReader, comparison: Comparison) -> tuple[Counterfactual, ...]:
    """Find admitted finite changes whose baseline is exactly this comparison.

    Returns:
        Checked deltas without recomputing or inventing alternatives during rendering.

    """
    baseline = revision_of(comparison)
    return tuple(
        sorted(
            (
                item
                for item in reader.records("counterfactuals")
                if isinstance(item, Counterfactual) and item.baseline == baseline
            ),
            key=lambda item: (item.requirement, item.after.text),
        )
    )


def links(reader: CorpusReader, comparison: Comparison) -> Iterator[tuple[str, str]]:
    """Retain the complete non-requirement decision evidence in the same release closure.

    Yields:
        Exact assertion and counterfactual revisions; their typed prerequisites follow normally.

    """
    yield from (("assertions", revision_of(item)) for item in evidence(reader, comparison))
    yield from (("counterfactuals", revision_of(item)) for item in deltas(reader, comparison))
