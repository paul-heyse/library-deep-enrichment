"""Reconcile static observations to selected executable source owners, without dispatch closure."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.contracts import Language
from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.behavior.typing_contracts import BehaviorTyping, TypePoint
from library_deep_enrichment.analyses.behavior.typing_locations import MAX_BYTES, RetainedFiles
from library_deep_enrichment.corpus.evidence import resolve_bytes, select
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.analyses.behavior.contracts import BehaviorProgram, BehaviorRequest
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

MODEL = "python-source-aligned-static-observations.v1"
MAX_FACTS = 50_000
MAX_POINTS = 5000
_ROLES = {"type_at": "computed_bulk", "call": "call_candidate"}


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Expose the exact observed context and every retained declaration prerequisite.

    Returns:
        Portable typed references; unresolved locations create no fabricated source reference.

    """
    if not isinstance(record, BehaviorTyping):
        return ()
    return (
        ("behavior_requests", record.request),
        ("behavior_programs", record.program),
        ("native_artifacts", record.artifact),
        ("contexts", record.context),
        *((("source_files", record.source),) if record.source else ()),
        *(("native_facts", point.fact) for point in record.points),
        *sorted(
            {
                ("source_files", item.source)
                for point in record.points
                for item in point.declarations
                if item.source
            }
        ),
    )


def _points(
    reader: CorpusReader, files: RetainedFiles, owner: NativeFact, raw_owner: dict
) -> tuple[TypePoint, ...]:
    result, count, size = [], 0, 0
    for fact in reader.filtered_records(
        "native_facts", (("artifact", revision_of(files.artifact)), ("file", owner.file))
    ):
        assert isinstance(fact, NativeFact)
        count += 1
        size += fact.original.end - fact.original.start
        require("typed fact budget exhausted", condition=count <= MAX_FACTS and size <= MAX_BYTES)
        raw = json.loads(resolve_bytes(reader, fact.original, max_bytes=MAX_BYTES))
        require(
            "typed source differs from executable source",
            condition=raw["source_digest"] == raw_owner["source_digest"],
        )
        payload = raw["payload"]
        kind = payload["kind"]
        if kind not in {"targeted", "type_at", "call"}:
            continue
        anchor = payload["anchor"]
        require(
            "type point has a non-byte coordinate",
            condition=anchor["coordinate"] == "utf8_bytes",
        )
        start, end = anchor["start"], anchor["end"]
        if not raw_owner["start"] <= start <= end <= raw_owner["end"]:
            continue
        declarations = ()
        if kind == "targeted" and payload["tsp"] is not None:
            declarations = files.declarations(json.loads(payload["tsp"]["raw_tsp"]))
        result.append(
            TypePoint(
                fact=revision_of(fact),
                role=payload["role"] if kind == "targeted" else _ROLES[kind],
                start=start,
                end=end,
                expected_fallback=payload.get("expected_fallback", False),
                declarations=declarations,
            )
        )
        require("typed owner point budget exhausted", condition=len(result) <= MAX_POINTS)
    return tuple(sorted(result, key=lambda point: (point.start, point.end, point.role, point.fact)))


def analyze(
    reader: CorpusReader, request: BehaviorRequest, programs: tuple[BehaviorProgram, ...]
) -> tuple[BehaviorTyping, ...]:
    """Retain all requested type-context/owner pairs, including pairs with no observations.

    Returns:
        Source-aligned static evidence; annotations and stubs never become runtime guarantees.

    """
    result = []
    for artifact in reader.get_many("native_artifacts", request.type_artifacts):
        assert isinstance(artifact, NativeArtifact)
        files = RetainedFiles(reader, artifact)
        for program in programs:
            if program.language != Language.PYTHON:
                continue
            owner = reader.get("native_facts", program.owner)
            assert isinstance(owner, NativeFact)
            raw = json.loads(resolve_bytes(reader, owner.original, max_bytes=MAX_BYTES))["payload"]
            selected = [pair for pair in files.files.values() if pair[0] == owner.file]
            source, points = "", ()
            if selected:
                require(
                    "type/executable file selections disagree",
                    condition=len(selected) == 1 and selected[0][1] == raw["source_digest"],
                )
                witness, _ = files.read(selected[0][1])
                source = revision_of(witness)
                points = _points(reader, files, owner, raw)
            result.append(
                BehaviorTyping(
                    logical_id=f"behavior-typing:{request.logical_id}:{program.owner}:{revision_of(artifact)}",
                    profile=request.profile,
                    request=revision_of(request),
                    program=revision_of(program),
                    artifact=revision_of(artifact),
                    context=artifact.context,
                    source=source,
                    model=MODEL,
                    points=points,
                    frontier=(
                        "static candidates do not establish runtime dispatch or annotation conformance",
                        "source and typing contexts remain independently recorded",
                        "bulk type numbering and substitution detail remain in the original artifact",
                        *(
                            ()
                            if points
                            else ("no source-aligned observations in this requested pair",)
                        ),
                    ),
                    support=(
                        select(artifact, "/input", "type-import-context"),
                        select(artifact, "/shards", "original-static-type-graph"),
                        *(
                            select(
                                reader.get("native_facts", point.fact),
                                "/original",
                                "static-observation",
                            )
                            for point in points
                        ),
                    ),
                )
            )
    return tuple(result)
