"""Admit replayable observation checks through the existing corpus validation authority."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.behavior.contracts import BehaviorProgram, BehaviorSummary
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.behavior.origins import BehaviorOrigins
from library_guides.analyses.behavior.witness_checks import (
    CONTEXT_MODEL,
    MODEL,
    OPERATOR_MODEL,
    SCALAR_MODEL,
    CheckPolicy,
    compare,
)
from library_guides.analyses.behavior.witness_contracts import (
    BehaviorWitnessCheck,
    BehaviorWitnessRequest,
    ObservationSet,
    Verdict,
)
from library_guides.corpus.encoding import CONVERTER
from library_guides.corpus.evidence import resolve, select
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader


MAX_CASES = 1000
MAX_CELLS = 100_000
MAX_STEPS = 10_000_000
MODELS = {
    "library-guides.behavior-observations.v1": MODEL,
    "library-guides.behavior-observations.v2": CONTEXT_MODEL,
    "library-guides.behavior-observations.v3": OPERATOR_MODEL,
    "library-guides.behavior-observations.v4": SCALAR_MODEL,
}


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Expose exact summary and observation prerequisites to portable closure.

    Returns:
        Typed relationships; nested source selections are checked by ordinary admission.

    """
    if isinstance(record, BehaviorWitnessRequest):
        return tuple(("behavior_summaries", item) for item in record.summaries)
    if isinstance(record, BehaviorWitnessCheck):
        return (
            ("behavior_witness_requests", record.request),
            ("behavior_summaries", record.summary),
        )
    return ()


def analyze(
    reader: CorpusReader, request: BehaviorWitnessRequest
) -> tuple[BehaviorWitnessCheck, ...]:
    """Compare a complete finite observation denominator, including failures to agree.

    Returns:
        Checks of result/outcome relationships, not an execution attestation or effect proof.

    """
    require(
        "invalid finite witness limits",
        condition=0 < request.max_cases <= MAX_CASES and 0 < request.max_cells <= MAX_CELLS,
    )
    require(
        "empty or repeated witness summary population",
        condition=0 < len(request.summaries) <= request.max_cases
        and len(set(request.summaries)) == len(request.summaries),
    )
    require(
        "witness observations require attributed execution evidence",
        condition=bool(request.evidence),
    )
    observed = CONVERTER.structure(resolve(reader, request.observations), ObservationSet)
    require(
        "unsupported witness observation wire version",
        condition=observed.version in MODELS,
    )
    contextual = observed.version != "library-guides.behavior-observations.v1"
    require(
        "contextual observations require wire version v2",
        condition=contextual
        or all(
            not item.globals
            and not item.calls
            and all(step.kind != "identity" for step in item.projection)
            for item in observed.observations
        ),
    )
    require(
        "operator observations require wire version v3",
        condition=observed.version
        in {"library-guides.behavior-observations.v3", "library-guides.behavior-observations.v4"}
        or not any(item.operations for item in observed.observations),
    )
    require(
        "witness invocation denominator is empty or exhausted",
        condition=0 < len(observed.observations) <= request.max_cases,
    )
    require(
        "witness concrete cell budget exhausted",
        condition=sum(len(item.values) for item in observed.observations) <= request.max_cells,
    )
    require(
        "witness observations omit or add a selected summary",
        condition={item.summary for item in observed.observations} == set(request.summaries),
    )
    require(
        "witness invocation identifiers repeat",
        condition=len({(item.summary, item.case) for item in observed.observations})
        == len(observed.observations),
    )
    result = []
    steps = 0
    origins = _origins(reader, request)
    for summary in reader.get_many("behavior_summaries", request.summaries):
        require(
            "witness summary crosses its execution profile",
            condition=isinstance(summary, BehaviorSummary) and summary.profile == request.profile,
        )
        assert isinstance(summary, BehaviorSummary)
        program = reader.get("behavior_programs", summary.program)
        assert isinstance(program, BehaviorProgram)
        cases = tuple(
            item for item in observed.observations if item.summary == revision_of(summary)
        )
        steps += len(summary.terms) * len(cases)
        require("witness expression evaluation budget exhausted", condition=steps <= MAX_STEPS)
        checks = tuple(
            compare(
                program,
                summary,
                item,
                CheckPolicy(
                    contextual=contextual,
                    origins=origins.get(revision_of(summary)),
                    primitive_unary=observed.version == "library-guides.behavior-observations.v4",
                ),
            )
            for item in cases
        )
        result.append(
            BehaviorWitnessCheck(
                logical_id=f"behavior-witness-check:{request.logical_id}:{revision_of(summary)}",
                profile=request.profile,
                request=revision_of(request),
                summary=revision_of(summary),
                model=MODELS[observed.version],
                cases=checks,
                matched=sum(item.verdict == Verdict.MATCHED for item in checks),
                inconclusive=sum(item.verdict == Verdict.INCONCLUSIVE for item in checks),
                disagreements=sum(item.verdict == Verdict.DISAGREEMENT for item in checks),
                support=(
                    select(summary, "/clauses", "checked-result-relationships"),
                    request.observations,
                    *request.evidence,
                ),
            )
        )
    return tuple(result)


def _origins(reader: CorpusReader, request: BehaviorWitnessRequest) -> dict[str, BehaviorOrigins]:
    result = {}
    for selection in request.evidence:
        if selection.family != "behavior_origins":
            continue
        record = reader.get(selection.family, selection.revision)
        require(
            "operator evidence must select a complete origin table for one requested summary",
            condition=isinstance(record, BehaviorOrigins)
            and selection.field == "/entries"
            and record.summary in request.summaries
            and record.profile == request.profile,
        )
        assert isinstance(record, BehaviorOrigins)
        require(
            "operator evidence repeats a summary origin table",
            condition=record.summary not in result,
        )
        result[record.summary] = record
    return result


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Reject forged verdicts by replaying comparisons against exact observed values."""
    requests = {item.request for item in records if isinstance(item, BehaviorWitnessCheck)}
    requests.update(
        revision_of(item) for item in records if isinstance(item, BehaviorWitnessRequest)
    )
    for revision in requests:
        request = reader.get("behavior_witness_requests", revision)
        assert isinstance(request, BehaviorWitnessRequest)
        expected = {revision_of(item) for item in analyze(reader, request)}
        require(
            "witness comparison differs from observation replay",
            condition=all(
                revision_of(item) in expected
                for item in records
                if isinstance(item, BehaviorWitnessCheck) and item.request == revision
            ),
        )
