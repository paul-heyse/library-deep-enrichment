"""Typed Arrow storage for contextual call shapes."""

import pyarrow as pa

from library_deep_enrichment.corpus.schemas import SELECTIONS, TEXTS, fields, register
from library_deep_enrichment.semantics.schemas import SLOT
from library_deep_enrichment.semantics.type_shapes import OperationShape

SLOTS = pa.list_(pa.field("item", SLOT, nullable=False))
register(
    "operation_shapes",
    OperationShape,
    [
        *fields("operation"),
        ("inputs", SLOTS),
        ("outputs", SLOTS),
        ("support", SELECTIONS),
        ("frontier", TEXTS),
    ],
)
