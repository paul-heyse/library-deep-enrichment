"""Physical family schemas for native receipts and contextual fact identities."""

import pyarrow as pa

from library_guides.corpus import native_contracts as c
from library_guides.corpus.schemas import BYTE_RANGE, NUMBER, TEXTS, fields, register

register(
    "native_artifacts",
    c.NativeArtifact,
    [
        *fields("external_id", "lane", "schema", "context"),
        ("input", BYTE_RANGE),
        ("header", BYTE_RANGE),
        ("receipt", BYTE_RANGE),
        ("shards", pa.list_(pa.field("item", BYTE_RANGE, nullable=False))),
        ("shard_counts", pa.list_(pa.field("item", NUMBER, nullable=False))),
        ("sources", TEXTS),
        ("record_count", NUMBER),
        *fields("disposition"),
        ("frontier", TEXTS),
    ],
)
register(
    "native_facts",
    c.NativeFact,
    [*fields("artifact", "native_id", "kind", "symbol", "file", "owner"), ("original", BYTE_RANGE)],
)
