"""Checked population-wide dependency, resource and local-cost derivation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
)
from library_guides.analyses.behavior.coverage import BehaviorCoverage
from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.characterization import costs, dependencies, resources
from library_guides.analyses.characterization.contracts import (
    BehaviorCharacterization,
    CharacterizationRequest,
)
from library_guides.corpus.backend import BudgetExceededError
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MODEL = "library-guides.guarded-dependency-resource-characterization.v1"
MAX_REQUESTS = 128
MAX_OWNERS = 5000
MAX_TERMS = 10_000_000
MAX_WORK = 100_000_000
FRONTIER = (
    "finite_selected_behavior_owners_not_complete_public_library_population",
    "names_do_not_classify_clock_randomness_service_atomicity_or_synchronization",
    "source_binding_and_summary_assumptions_remain_applicable",
    "absent_retained_dependency_does_not_prove_purity_or_race_freedom",
)


@frozen(kw_only=True)
class Owner:
    """One exact population member and the outcomes actually retained for it."""

    behavior: BehaviorRequest
    coverage: BehaviorCoverage
    program: BehaviorProgram | None
    summary: BehaviorSummary | None


def population(reader: CorpusReader, request: CharacterizationRequest) -> tuple[Owner, ...]:
    """Require complete owner accounting before deriving any population profile.

    Returns:
        Every requested owner, including explicit normalization/interpretation exhaustion.

    """
    require(
        "invalid characterization population or independent budgets",
        condition=all(
            (
                0 < len(request.behaviors) <= MAX_REQUESTS,
                len(set(request.behaviors)) == len(request.behaviors),
                0 < request.max_owners <= MAX_OWNERS,
                0 < request.max_terms <= MAX_TERMS,
                0 < request.max_work <= MAX_WORK,
            )
        ),
    )
    result = []
    term_count = 0
    for behavior in reader.get_many("behavior_requests", sorted(request.behaviors)):
        assert isinstance(behavior, BehaviorRequest)
        outcomes = tuple(
            reader.filtered_records("behavior_coverage", (("request", revision_of(behavior)),))
        )
        require(
            "characterization requires one exact outcome for every selected behavior owner",
            condition=len(outcomes) == len(behavior.owners)
            and {row.owner for row in outcomes if isinstance(row, BehaviorCoverage)}
            == set(behavior.owners),
        )
        for outcome in sorted(outcomes, key=revision_of):
            assert isinstance(outcome, BehaviorCoverage)
            item = _owner(reader, behavior, outcome)
            term_count += sum(
                len(record.terms) for record in (item.program, item.summary) if record is not None
            )
            result.append(item)
            _budget(len(result), request.max_owners, "owner")
            _budget(term_count, request.max_terms, "term")
    return tuple(result)


def _owner(reader: CorpusReader, behavior: BehaviorRequest, outcome: BehaviorCoverage) -> Owner:
    program = reader.get("behavior_programs", outcome.program) if outcome.program else None
    summary = reader.get("behavior_summaries", outcome.summary) if outcome.summary else None
    require(
        "characterization program reference is invalid",
        condition=program is None or isinstance(program, BehaviorProgram),
    )
    require(
        "characterization summary reference is invalid",
        condition=summary is None or isinstance(summary, BehaviorSummary),
    )
    assert program is None or isinstance(program, BehaviorProgram)
    assert summary is None or isinstance(summary, BehaviorSummary)
    if program is not None:
        require(
            "characterization program escaped its owner/context",
            condition=(program.request, program.owner, program.profile)
            == (revision_of(behavior), outcome.owner, behavior.profile),
        )
    if summary is not None:
        require(
            "characterization summary escaped its program/context",
            condition=(summary.request, summary.program, summary.profile)
            == (revision_of(behavior), outcome.program, behavior.profile),
        )
    return Owner(behavior=behavior, coverage=outcome, program=program, summary=summary)


def _budget(actual: int, limit: int, label: str) -> None:
    if actual > limit:
        message = f"characterization {label} budget exhausted: {actual} > {limit}"
        raise BudgetExceededError(message)


def _profile(
    request: CharacterizationRequest, item: Owner, work_limit: int
) -> tuple[BehaviorCharacterization, int]:
    program, summary = item.program, item.summary
    base_work = 0 if program is None else len(program.instructions) + len(program.edges)
    if summary is not None:
        base_work += sum(
            1 + len(clause.effects) + len(clause.regions) + len(clause.guards) + len(clause.memory)
            for clause in summary.clauses
        )
    _budget(base_work, work_limit, "structural-work")
    original = dependencies.Ancestry(program.terms if program else (), work_limit - base_work)
    source_dependencies = dependencies.program_sources(program, original) if program else ()
    inferred = dependencies.Ancestry(
        summary.terms if summary else (), work_limit - base_work - original.visits
    )
    outcome_dependencies = dependencies.summary_sources(summary, inferred) if summary else ()
    region_relations = resources.relations(summary, inferred) if summary else ()
    profile = BehaviorCharacterization(
        logical_id=f"behavior-characterization:{request.logical_id}:{revision_of(item.behavior)}:{item.coverage.owner}",
        profile=item.behavior.profile,
        request=revision_of(request),
        behavior=revision_of(item.behavior),
        owner=item.coverage.owner,
        coverage=revision_of(item.coverage),
        program=item.coverage.program,
        summary=item.coverage.summary,
        model=MODEL,
        state=item.coverage.state,
        dependencies=(*source_dependencies, *outcome_dependencies),
        costs=costs.analyze(program) if program else (),
        resources=region_relations,
        ordering=resources.ordering(summary) if summary else (),
        frontier=(
            *FRONTIER,
            *(("normalization_unavailable:" + item.coverage.detail,) if program is None else ()),
            *(("summary_unavailable:" + item.coverage.detail,) if summary is None else ()),
        ),
        support=(
            select(request, "/behaviors", "finite-characterization-population"),
            select(item.behavior, "/owners", "exact-native-owner-denominator"),
            select(item.coverage, "/state", "actual-behavior-outcome"),
            *((select(program, "/instructions", "owned-executable-graph"),) if program else ()),
            *((select(summary, "/clauses", "guarded-outcome-relations"),) if summary else ()),
        ),
    )
    return profile, base_work + original.visits + inferred.visits


def analyze(
    reader: CorpusReader, request: CharacterizationRequest
) -> tuple[BehaviorCharacterization, ...]:
    """Derive reusable dimensions with bounded ancestry work across the entire selection.

    Returns:
        One profile per selected owner; no identifier-specific semantic overrides.

    """
    result, work = [], 0
    for item in population(reader, request):
        profile, consumed = _profile(request, item, request.max_work - work)
        result.append(profile)
        work += consumed
    return tuple(result)


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Retain exact population and dimension expression prerequisites.

    Returns:
        Typed links for invalidation, replay and portable evidence closure.

    """
    if isinstance(record, CharacterizationRequest):
        return tuple(("behavior_requests", item) for item in record.behaviors)
    if not isinstance(record, BehaviorCharacterization):
        return ()
    return (
        ("characterization_requests", record.request),
        ("behavior_requests", record.behavior),
        ("native_facts", record.owner),
        ("behavior_coverage", record.coverage),
        *((("behavior_programs", record.program),) if record.program else ()),
        *((("behavior_summaries", record.summary),) if record.summary else ()),
    )


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Replay complete requested dimensions and reject forged relations or missing owners."""
    for record in records:
        if isinstance(record, CharacterizationRequest):
            population(reader, record)
    for key in {item.request for item in records if isinstance(item, BehaviorCharacterization)}:
        request = reader.get("characterization_requests", key)
        assert isinstance(request, CharacterizationRequest)
        expected = {revision_of(item) for item in analyze(reader, request)}
        require(
            "behavior characterization differs from admitted evidence replay",
            condition=all(
                revision_of(item) in expected
                for item in records
                if isinstance(item, BehaviorCharacterization) and item.request == key
            ),
        )
