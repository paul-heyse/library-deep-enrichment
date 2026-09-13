"""Owner-level analysis outcomes; budget exhaustion is evidence about work, not behavior."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.analyses.behavior.contracts import BehaviorRequest, Metric
from library_deep_enrichment.analyses.behavior.engine import Interpreter
from library_deep_enrichment.analyses.behavior.fixedpoints import solve
from library_deep_enrichment.analyses.behavior.projection_budget import ProjectionBudgetError
from library_deep_enrichment.corpus.backend import BudgetExceededError
from library_deep_enrichment.corpus.contracts import Record
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, Limits


class State(StrEnum):
    """Whether interpretation produced a checked summary under the requested limits."""

    SUMMARIZED = "summarized"
    EXHAUSTED = "budget_exhausted"


@frozen(kw_only=True)
class BehaviorCoverage(Record):
    """One selected owner's outcome; an empty summary never means an empty behavior."""

    request: str
    owner: str
    program: str
    summary: str
    state: State
    phase: str
    detail: str
    metrics: tuple[Metric, ...]


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Retain denominator membership and any actual derived result through export.

    Returns:
        Exact prerequisites, including the summary only when one was completed.

    """
    if not isinstance(record, BehaviorCoverage):
        return ()
    return (
        ("behavior_requests", record.request),
        ("native_facts", record.owner),
        *((("behavior_programs", record.program),) if record.program else ()),
        *((("behavior_summaries", record.summary),) if record.summary else ()),
    )


def projection_failure(
    request: BehaviorRequest, owner: str, error: ProjectionBudgetError
) -> BehaviorCoverage:
    """Retain a selected owner without fabricating a completed execution graph.

    Returns:
        Exact request/owner membership and observed attempted projection size.

    """
    return BehaviorCoverage(
        logical_id=f"behavior-coverage:{revision_of(request)}:{owner}",
        profile=request.profile,
        request=revision_of(request),
        owner=owner,
        program="",
        summary="",
        state=State.EXHAUSTED,
        phase="normalization",
        detail=str(error),
        metrics=(
            Metric(name=f"projection_{error.dimension}_attempted", value=error.attempted),
            Metric(name=f"projection_{error.dimension}_limit", value=error.limit),
        ),
    )


def _exhausted(
    body: BehaviorProgram,
    error: BudgetExceededError,
    phase: str,
    metrics: tuple[Metric, ...] = (),
) -> BehaviorCoverage:
    return BehaviorCoverage(
        logical_id=f"behavior-coverage:{body.request}:{body.owner}",
        profile=body.profile,
        request=body.request,
        owner=body.owner,
        program=revision_of(body),
        summary="",
        state=State.EXHAUSTED,
        phase=phase,
        detail=str(error),
        metrics=metrics,
    )


def analyze(
    bodies: tuple[BehaviorProgram, ...], targets: dict[str, BehaviorProgram], limits: Limits
) -> tuple[Record, ...]:
    """Account for every normalized owner without converting exhaustion to an unknown summary.

    Returns:
        Successful summaries and one explicit coverage outcome per selected owner.

    """
    try:
        solution = solve(bodies, targets, limits)
    except BudgetExceededError as error:
        return tuple(_exhausted(body, error, "shared_fixedpoint") for body in bodies)
    records: list[Record] = []
    for body in bodies:
        interpreter = Interpreter(limits, targets=targets, solution=solution)
        try:
            summary = interpreter.summarize(body)
        except BudgetExceededError as error:
            records.append(
                _exhausted(
                    body,
                    error,
                    "interpretation",
                    (
                        Metric(name="instructions_before_exhaustion", value=interpreter.steps),
                        Metric(name="states_before_exhaustion", value=interpreter.states),
                        Metric(name="calls_before_exhaustion", value=interpreter.calls),
                        Metric(name="terms_before_exhaustion", value=len(interpreter.values.terms)),
                    ),
                )
            )
            continue
        records.extend(
            (
                summary,
                interpreter.origins.record(summary),
                BehaviorCoverage(
                    logical_id=f"behavior-coverage:{body.request}:{body.owner}",
                    profile=body.profile,
                    request=body.request,
                    owner=body.owner,
                    program=revision_of(body),
                    summary=revision_of(summary),
                    state=State.SUMMARIZED,
                    phase="interpretation",
                    detail="summary precision and semantic frontiers are carried by the referenced result",
                    metrics=summary.metrics,
                ),
            )
        )
    return tuple(records)
