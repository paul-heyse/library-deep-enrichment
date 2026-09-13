"""Typed Arrow storage for contextual call shapes."""

import pyarrow as pa

from library_guides.corpus.schemas import SELECTIONS, TEXTS, fields, register
from library_guides.semantics.schemas import SLOT
from library_guides.semantics.type_shapes import OperationShape

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
