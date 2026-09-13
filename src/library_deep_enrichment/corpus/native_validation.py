"""Recheck native projections against original bytes, rather than trusting identity fields."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.evidence import resolve_bytes
from library_deep_enrichment.corpus.native_contracts import NativeArtifact, NativeFact
from library_deep_enrichment.facts.witness_origins import read as read_witness_origins

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Return exact typed ownership links for release closure and admission.

    Returns:
        Typed family and revision pairs.

    """
    if isinstance(record, NativeFact):
        return (("native_artifacts", record.artifact),)
    if isinstance(record, NativeArtifact):
        return (("contexts", record.context), *(("source_files", item) for item in record.sources))
    return ()


def validate(reader: CorpusReader, record: Record) -> None:
    """Verify projected fields and transport denominators against retained receipts.

    Raises:
        CorpusError: A projection, scope, or transport denominator differs.

    """
    if isinstance(record, NativeFact):
        raw = json.loads(resolve_bytes(reader, record.original, max_bytes=32 * 1024 * 1024))
        payload = raw.get("payload", {})
        actual = (
            str(raw["id"]),
            str(raw.get("kind", payload.get("kind", "unknown"))),
            str(raw.get("symbol", "")),
            str(raw.get("file", "")),
            str(payload.get("owner") or raw.get("owner") or ""),
        )
        expected = (record.native_id, record.kind, record.symbol, record.file, record.owner)
        if actual != expected:
            msg = "native fact projection differs from original worker fields"
            raise CorpusError(msg)
        artifact = reader.get("native_artifacts", record.artifact)
        if not isinstance(artifact, NativeArtifact) or record.profile != artifact.profile:
            msg = "native fact escaped its artifact context"
            raise CorpusError(msg)
        if not any(
            part.blob == record.original.blob
            and part.start <= record.original.start
            and part.end >= record.original.end
            for part in artifact.shards
        ):
            msg = "native fact bytes are outside the verified shard selection"
            raise CorpusError(msg)
    elif isinstance(record, NativeArtifact):
        receipt = json.loads(resolve_bytes(reader, record.receipt, max_bytes=32 * 1024 * 1024))
        read_witness_origins(receipt)
        header = json.loads(resolve_bytes(reader, record.header, max_bytes=32 * 1024 * 1024))
        context_valid = (
            receipt["header"] == header and header["input_digest"] == record.input.digest
        )
        count_valid = (
            len(record.shards) == len(record.shard_counts)
            and sum(record.shard_counts) == record.record_count
            and header["expected_records"] == record.record_count
            and receipt["terminal"]["records"] == record.record_count
        )
        if (
            not context_valid
            or not count_valid
            or receipt["terminal"]["coverage"]["state"] != record.disposition.value
        ):
            msg = "native artifact context or completeness denominator differs"
            raise CorpusError(msg)
