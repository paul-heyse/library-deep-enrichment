"""Replayable reconciliation of fundamental package, compiler and input observations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.compilation_contracts import (
    CompilationPopulation,
    CompilationRequest,
    CompilationUnit,
)
from library_guides.analyses.compilation_inputs import catalogs, commands, inputs, invocation
from library_guides.analyses.compilation_join import JoinInput, candidates, settings
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of
from library_guides.facts.compiler_invocation import arguments

if TYPE_CHECKING:
    from library_guides.analyses.compilation_inputs import CompilationCatalog
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MODEL = "library-guides.observed-compilation-correspondence.v1"
FRONTIER = (
    "finite_selected_compilations_not_all_features_or_whole_program",
    "declaration_contexts_remain_distinct_from_compilation_contexts",
    "native_binding_and_consumer_availability_require_separate_evidence",
    "cargo_command_requests_are_separate_from_resolved_and_compiled_features",
)


def _unit(
    selected: dict[str, CompilationCatalog], key: str, request: CompilationRequest
) -> CompilationUnit:
    catalog = selected[key]
    retained = invocation(catalog)
    if retained is None:
        return CompilationUnit(
            artifact=key,
            context=catalog.artifact.context,
            invocation="",
            invocation_source="",
            compiler="",
            producer="",
            working_directory="",
            inputs=(),
            settings=(),
            candidates=(),
            state="original_invocation_unobserved",
            frontier=("normalizer_receipt_cannot_reconstruct_original_compiler_context",),
        )
    observed, source = retained
    parsed = arguments(observed)
    witnessed = inputs(catalog, observed)
    joined = candidates(
        selected, request, JoinInput(observed=observed, parsed=parsed, inputs=witnessed)
    )
    return CompilationUnit(
        artifact=key,
        context=catalog.artifact.context,
        invocation=observed.identity,
        invocation_source=source.revision,
        compiler=observed.compiler_digest,
        producer=observed.execution.provider_digest if observed.execution else "",
        working_directory=observed.execution.working_directory if observed.execution else "",
        inputs=witnessed,
        settings=settings(parsed, observed),
        candidates=joined,
        state="observed_invocation_with_candidates"
        if joined
        else "observed_invocation_cargo_unresolved",
        frontier=(
            *observed.frontier,
            *parsed.frontier,
            "target_defaults_and_build_script_effective_context_require_separate_observation",
        ),
    )


def analyze(reader: CorpusReader, request: CompilationRequest) -> CompilationPopulation:
    """Reconcile exact observations without dropping missing or conflicting unit members.

    Returns:
        One replayable population with separate request, resolution and execution evidence.

    """
    selected = catalogs(reader, request)
    return CompilationPopulation(
        logical_id="compilation-population:" + request.logical_id,
        profile=request.profile,
        request=revision_of(request),
        model=MODEL,
        units=tuple(_unit(selected, key, request) for key in sorted(request.executables)),
        commands=tuple(
            item
            for key in sorted(request.metadata + request.messages)
            for item in commands(selected[key])
        ),
        frontier=FRONTIER,
        support=(
            select(request, "/executables", "finite-compiler-unit-catalog"),
            select(request, "/metadata", "finite-package-resolution-catalog"),
            select(request, "/messages", "finite-build-observation-catalog"),
            *(
                select(item.artifact, "/receipt", "exact-acquisition-observation")
                for item in selected.values()
            ),
            *(
                select(fact, "/original", "complete-cargo-catalog-member")
                for item in selected.values()
                for fact, _ in item.rows
            ),
        ),
    )


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Enumerate observation and catalog prerequisites.

    Returns:
        Exact references for currentness and portable closure.

    """
    if isinstance(record, CompilationRequest):
        return tuple(
            ("native_artifacts", key)
            for key in sorted(set(record.executables + record.metadata + record.messages))
        )
    if not isinstance(record, CompilationPopulation):
        return ()
    result = [("compilation_requests", record.request)]
    for unit in record.units:
        result.extend((("native_artifacts", unit.artifact), ("contexts", unit.context)))
        if unit.invocation_source:
            result.append(("source_files", unit.invocation_source))
        result.extend(("source_files", item.source) for item in unit.inputs if item.source)
        for candidate in unit.candidates:
            result.append(("native_facts", candidate.metadata))
            if candidate.message:
                result.append(("native_facts", candidate.message))
    result.extend(("source_files", item.source) for item in record.commands)
    return tuple(sorted(set(result)))


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Replay the finite catalog and reject fabricated settings, identity joins and omissions."""
    for record in records:
        if isinstance(record, CompilationRequest):
            catalogs(reader, record)
        elif isinstance(record, CompilationPopulation):
            request = reader.get("compilation_requests", record.request)
            assert isinstance(request, CompilationRequest)
            require(
                "compilation population differs from original-observation replay",
                condition=record == analyze(reader, request),
            )
