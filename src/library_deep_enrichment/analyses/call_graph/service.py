"""Replay, invalidation and portable references for call catalogs and helper selections."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.analyses.behavior.integrity import require
from library_deep_enrichment.analyses.call_graph import closure, index
from library_deep_enrichment.analyses.call_graph.contracts import (
    CallClosure,
    CallClosureRequest,
    CallIndex,
    CallIndexRequest,
)
from library_deep_enrichment.corpus.schemas import revision_of

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Expose both exact owner support and the finite catalog underlying target absence.

    Returns:
        Prerequisites for admission, dependency withdrawal and portable closure.

    """
    if isinstance(record, CallIndexRequest):
        return tuple(("native_artifacts", item) for item in record.artifacts)
    if isinstance(record, CallIndex):
        return (
            ("call_index_requests", record.request),
            *(("native_facts", item.owner) for item in record.owners),
        )
    if isinstance(record, CallClosureRequest):
        return (("call_indexes", record.index), *(("native_facts", item) for item in record.roots))
    if isinstance(record, CallClosure):
        return (
            ("call_closure_requests", record.request),
            ("call_indexes", record.index),
            ("behavior_requests", record.behavior),
        )
    return ()


def validate(reader: CorpusReader, records: tuple[Record, ...]) -> None:
    """Reject catalog omissions, forged targets and selections that differ from replay."""
    for record in records:
        if isinstance(record, CallIndexRequest):
            index.analyze(reader, record)
        elif isinstance(record, CallClosureRequest):
            closure.analyze(reader, record)
        elif isinstance(record, CallIndex):
            request = reader.get("call_index_requests", record.request)
            assert isinstance(request, CallIndexRequest)
            require(
                "native call index differs from complete catalog replay",
                condition=record == index.analyze(reader, request),
            )
        elif isinstance(record, CallClosure):
            request = reader.get("call_closure_requests", record.request)
            assert isinstance(request, CallClosureRequest)
            expected, behavior = closure.analyze(reader, request)
            require(
                "native helper selection differs from contextual replay",
                condition=record == expected
                and reader.get("behavior_requests", revision_of(behavior)) == behavior,
            )
