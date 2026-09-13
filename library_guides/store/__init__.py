"""Artifact store: digests, deterministic JSONL, receipts, atomic publication."""

from __future__ import annotations

from library_guides.store.digests import (
    canonical_bytes,
    content_addressed,
    digest_bytes,
    digest_file,
    digest_mapping,
    digest_sequence,
)
from library_guides.store.jsonl import encode_line, read_records, write_records
from library_guides.store.receipts import (
    ReceiptRequest,
    build_receipt,
    configuration_digest,
    merge_completion,
)
from library_guides.store.staging import (
    PublicationRefusedError,
    StagedBundle,
    publish_bundle,
    write_atomic,
)

__all__ = [
    "PublicationRefusedError",
    "ReceiptRequest",
    "StagedBundle",
    "build_receipt",
    "canonical_bytes",
    "configuration_digest",
    "content_addressed",
    "digest_bytes",
    "digest_file",
    "digest_mapping",
    "digest_sequence",
    "encode_line",
    "merge_completion",
    "publish_bundle",
    "read_records",
    "write_atomic",
    "write_records",
]
