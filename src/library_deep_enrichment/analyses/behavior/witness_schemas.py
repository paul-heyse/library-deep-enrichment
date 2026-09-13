"""Portable schemas for finite observation comparisons and their exact prerequisites."""

import pyarrow as pa

from library_deep_enrichment.analyses.behavior.witness_contracts import (
    BehaviorWitnessCheck,
    BehaviorWitnessRequest,
)
from library_deep_enrichment.corpus.schemas import (
    NUMBER,
    SELECTION,
    SELECTIONS,
    TEXT,
    TEXTS,
    fields,
    register,
)

CHECKS = pa.list_(
    pa.struct(
        [
            pa.field("case", TEXT, nullable=False),
            pa.field("verdict", TEXT, nullable=False),
            pa.field("clauses", pa.list_(pa.field("item", NUMBER, nullable=False)), nullable=False),
            pa.field("detail", TEXTS, nullable=False),
        ]
    )
)

register(
    "behavior_witness_requests",
    BehaviorWitnessRequest,
    [
        ("summaries", TEXTS),
        ("observations", SELECTION),
        ("evidence", SELECTIONS),
        ("max_cases", NUMBER),
        ("max_cells", NUMBER),
    ],
)
register(
    "behavior_witness_checks",
    BehaviorWitnessCheck,
    [
        *fields("request", "summary", "model"),
        ("cases", CHECKS),
        ("matched", NUMBER),
        ("inconclusive", NUMBER),
        ("disagreements", NUMBER),
        ("support", SELECTIONS),
    ],
)
