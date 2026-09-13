"""Ordered selected-membership pages with explicit byte limits and pinned continuations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from attrs import frozen
from lancedb.query import ColumnOrdering

from library_deep_enrichment.corpus.backend import CorpusError, literal
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical, digest, payload
from library_deep_enrichment.corpus.schemas import REGISTRY

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.backend import Backend
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader

MAX_ROWS = 200
MAX_BYTES = 900_000
MAX_CURSOR_BYTES = 8192


@frozen(kw_only=True)
class PageRequest:
    """Finite selected-family request; the continuation pins the logical generation."""

    family: str
    profile: str | None = None
    continuation: str = ""
    max_rows: int = 20
    max_bytes: int = MAX_BYTES


@frozen(kw_only=True)
class Cursor:
    """A selection-bound offset in immutable, explicitly ordered membership."""

    manifest: str
    family: str
    profile: str | None
    offset: int


@frozen(kw_only=True)
class Page:
    """A finite response; completion refers only to this exact admitted population."""

    manifest: str
    family: str
    records: tuple[Record, ...]
    consumed: int
    eligible: int
    complete: bool
    continuation: str
    limit_reason: str


def _token(cursor: Cursor) -> str:
    body = CONVERTER.unstructure(cursor)
    return canonical({"cursor": body, "digest": digest(body)}).decode()


def _cursor(token: str, expected: Cursor) -> Cursor:
    if not token:
        return expected
    if len(token.encode()) > MAX_CURSOR_BYTES:
        message = "continuation exceeds its finite envelope"
        raise CorpusError(message)
    body = json.loads(token)
    if set(body) != {"cursor", "digest"} or digest(body["cursor"]) != body["digest"]:
        message = "continuation integrity check failed"
        raise CorpusError(message)
    result = CONVERTER.structure(body["cursor"], Cursor)
    if (result.manifest, result.family, result.profile) != (
        expected.manifest,
        expected.family,
        expected.profile,
    ) or result.offset < 0:
        message = "continuation belongs to a different pinned manifest or selection"
        raise CorpusError(message)
    return result


def read(
    reader: CorpusReader,
    backend: Backend,
    request: PageRequest,
) -> Page:
    """Read an ordered physical projection only after pinning exact membership.

    Returns:
        A page and continuation, including an unchanged cursor for an oversized single record.

    Raises:
        CorpusError: Bounds, selection, or continuation are invalid.

    """
    family, profile = request.family, request.profile
    if (
        family not in REGISTRY
        or not 1 <= request.max_rows <= MAX_ROWS
        or not 1 <= request.max_bytes <= MAX_BYTES
    ):
        message = "page requires a registered family, 1..200 rows and 1..900000 bytes"
        raise CorpusError(message)
    cursor = _cursor(
        request.continuation,
        Cursor(manifest=reader.manifest_id, family=family, profile=profile, offset=0),
    )
    rows: list[Record] = []
    eligible, size, reason = 0, 0, ""
    if reader.manifest is not None:
        predicate = f"manifest = {literal(reader.manifest_id)} AND family = {literal(family)}"
        if profile is not None:
            predicate += f" AND profile = {literal(profile)}"
        table = backend.table("memberships", reader.manifest.membership_version)
        eligible = table.count_rows(predicate)
        if cursor.offset > eligible:
            message = "continuation offset exceeds the pinned denominator"
            raise CorpusError(message)
        query = (
            table.search()
            .where(predicate)
            .select(["revision", "logical_id", "profile"])
            .order_by([ColumnOrdering(column_name=name) for name in ("logical_id", "profile")])
            .offset(cursor.offset)
            .limit(request.max_rows)
        )
        revisions = [str(row["revision"]) for row in query.to_arrow().to_pylist()]
        for record in reader.get_many(family, revisions):
            record_size = len(canonical(payload(record)))
            if size + record_size > request.max_bytes:
                reason = "byte limit; inspect exact fields or increase the page budget"
                break
            size += record_size
            rows.append(record)
    consumed = cursor.offset + len(rows)
    complete = consumed == eligible
    return Page(
        manifest=reader.manifest_id,
        family=family,
        records=tuple(rows),
        consumed=consumed,
        eligible=eligible,
        complete=complete,
        continuation=""
        if complete
        else _token(
            Cursor(manifest=reader.manifest_id, family=family, profile=profile, offset=consumed)
        ),
        limit_reason=reason or ("" if complete else "row limit"),
    )
