"""General source-backed public candidate accounting without runtime dispatch promotion."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from attrs import frozen

from library_guides.analyses.behavior.integrity import require
from library_guides.analyses.callable_contracts import (
    BodyCandidate,
    CallableCandidate,
    CallablePopulation,
    CallableRequest,
)
from library_guides.analyses.callable_sources import RetainedSource, paths, sources
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import resolve_bytes, select
from library_guides.corpus.native_contracts import NativeArtifact, NativeFact
from library_guides.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_guides.corpus.contracts import Record
    from library_guides.corpus.store import CorpusReader

MODEL = "library-guides.contextual-callable-source-population.v2"
MAX_FACTS = 100_000
MAX_ARTIFACTS = 128
FRONTIER = (
    "finite_artifact_catalog_not_whole_program_or_all_configurations",
    "source_correspondence_does_not_establish_runtime_binding_or_consumer_availability",
    "registry_and_dynamic_export_membership_remain_open",
)


@frozen(kw_only=True)
class Catalog:
    """Bounded native rows and retained source bytes for one exact artifact."""

    artifact: NativeArtifact
    rows: tuple[tuple[NativeFact, dict], ...]
    sources: dict[str, RetainedSource]
    paths: dict[str, RetainedSource]


def catalogs(reader: CorpusReader, request: CallableRequest) -> dict[str, Catalog]:
    """Acquire the complete finite catalogs before any candidate is excluded.

    Returns:
        Exact context-qualified rows; an incomplete native denominator is rejected.

    """
    require(
        "invalid callable population budget or interface selection",
        condition=0 < request.max_facts <= MAX_FACTS
        and 0 < request.max_bytes <= 128 * 1024 * 1024
        and bool(request.interfaces)
        and len(set(request.interfaces)) == len(request.interfaces)
        and len(set(request.executables)) == len(request.executables)
        and len(set(request.files)) == len(request.files)
        and all(request.files),
    )
    require(
        "callable artifact catalog exceeds budget",
        condition=len(set(request.interfaces + request.executables)) <= MAX_ARTIFACTS,
    )
    result = {}
    total = count = 0
    for artifact in sorted(
        reader.get_many("native_artifacts", sorted(set(request.interfaces + request.executables))),
        key=revision_of,
    ):
        require(
            "callable catalog escaped observation profile",
            condition=isinstance(artifact, NativeArtifact) and artifact.profile == request.profile,
        )
        assert isinstance(artifact, NativeArtifact)
        key = revision_of(artifact)
        require(
            "unsupported callable interface or executable schema",
            condition=(
                key not in request.interfaces
                or (artifact.lane, artifact.schema)
                in {
                    ("declarations", "library-guides.declaration.v1"),
                    ("execution", "library-guides.source-execution.v1"),
                    ("syntax", "library-guides.source-facts.v1"),
                }
            )
            and (
                key not in request.executables
                or (artifact.lane, artifact.schema)
                in {
                    ("mir_execution", "library-guides.mir-execution.v1"),
                    ("mir_instances", "library-guides.mir-instances.v1"),
                    ("mir_callables", "library-guides.mir-callables.v1"),
                    ("mir_lifecycle", "library-guides.mir-lifecycle.v1"),
                    ("mir_memory", "library-guides.mir-memory.v1"),
                    ("mir", "library-guides.mir.v1"),
                    ("execution", "library-guides.source-execution.v1"),
                }
            ),
        )
        rows = []
        for fact in reader.filtered_records("native_facts", (("artifact", key),)):
            assert isinstance(fact, NativeFact)
            total += fact.original.end - fact.original.start
            count += 1
            require(
                "callable catalog exceeded native budget",
                condition=count <= request.max_facts and total <= request.max_bytes,
            )
            rows.append(
                (
                    fact,
                    json.loads(resolve_bytes(reader, fact.original, max_bytes=request.max_bytes)),
                )
            )
        require(
            "callable catalog has an incomplete native denominator",
            condition=len(rows) == artifact.record_count,
        )
        retained = sources(reader, artifact)
        result[key] = Catalog(
            artifact=artifact,
            rows=tuple(sorted(rows, key=lambda pair: revision_of(pair[0]))),
            sources=retained,
            paths=paths(reader, artifact, retained),
        )
    return result


def _python_visibility(fact: NativeFact, rows: dict[str, dict]) -> str:
    current = rows[fact.native_id]["payload"]
    name = current.get("name", "")
    if name.startswith("_") and not (
        current.get("owner") and name.startswith("__") and name.endswith("__")
    ):
        return "excluded_private_name"
    seen: set[str] = set()
    while True:
        owner = current.get("owner")
        if not owner:
            return "public_name_or_protocol_candidate"
        if owner in seen or owner not in rows:
            return "unresolved_lexical_owner"
        seen.add(owner)
        current = rows[owner]["payload"]
        if current.get("node_kind") != "class_definition":
            return "excluded_nested_function"
        if current.get("name", "").startswith("_"):
            return "excluded_private_name"


def _rust_visibility(raw: dict, public: set[int]) -> str:
    if raw.get("public_routes"):
        return "documented_public_route"
    implementation = (raw.get("owner_contract") or {}).get("impl", {})
    receiver = implementation.get("for", {}).get("resolved_path", {})
    if (
        implementation.get("trait")
        and not implementation.get("is_negative")
        and receiver.get("id") in public
    ):
        return "trait_member_on_public_receiver_candidate"
    return (
        "excluded_no_public_route"
        if raw.get("route_state") == "complete"
        else "unresolved_public_route"
    )


def _body_sources(catalog: Catalog) -> dict[tuple[str, str, int, int], tuple[BodyCandidate, ...]]:
    result: dict[tuple[str, str, int, int], list[BodyCandidate]] = {}
    for fact, raw in catalog.rows:
        if fact.kind != "mir_owner":
            continue
        point = raw["payload"].get("source") or {}
        if point.get("mapping") != "exact_original_file_bytes" or point.get("expansion"):
            continue
        source_digest = point.get("source_digest")
        require("MIR source mapping lacks byte identity", condition=isinstance(source_digest, str))
        assert isinstance(source_digest, str)
        source = catalog.sources.get(source_digest)
        require("MIR source correspondence lacks retained bytes", condition=source is not None)
        assert source is not None
        start, end = point.get("byte_start"), point.get("byte_end")
        require(
            "MIR owner coordinate escaped source",
            condition=type(start) is int
            and type(end) is int
            and 0 <= start <= end <= len(source.data),
        )
        assert isinstance(start, int)
        assert isinstance(end, int)
        behavior = raw.get("behavior") or {}
        result.setdefault((point["file"], source.digest, start, end), []).append(
            BodyCandidate(
                owner=revision_of(fact),
                artifact=fact.artifact,
                context=catalog.artifact.context,
                definition=behavior.get("definition", ""),
                phase=behavior.get("phase", "unqualified_definition_body"),
                source=source.revision,
                start=start,
                end=end,
                state="exact_original_source_span",
            )
        )
    return {key: tuple(sorted(value, key=lambda body: body.owner)) for key, value in result.items()}


def _rust(
    catalog: Catalog,
    row: tuple[NativeFact, dict],
    bodies: dict,
    request: CallableRequest,
    public: set[int],
) -> CallableCandidate | None:
    fact, raw = row
    if raw.get("kind") != "function":
        return None
    span = raw["item"].get("span") or {}
    path = span.get("filename", "")
    if request.files and path and path not in request.files:
        return None
    source = catalog.paths.get(path)
    start = source.offset(span["begin"]) if source and span else -1
    end = source.offset(span["end"]) if source and span else -1
    require("reversed declaration source range", condition=start <= end)
    candidates = bodies.get((path, source.digest, start, end), ()) if source else ()
    routes = tuple(sorted(raw.get("public_routes", ())))
    reachability = _rust_visibility(raw, public)
    function = raw["item"]["inner"]["function"]
    return CallableCandidate(
        declaration=revision_of(fact),
        context=catalog.artifact.context,
        identity=digest(
            [
                MODEL,
                catalog.artifact.profile,
                raw.get("semantic_digest"),
                path,
                source.digest if source else "",
                start,
                end,
            ]
        ),
        symbol=fact.symbol,
        routes=routes,
        reachability=reachability,
        scope="selected_file" if path else "unlocated",
        path=path,
        source=source.revision if source else "",
        start=start,
        end=end,
        bodies=candidates,
        disposition=(
            "contextual_body_candidates"
            if candidates
            else "declaration_without_body"
            if not function.get("has_body")
            else "source_body_unresolved"
            if source
            else "source_attribution_unresolved"
        ),
        frontier=(
            "documentation_context_is_distinct_from_compilation_context",
            *(() if candidates else ("no_exact_body_in_selected_contexts",)),
            *(("multiple_contextual_bodies",) if len(candidates) > 1 else ()),
        ),
    )


def _python(catalog: Catalog, request: CallableRequest) -> tuple[CallableCandidate, ...]:
    rows = {fact.native_id: raw for fact, raw in catalog.rows if fact.kind == "definition"}
    result = []
    for fact, raw in catalog.rows:
        payload = raw.get("payload", {})
        if payload.get("node_kind") != "function_definition":
            continue
        if request.files and fact.file not in request.files:
            continue
        source = catalog.sources.get(payload.get("source_digest"))
        start, end = payload["start"], payload["end"]
        require(
            "Python callable range escaped retained source",
            condition=source is None or 0 <= start <= end <= len(source.data),
        )
        state = "stub_interface" if fact.file.endswith(".pyi") else "source_definition_candidate"
        bodies = ()
        if source and fact.artifact in request.executables and state != "stub_interface":
            bodies = (
                BodyCandidate(
                    owner=revision_of(fact),
                    artifact=fact.artifact,
                    context=catalog.artifact.context,
                    definition=digest([catalog.artifact.context, source.digest, start, end]),
                    phase="source_definition_before_binding",
                    source=source.revision,
                    start=start,
                    end=end,
                    state=state,
                ),
            )
        result.append(
            CallableCandidate(
                declaration=revision_of(fact),
                context=catalog.artifact.context,
                identity=digest(
                    [
                        MODEL,
                        catalog.artifact.profile,
                        fact.file,
                        source.digest if source else "",
                        start,
                        end,
                    ]
                ),
                symbol=fact.symbol,
                routes=(),
                reachability=_python_visibility(fact, rows),
                scope="selected_file",
                path=fact.file,
                source=source.revision if source else "",
                start=start,
                end=end,
                bodies=bodies,
                disposition=state if source else "source_attribution_unresolved",
                frontier=(
                    "public_name_rule_is_candidate_selection_not_runtime_export_proof",
                    "decorators_overloads_imports_and_descriptors_require_binding",
                    "source_definition_requires_execution_normalization",
                ),
            )
        )
    return tuple(result)


def analyze(reader: CorpusReader, request: CallableRequest) -> CallablePopulation:
    """Derive every selected candidate, retaining missing bodies and separate unit contexts.

    Returns:
        A source-correspondence population without a closed availability judgment.

    """
    selected = catalogs(reader, request)
    bodies: dict[tuple[str, str, int, int], tuple[BodyCandidate, ...]] = {}
    for key in request.executables:
        for point, values in _body_sources(selected[key]).items():
            bodies[point] = (*bodies.get(point, ()), *values)
    candidates = []
    for key in request.interfaces:
        catalog = selected[key]
        if catalog.artifact.lane == "declarations":
            public = {row["local_id"] for _, row in catalog.rows if row.get("public_routes")}
            candidates.extend(
                value
                for row in catalog.rows
                if (value := _rust(catalog, row, bodies, request, public)) is not None
            )
        else:
            candidates.extend(_python(catalog, request))
    return CallablePopulation(
        logical_id="callable-population:" + request.logical_id,
        profile=request.profile,
        request=revision_of(request),
        model=MODEL,
        candidates=tuple(sorted(candidates, key=lambda item: (item.identity, item.declaration))),
        frontier=FRONTIER,
        support=(
            select(request, "/interfaces", "finite-public-candidate-catalog"),
            select(request, "/executables", "finite-executable-catalog"),
            select(request, "/files", "source-scope"),
            *(
                select(item.artifact, "/receipt", "acquisition-context")
                for item in selected.values()
            ),
            *(
                select(fact, "/original", "complete-finite-catalog-member")
                for item in selected.values()
                for fact, _ in item.rows
            ),
        ),
    )


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return the finite catalog and every derived source/body dependency.

    Returns:
        Exact references for invalidation, admission and portable closure.

    """
    if isinstance(record, CallableRequest):
        return tuple(
            ("native_artifacts", key) for key in sorted(set(record.interfaces + record.executables))
        )
    if not isinstance(record, CallablePopulation):
        return ()
    result = [("callable_requests", record.request)]
    for item in record.candidates:
        result.extend((("native_facts", item.declaration), ("contexts", item.context)))
        if item.source:
            result.append(("source_files", item.source))
        for body in item.bodies:
            result.extend(
                (
                    ("native_facts", body.owner),
                    ("contexts", body.context),
                    ("source_files", body.source),
                )
            )
    return tuple(sorted(set(result)))


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Replay the complete candidate denominator and reject invented source or unit joins."""
    for record in records:
        if isinstance(record, CallableRequest):
            catalogs(reader, record)
        elif isinstance(record, CallablePopulation):
            request = reader.get("callable_requests", record.request)
            assert isinstance(request, CallableRequest)
            require(
                "callable population differs from retained-source replay",
                condition=record == analyze(reader, request),
            )
