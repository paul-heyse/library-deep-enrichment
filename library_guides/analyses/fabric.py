"""Run existing pure MIR analyses against exact native facts in the shared fabric."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_guides.analyses import effects, flow
from library_guides.analyses.fabric_contracts import AnalysisRequest, ControlEdge, SourceAnalysis
from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MAX_OWNERS = 200
MAX_OWNER_BYTES = 64 * 1024 * 1024
MODEL = "library-guides.mir-local-flow-and-effects.v1"


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Identify the exact source universe and model prerequisites.

    Returns:
        Typed prerequisites usable by admission, invalidation, and portable closure.

    """
    if isinstance(record, AnalysisRequest):
        return (
            ("native_artifacts", record.artifact),
            *(("native_facts", item) for item in record.owners),
        )
    if isinstance(record, SourceAnalysis):
        return (("analysis_requests", record.request), ("native_facts", record.owner))
    from library_guides.analyses.behavior.service import references as behavior_references
    from library_guides.analyses.behavior.witness_service import references as witness_references
    from library_guides.analyses.call_graph.service import references as call_graph_references
    from library_guides.analyses.callable_population import references as callable_references
    from library_guides.analyses.characterization.service import (
        references as characterization_references,
    )
    from library_guides.analyses.compilation import references as compilation_references
    from library_guides.analyses.python_fabric import references as python_references

    return (
        *python_references(record),
        *behavior_references(record),
        *witness_references(record),
        *callable_references(record),
        *compilation_references(record),
        *characterization_references(record),
        *call_graph_references(record),
    )


def _read(reader: CorpusReader, request: AnalysisRequest) -> tuple[tuple[NativeFact, dict], ...]:
    artifact = reader.get("native_artifacts", request.artifact)
    if (
        not isinstance(artifact, NativeArtifact)
        or artifact.lane != "mir"
        or artifact.profile != request.profile
        or not 1 <= len(request.owners) <= MAX_OWNERS
        or len(set(request.owners)) != len(request.owners)
    ):
        message = "source analysis requires 1..200 exact MIR owners under one artifact profile"
        raise CorpusError(message)
    total = 0
    result = []
    for owner in reader.get_many("native_facts", sorted(request.owners)):
        if not isinstance(owner, NativeFact) or owner.artifact != request.artifact:
            message = "analysis owner escaped its declared native artifact"
            raise CorpusError(message)
        total += owner.original.end - owner.original.start
        if total > MAX_OWNER_BYTES:
            message = "source analysis exceeds its 64 MiB owner-byte bound"
            raise BudgetExceededError(message)
        raw = json.loads(resolve_bytes(reader, owner.original, max_bytes=MAX_OWNER_BYTES))
        if raw.get("kind") != "mir_owner":
            message = "source analysis requires MIR owner payloads"
            raise CorpusError(message)
        result.append((owner, raw))
    return tuple(result)


def analyze(reader: CorpusReader, request: AnalysisRequest) -> tuple[SourceAnalysis, ...]:
    """Compute finite modeled consequences without touching legacy YAML or native workers.

    Returns:
        Typed owner consequences with unselected/external callees retained as open frontiers.

    """
    sources = _read(reader, request)
    summaries = effects.summarize(tuple(raw for _, raw in sources))
    result = []
    for owner, raw in sources:
        dataflow = flow.analyze(raw["payload"])
        control = flow.control_dependence(raw["payload"], dataflow.reachable)
        effect = summaries[raw["id"]]
        edges = control["edges"]
        frontier = control["frontier"]
        assert isinstance(edges, list)
        assert isinstance(frontier, list)
        result.append(
            SourceAnalysis(
                logical_id=f"source-analysis:{request.logical_id}:{owner.native_id}",
                profile=owner.profile,
                request=revision_of(request),
                owner=revision_of(owner),
                model=MODEL,
                reachable=dataflow.reachable,
                return_dependencies=dataflow.return_dependencies,
                may_effects=tuple(effect["may_effects"]),
                local_callees=tuple(effect["local_callees"]),
                effect_closed=effect["closed"],
                control=tuple(
                    ControlEdge(branch=edge[0], successor=edge[1], dependent=edge[2])
                    for edge in edges
                ),
                control_state=str(control["state"]),
                control_policy=str(control["policy"]),
                frontier=tuple(
                    sorted(
                        set(dataflow.frontier)
                        | set(effect["frontier"])
                        | {str(item) for item in frontier}
                    )
                ),
                support=(
                    select(owner, "/original", "modeled-source"),
                    select(request, "/owners", "finite-callee-universe"),
                ),
            )
        )
    return tuple(result)


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Independently replay each selected native model universe once per admission.

    Raises:
        CorpusError: A proposed consequence differs from the retained source-model result.

    """
    from library_guides.analyses.behavior.service import validate as validate_behavior
    from library_guides.analyses.behavior.witness_service import validate as validate_witness
    from library_guides.analyses.call_graph.service import validate as validate_call_graph
    from library_guides.analyses.callable_population import validate as validate_callables
    from library_guides.analyses.characterization.service import (
        validate as validate_characterization,
    )
    from library_guides.analyses.compilation import validate as validate_compilation
    from library_guides.analyses.python_fabric import validate as validate_python

    validate_python(reader, records)
    validate_behavior(reader, records)
    validate_witness(reader, records)
    validate_callables(reader, records)
    validate_compilation(reader, records)
    validate_characterization(reader, records)
    validate_call_graph(reader, records)
    requests = {record.request for record in records if isinstance(record, SourceAnalysis)}
    for record in records:
        if isinstance(record, AnalysisRequest):
            _read(reader, record)
    for revision in requests:
        request = reader.get("analysis_requests", revision)
        assert isinstance(request, AnalysisRequest)
        expected = {revision_of(item) for item in analyze(reader, request)}
        if any(
            isinstance(item, SourceAnalysis)
            and item.request == revision
            and revision_of(item) not in expected
            for item in records
        ):
            message = "source analysis differs from independent model replay"
            raise CorpusError(message)
