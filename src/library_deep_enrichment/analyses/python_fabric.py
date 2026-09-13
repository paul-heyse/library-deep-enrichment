"""Source-aligned Python call reconciliation using only pinned corpus evidence."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.fabric_contracts import (
    PythonBoundary,
    PythonBoundaryRequest,
    PythonCall,
)
from library_deep_enrichment.corpus.backend import BudgetExceededError, CorpusError
from library_deep_enrichment.corpus.contracts import SourceFile
from library_deep_enrichment.corpus.evidence import iter_blob, resolve_bytes, select
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

MODEL = "library-guides.python-callee-source-alignment.v1"
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_CALLS = 1000
MAX_FILE_FACTS = 50_000


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return typed prerequisites, including every member of each finite call denominator.

    Returns:
        Exact source and target revisions for validation and portable closure.

    """
    if isinstance(record, PythonBoundaryRequest):
        return (("native_facts", record.owner), ("native_artifacts", record.types))
    if isinstance(record, PythonBoundary):
        return (
            ("python_boundary_requests", record.request),
            ("source_files", record.syntax_source),
            ("source_files", record.typed_source),
            *(
                ("native_facts", revision)
                for call in record.calls
                for revision in (call.site, *call.lexical, *call.targets)
            ),
        )
    return ()


def _raw(reader: CorpusReader, fact: NativeFact) -> dict:
    return json.loads(resolve_bytes(reader, fact.original, max_bytes=1_000_000))


def _source(reader: CorpusReader, artifact: NativeArtifact, file: str) -> SourceFile:
    matches = [
        item
        for item in reader.get_many("source_files", artifact.sources)
        if isinstance(item, SourceFile)
        and (item.path == file or item.path.endswith("/source/" + file))
    ]
    if len(matches) != 1:
        message = "Python boundary requires one exact source path in each lane"
        raise CorpusError(message)
    return matches[0]


def _facts(reader: CorpusReader, artifact: str, file: str) -> tuple[tuple[NativeFact, dict], ...]:
    result = []
    for fact in reader.filtered_records("native_facts", (("artifact", artifact), ("file", file))):
        if isinstance(fact, NativeFact):
            result.append((fact, _raw(reader, fact)))
        if len(result) > MAX_FILE_FACTS:
            message = "Python boundary exceeds 50000 facts in one selected source file"
            raise BudgetExceededError(message)
    return tuple(result)


def _calls(
    owner: NativeFact,
    syntax: tuple[tuple[NativeFact, dict], ...],
    typed: tuple[tuple[NativeFact, dict], ...],
    source_digest: str,
) -> tuple[PythonCall, ...]:
    result = []
    for fact, raw in syntax:
        body = raw.get("payload", {})
        if body.get("node_kind") != "call" or body.get("owner") != owner.native_id:
            continue
        callee = next(
            (field for field in body.get("fields", ()) if field.get("name") == "function"), None
        )
        if callee is None or body.get("source_digest") != source_digest:
            message = "Python call has no exact callee span under its source owner"
            raise CorpusError(message)
        lexical = tuple(
            sorted(
                revision_of(item)
                for item, row in syntax
                if row.get("payload", {}).get("event") == "callee_expression"
                and (row["payload"].get("start"), row["payload"].get("end"))
                == (callee["start"], callee["end"])
            )
        )
        targets = tuple(
            sorted(
                revision_of(item)
                for item, row in typed
                if row.get("source_digest") == source_digest
                and row.get("payload", {}).get("kind") == "call"
                and callee["start"]
                <= row["payload"]["anchor"]["start"]
                <= row["payload"]["anchor"]["end"]
                <= callee["end"]
            )
        )
        result.append(
            PythonCall(
                site=revision_of(fact),
                start=body["start"],
                end=body["end"],
                lexical=lexical,
                targets=targets,
                state="candidate" if targets else "unresolved",
            )
        )
        if len(result) > MAX_CALLS:
            message = "Python boundary exceeds its 1000-call owner limit"
            raise BudgetExceededError(message)
    return tuple(sorted(result, key=lambda item: (item.start, item.end, item.site)))


def analyze(reader: CorpusReader, request: PythonBoundaryRequest) -> PythonBoundary:
    """Reconcile one complete call denominator without a legacy collection or live analyzer.

    Returns:
        Source-position target candidates with dispatch and native-effect uncertainty retained.

    Raises:
        CorpusError: Lanes, owner, profiles, or exact source bytes do not agree.
        BudgetExceededError: The retained file exceeds its declared byte bound.

    """
    owner = reader.get("native_facts", request.owner)
    types = reader.get("native_artifacts", request.types)
    if not isinstance(owner, NativeFact) or not isinstance(types, NativeArtifact):
        message = "Python boundary requires an exact native owner and types artifact"
        raise CorpusError(message)
    syntax = reader.get("native_artifacts", owner.artifact)
    raw = _raw(reader, owner)
    if (
        not isinstance(syntax, NativeArtifact)
        or syntax.lane != "syntax"
        or types.lane != "types"
        or not syntax.profile == types.profile == request.profile
        or raw.get("payload", {}).get("node_kind") != "function_definition"
    ):
        message = "Python boundary requires same-profile syntax/types and one function owner"
        raise CorpusError(message)
    syntax_source = _source(reader, syntax, owner.file)
    typed_source = _source(reader, types, owner.file)
    if syntax_source.blob != typed_source.blob:
        message = "Python boundary lanes observe different source bytes"
        raise CorpusError(message)
    source = bytearray()
    for chunk in iter_blob(reader, syntax_source.blob):
        source.extend(chunk)
        if len(source) > MAX_FILE_BYTES:
            message = "Python boundary exceeds its 8 MiB source-file limit"
            raise BudgetExceededError(message)
    from library_deep_enrichment.corpus.encoding import bytes_digest

    source_digest = bytes_digest(bytes(source))
    if source_digest != raw["payload"].get("source_digest"):
        message = "Python owner does not describe the retained file bytes"
        raise CorpusError(message)
    syntax_facts = _facts(reader, owner.artifact, owner.file)
    typed_facts = _facts(reader, request.types, typed_source.path)
    calls = _calls(owner, syntax_facts, typed_facts, source_digest)
    return PythonBoundary(
        logical_id=f"python-boundary:{request.logical_id}",
        profile=request.profile,
        request=revision_of(request),
        model=MODEL,
        syntax_source=revision_of(syntax_source),
        typed_source=revision_of(typed_source),
        calls=calls,
        frontier=(
            "Call targets remain candidates at their retained dispatch certainty; target identity does not establish callee effects",
            "Native/shared-object bodies remain outside Python source; no cross-language owner identity is inferred from spelling",
            "Nested source owners are excluded; the complete denominator is this exact function owner",
        ),
        support=(
            select(owner, "/original", "source-owner"),
            select(syntax, "/sources", "syntax-source-universe"),
            select(types, "/sources", "typed-source-universe"),
            *(
                select(fact, "/original", "source-file-fact-universe")
                for fact, _ in (*syntax_facts, *typed_facts)
            ),
        ),
    )


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Recompute typed call packets before admission.

    Raises:
        CorpusError: A packet changes its call denominator or candidate/source membership.

    """
    for record in records:
        if isinstance(record, PythonBoundary):
            request = reader.get("python_boundary_requests", record.request)
            if not isinstance(request, PythonBoundaryRequest) or analyze(reader, request) != record:
                message = "Python boundary differs from exact source-alignment replay"
                raise CorpusError(message)
