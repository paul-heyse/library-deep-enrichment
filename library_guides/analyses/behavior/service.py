"""Source-backed behavior derivation through the existing typed corpus authority."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from attrs import evolve, frozen

from library_guides.analyses.behavior import (
    coverage,
    mir,
    mir_callables,
    mir_instances,
    mir_lifecycle,
    mir_memory,
    origins,
    python,
    typing_evidence,
)
from library_guides.analyses.behavior.builder import Origin
from library_guides.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
    Language,
)
from library_guides.analyses.behavior.integrity import HARD_LIMITS, limits_valid, require
from library_guides.analyses.behavior.projection_budget import ProjectionBudgetError
from library_guides.analyses.behavior.python_nodes import Node, read, walk
from library_guides.analyses.behavior.typing_contracts import BehaviorTyping
from library_guides.corpus.contracts import Blob, Context, SourceFile
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_NATIVE_BYTES = 64 * 1024 * 1024
_CONSEQUENCES = (
    BehaviorProgram,
    BehaviorSummary,
    BehaviorTyping,
    coverage.BehaviorCoverage,
    origins.BehaviorOrigins,
)
type PythonOwners = dict[
    tuple[str, str, str], dict[tuple[str, int, int], tuple[Node, NativeFact, SourceFile]]
]


@frozen(kw_only=True)
class Population:
    """A request's exact admitted native owners and contextual source artifacts."""

    owners: tuple[NativeFact, ...]
    artifacts: dict[str, NativeArtifact]


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Expose derivation prerequisites to admission, invalidation and portable closure.

    Returns:
        Typed references, including the complete finite owner denominator.

    """
    if isinstance(record, BehaviorRequest):
        return (
            *(("native_facts", item) for item in record.owners),
            *(("native_artifacts", item) for item in (*record.artifacts, *record.type_artifacts)),
        )
    if isinstance(record, BehaviorProgram):
        return (
            ("behavior_requests", record.request),
            ("native_facts", record.owner),
            ("native_artifacts", record.artifact),
            ("contexts", record.context),
        )
    if isinstance(record, BehaviorSummary):
        return (
            ("behavior_requests", record.request),
            ("behavior_programs", record.program),
            *(("behavior_programs", item) for item in record.dependencies),
        )
    return (
        *typing_evidence.references(record),
        *coverage.references(record),
        *origins.references(record),
    )


def population(reader: CorpusReader, request: BehaviorRequest) -> Population:
    """Validate exact owner and source context before normalization or interpretation.

    Returns:
        A finite native selection with no display-name identity joins.

    """
    limits_valid(request.limits)
    require("unknown behavior invocation phase", condition=request.phase in {"invoke", "activate"})
    require(
        "behavior owner denominator is empty, duplicate or over budget",
        condition=0 < len(request.owners) <= request.limits.owners
        and len(set(request.owners)) == len(request.owners),
    )
    require(
        "behavior artifact denominator is empty or repeated",
        condition=bool(request.artifacts) and len(set(request.artifacts)) == len(request.artifacts),
    )
    require(
        "behavior type artifacts are repeated or overlap executable artifacts",
        condition=len(set(request.type_artifacts)) == len(request.type_artifacts)
        and not set(request.type_artifacts).intersection(request.artifacts),
    )
    require(
        "supplied call bindings require a qualified binding derivation",
        condition=not request.bindings,
    )
    artifacts = {}
    for item in reader.get_many("native_artifacts", (*request.artifacts, *request.type_artifacts)):
        require(
            "behavior requires same-profile native artifacts",
            condition=isinstance(item, NativeArtifact) and item.profile == request.profile,
        )
        assert isinstance(item, NativeArtifact)
        if revision_of(item) in request.type_artifacts:
            require(
                "behavior typing requires the supported static type lane",
                condition=item.lane == "types"
                and item.schema == "library-guides.python-semantics.v1",
            )
        context = reader.get("contexts", item.context)
        require(
            "behavior artifact has an invalid contextual owner",
            condition=isinstance(context, Context) and context.profile == item.profile,
        )
        artifacts[revision_of(item)] = item
    owners = []
    total_bytes = 0
    for item in reader.get_many("native_facts", request.owners):
        require(
            "behavior owner escaped its selected artifact/profile",
            condition=isinstance(item, NativeFact)
            and item.artifact in request.artifacts
            and item.profile == request.profile,
        )
        assert isinstance(item, NativeFact)
        total_bytes += item.original.end - item.original.start
        owners.append(item)
    require("behavior native owner bytes exceed budget", condition=total_bytes <= MAX_NATIVE_BYTES)
    return Population(owners=tuple(sorted(owners, key=revision_of)), artifacts=artifacts)


def _raw(reader: CorpusReader, fact: NativeFact) -> dict:
    return json.loads(resolve_bytes(reader, fact.original, max_bytes=MAX_NATIVE_BYTES))


def _source(reader: CorpusReader, artifact: NativeArtifact, digest: str) -> tuple[SourceFile, Blob]:
    matches = []
    for source in reader.get_many("source_files", artifact.sources):
        assert isinstance(source, SourceFile)
        blob = reader.get("blobs", source.blob)
        assert isinstance(blob, Blob)
        if blob.digest == digest:
            matches.append((source, blob))
    require(
        "behavior requires retained source bytes matching the producer digest",
        condition=bool(matches),
    )
    return min(matches, key=lambda pair: revision_of(pair[0]))


def _mir_sources(
    reader: CorpusReader, artifact: NativeArtifact, raw: dict
) -> tuple[SourceFile, ...]:
    pending = [raw]
    sources: dict[str, tuple[SourceFile, Blob]] = {}
    while pending:
        value = pending.pop()
        if isinstance(value, list):
            pending.extend(value)
        elif isinstance(value, dict):
            if value.get("mapping") == "exact_original_file_bytes":
                digest = value.get("source_digest")
                require("MIR exact mapping lacks a byte digest", condition=isinstance(digest, str))
                assert isinstance(digest, str)
                if digest not in sources:
                    sources[digest] = _source(reader, artifact, digest)
                start, end = value.get("byte_start"), value.get("byte_end")
                require(
                    "MIR source mapping escapes its retained bytes",
                    condition=type(start) is int
                    and type(end) is int
                    and 0 <= start <= end <= sources[digest][1].size,
                )
            pending.extend(value.values())
    return tuple(pair[0] for _, pair in sorted(sources.items()))


def _python_node(
    reader: CorpusReader, owner: NativeFact, cache: PythonOwners
) -> tuple[Node, NativeFact, SourceFile]:
    artifact = reader.get("native_artifacts", owner.artifact)
    assert isinstance(artifact, NativeArtifact)
    raw = _raw(reader, owner)["payload"]
    require(
        "Python execution requires a source function definition",
        condition=raw.get("node_kind") == "function_definition" and raw.get("syntax_valid") is True,
    )
    source, blob = _source(reader, artifact, raw["source_digest"])
    require("Python execution source exceeds byte bound", condition=blob.size <= MAX_SOURCE_BYTES)
    key = (owner.artifact, owner.file, raw["source_digest"])
    if key not in cache:
        cache[key] = _python_file(reader, owner, source, blob)
    names = [field for field in raw["fields"] if field["name"] == "name"]
    require("Python source owner requires one name anchor", condition=len(names) == 1)
    name = names[0]
    selected = cache[key].get(("identifier", name["start"], name["end"]))
    if selected is None:
        selected = cache[key].get(("extent", raw["start"], raw["end"]))
    require(
        "Python source owner lacks one exact Ruff execution projection",
        condition=selected is not None,
    )
    assert selected is not None
    require("Python anchored owner names disagree", condition=selected[0].value == raw["name"])
    return selected


def _python_file(
    reader: CorpusReader,
    owner: NativeFact,
    source: SourceFile,
    blob: Blob,
) -> dict[tuple[str, int, int], tuple[Node, NativeFact, SourceFile]]:
    candidates = {}
    total = 0
    for fact in reader.filtered_records(
        "native_facts", (("artifact", owner.artifact), ("file", owner.file), ("kind", "execution"))
    ):
        assert isinstance(fact, NativeFact)
        total += fact.original.end - fact.original.start
        require(
            "Python projection file exceeds native byte budget", condition=total <= MAX_NATIVE_BYTES
        )
        projected = _raw(reader, fact)["payload"]
        projected.pop("family")
        # File-level source acquisition has its own hard bound. A selected owner's
        # small graph budget must not reject another owner's cached syntax tree.
        root = read(projected, source_size=blob.size, node_limit=HARD_LIMITS.steps)
        for node in walk(root):
            if node.kind == "function":
                keys = [("extent", *node.span)]
                if node.children("identifier"):
                    name = node.one("identifier")
                    require(
                        "Python function identifier escaped its owner",
                        condition=name.kind == "identifier"
                        and name.value == node.value
                        and node.start <= name.start < name.end <= node.end,
                    )
                    keys.append(("identifier", *name.span))
                require(
                    "Python execution repeats a source owner",
                    condition=all(key not in candidates for key in keys),
                )
                for key in keys:
                    candidates[key] = (node, fact, source)
    return candidates


def _program(
    reader: CorpusReader,
    owner: NativeFact,
    request: BehaviorRequest,
    artifact: NativeArtifact,
    cache: PythonOwners,
) -> BehaviorProgram:
    support = (
        select(owner, "/original", "source-owner"),
        select(request, "/owners", "finite-owner-universe"),
        select(artifact, "/sources", "retained-source-universe"),
    )
    origin = Origin(
        request=revision_of(request),
        owner=revision_of(owner),
        artifact=owner.artifact,
        context=artifact.context,
        profile=owner.profile,
        symbol=owner.symbol,
        language=Language.RUST
        if artifact.lane
        in {"mir", "mir_execution", "mir_instances", "mir_callables", "mir_lifecycle", "mir_memory"}
        else Language.PYTHON,
        support=support,
    )
    if artifact.lane in {
        "mir",
        "mir_execution",
        "mir_instances",
        "mir_callables",
        "mir_lifecycle",
        "mir_memory",
    }:
        require(
            "Rust body activation requires an instance-specific request",
            condition=request.phase == "invoke",
        )
        raw = _raw(reader, owner)
        require(
            "Rust execution requires a MIR body owner",
            condition=raw.get("kind")
            in (
                {"mir_owner", "mir_instance"}
                if artifact.lane
                in {"mir_instances", "mir_callables", "mir_lifecycle", "mir_memory"}
                else {"mir_owner"}
            ),
        )
        require(
            "Rust execution schema or behavioral identity is invalid",
            condition=artifact.schema == "library-guides.mir.v1"
            if artifact.lane == "mir"
            else artifact.schema
            == (
                mir_memory.SCHEMA
                if artifact.lane == "mir_memory"
                else mir_lifecycle.SCHEMA
                if artifact.lane == "mir_lifecycle"
                else mir_callables.SCHEMA
                if artifact.lane == "mir_callables"
                else mir_instances.SCHEMA
                if artifact.lane == "mir_instances"
                else "library-guides.mir-execution.v1"
            )
            and isinstance(raw.get("behavior"), dict),
        )
        if artifact.lane in {"mir_instances", "mir_callables", "mir_lifecycle", "mir_memory"}:
            mir_instances.validate(raw)
        if artifact.lane in {"mir_callables", "mir_lifecycle", "mir_memory"}:
            mir_callables.validate(raw)
        if artifact.lane in {"mir_lifecycle", "mir_memory"}:
            mir_lifecycle.validate(raw)
        if artifact.lane == "mir_memory":
            mir_memory.validate(raw)
        source_files = _mir_sources(reader, artifact, raw)
        origin = evolve(
            origin,
            support=(
                *support,
                *(select(item, "/blob", "compiler-source-bytes") for item in source_files),
            ),
        )
        return mir.normalize(origin, raw, request.limits)
    require(
        "Python execution requires the versioned execution lane",
        condition=artifact.lane == "execution"
        and artifact.schema == "library-guides.source-execution.v1",
    )
    node, fact, source = _python_node(reader, owner, cache)
    origin = evolve(
        origin,
        support=(
            *support,
            select(fact, "/original", "ruff-execution-projection"),
            select(source, "/blob", "exact-source-bytes"),
        ),
    )
    return python.normalize(origin, node, request.limits, phase=request.phase)


def programs(reader: CorpusReader, request: BehaviorRequest) -> tuple[BehaviorProgram, ...]:
    """Normalize every selected owner; never shrink a denominator after a failure.

    Returns:
        Deterministic execution projections of the complete selected population.

    """
    selected = population(reader, request)
    return _programs(reader, request, selected)


def _programs(
    reader: CorpusReader, request: BehaviorRequest, selected: Population
) -> tuple[BehaviorProgram, ...]:
    cache: PythonOwners = {}
    return tuple(
        _program(reader, owner, request, selected.artifacts[owner.artifact], cache)
        for owner in selected.owners
    )


def analyze(reader: CorpusReader, request: BehaviorRequest) -> tuple[Record, ...]:
    """Derive graphs and guarded summaries using only the admitted native inputs.

    Returns:
        Every selected owner has a summary or explicit projection/analysis budget disposition.
        Invalid source/projection evidence still fails before admission.

    """
    selected = population(reader, request)
    bodies, failures = _attempt_programs(reader, request, selected)
    native = {revision_of(item): item for item in selected.owners}
    targets = _targets(reader, native, bodies)
    return (
        *bodies,
        *failures,
        *coverage.analyze(bodies, targets, request.limits),
        *typing_evidence.analyze(reader, request, bodies),
    )


def _attempt_programs(
    reader: CorpusReader, request: BehaviorRequest, selected: Population
) -> tuple[tuple[BehaviorProgram, ...], tuple[coverage.BehaviorCoverage, ...]]:
    cache: PythonOwners = {}
    bodies, failures = [], []
    for owner in selected.owners:
        try:
            body = _program(reader, owner, request, selected.artifacts[owner.artifact], cache)
        except ProjectionBudgetError as error:
            failures.append(coverage.projection_failure(request, revision_of(owner), error))
        else:
            bodies.append(body)
    return tuple(bodies), tuple(failures)


def _targets(
    reader: CorpusReader, native: dict[str, NativeFact], bodies: tuple[BehaviorProgram, ...]
) -> dict[str, BehaviorProgram]:
    candidates: dict[str, list[BehaviorProgram]] = {}
    originals: dict[str, dict] = {}
    for body in bodies:
        if body.language != Language.RUST:
            continue
        fact = native[body.owner]
        candidates.setdefault(fact.native_id, []).append(body)
        raw = _raw(reader, fact)
        originals[body.owner] = raw
        metadata = raw.get("behavior") or {}
        if metadata.get("definition") and raw.get("kind") != "mir_instance":
            candidates.setdefault(metadata["definition"], []).append(body)
    # Multiple contextual bodies prevent a closed target choice; names are never a fallback.
    result = {key: values[0] for key, values in candidates.items() if len(values) == 1}
    instances = {
        key: originals[body.owner]
        for key, body in result.items()
        if key.startswith("mir-instance:")
    }
    for raw in originals.values():
        mir_instances.qualify_calls(raw, instances)
        mir_callables.qualify(raw, instances)
        mir_lifecycle.qualify(raw, instances)
        mir_memory.qualify(raw, instances)
    return result


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Replay derivations at admission; replay is not an independent soundness proof."""
    for record in records:
        if isinstance(record, BehaviorRequest):
            population(reader, record)
    requests = {item.request for item in records if isinstance(item, _CONSEQUENCES)}
    for revision in requests:
        request = reader.get("behavior_requests", revision)
        require(
            "behavior consequence has no typed request",
            condition=isinstance(request, BehaviorRequest),
        )
        assert isinstance(request, BehaviorRequest)
        expected = {revision_of(item) for item in analyze(reader, request)}
        require(
            "behavior consequence differs from retained-source replay",
            condition=all(
                revision_of(item) in expected
                for item in records
                if isinstance(item, _CONSEQUENCES) and item.request == revision
            ),
        )
