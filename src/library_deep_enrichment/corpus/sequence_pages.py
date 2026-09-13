"""Bounded nested-sequence inspection for complete large comparisons and proof scopes."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from attrs import frozen

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical, digest, payload
from library_deep_enrichment.corpus.evidence import field_value
from library_deep_enrichment.corpus.paging import MAX_BYTES, MAX_CURSOR_BYTES, MAX_ROWS

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.store import CorpusReader


@frozen(kw_only=True)
class SequenceRequest:
    """An exact record field; offsets are carried only in pinned continuations."""

    family: str
    revision: str
    field: str
    continuation: str = ""
    max_rows: int = 20
    max_bytes: int = MAX_BYTES


@frozen(kw_only=True)
class SequenceCursor:
    """A position in one immutable record field and manifest."""

    manifest: str
    family: str
    revision: str
    field: str
    offset: int


@frozen(kw_only=True)
class SequencePage:
    """Exact denominator, ordered values and an unambiguous byte/row frontier."""

    manifest: str
    family: str
    revision: str
    field: str
    values: tuple[object, ...]
    consumed: int
    eligible: int
    complete: bool
    continuation: str
    limit_reason: str


def _token(cursor: SequenceCursor) -> str:
    body = CONVERTER.unstructure(cursor)
    return canonical({"cursor": body, "digest": digest(body)}).decode()


def _offset(reader: CorpusReader, request: SequenceRequest) -> int:
    if not request.continuation:
        return 0
    if len(request.continuation.encode()) > MAX_CURSOR_BYTES:
        message = "sequence continuation exceeds its envelope"
        raise CorpusError(message)
    body = json.loads(request.continuation)
    if set(body) != {"cursor", "digest"} or digest(body["cursor"]) != body["digest"]:
        message = "sequence continuation integrity check failed"
        raise CorpusError(message)
    cursor = CONVERTER.structure(body["cursor"], SequenceCursor)
    if (cursor.manifest, cursor.family, cursor.revision, cursor.field) != (
        reader.manifest_id,
        request.family,
        request.revision,
        request.field,
    ) or cursor.offset < 0:
        message = "sequence continuation belongs to another manifest, record or field"
        raise CorpusError(message)
    return cursor.offset


def read(reader: CorpusReader, request: SequenceRequest) -> SequencePage:
    """Page an exact JSON-pointer sequence without truncating its stored proof or universe.

    Returns:
        A bounded response; an oversized value leaves its cursor unconsumed for narrower inspection.

    Raises:
        CorpusError: The request is unbounded, stale, outside membership, or not a sequence.

    """
    if not 1 <= request.max_rows <= MAX_ROWS or not 1 <= request.max_bytes <= MAX_BYTES:
        message = "sequence page requires 1..200 rows and 1..900000 bytes"
        raise CorpusError(message)
    values = field_value(payload(reader.get(request.family, request.revision)), request.field)
    if not isinstance(values, list):
        message = "selected field is not an ordered sequence"
        raise CorpusError(message)
    offset = _offset(reader, request)
    if offset > len(values):
        message = "sequence continuation exceeds the exact denominator"
        raise CorpusError(message)
    retained: list[object] = []
    size = 0
    reason = ""
    for value in values[offset : offset + request.max_rows]:
        item_size = len(canonical(value))
        if size + item_size > request.max_bytes:
            reason = "byte limit; inspect a narrower nested field for an oversized value"
            break
        retained.append(value)
        size += item_size
    consumed = offset + len(retained)
    complete = consumed == len(values)
    return SequencePage(
        manifest=reader.manifest_id,
        family=request.family,
        revision=request.revision,
        field=request.field,
        values=tuple(retained),
        consumed=consumed,
        eligible=len(values),
        complete=complete,
        continuation=""
        if complete
        else _token(
            SequenceCursor(
                manifest=reader.manifest_id,
                family=request.family,
                revision=request.revision,
                field=request.field,
                offset=consumed,
            )
        ),
        limit_reason=reason or ("" if complete else "row limit"),
    )
