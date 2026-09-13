"""Portable layouts for exact evidence-linked behavioral dimensions."""

import pyarrow as pa

from library_deep_enrichment.analyses.characterization.contracts import (
    BehaviorCharacterization,
    CharacterizationRequest,
)
from library_deep_enrichment.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

INTEGERS = pa.list_(pa.field("item", NUMBER, nullable=False))
USES = pa.list_(
    pa.struct(
        [
            pa.field("kind", TEXT, nullable=False),
            *[pa.field(name, NUMBER, nullable=False) for name in ("clause", "term", "point")],
        ]
    )
)
DEPENDENCIES = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("kind", "name", "space", "qualification")
            ],
            pa.field("term", NUMBER, nullable=False),
            pa.field("uses", USES, nullable=False),
        ]
    )
)
COSTS = pa.list_(
    pa.struct(
        [
            pa.field("metric", TEXT, nullable=False),
            pa.field("lower", NUMBER, nullable=False),
            pa.field("upper", INTEGERS, nullable=False),
            pa.field("basis", TEXT, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
RESOURCES = pa.list_(
    pa.struct(
        [
            *[pa.field(name, NUMBER, nullable=False) for name in ("clause", "root", "extent")],
            pa.field("kind", TEXT, nullable=False),
            *[
                pa.field(name, TEXTS, nullable=False)
                for name in ("argument_dependencies", "ambient_dependencies", "frontier")
            ],
            pa.field("escaped", pa.bool_(), nullable=False),
            pa.field("unique", pa.bool_(), nullable=False),
        ]
    )
)
ORDERING = pa.list_(
    pa.struct(
        [
            pa.field("clause", NUMBER, nullable=False),
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("kind", "target", "point", "phase", "obligation")
            ],
        ]
    )
)

register(
    "characterization_requests",
    CharacterizationRequest,
    [
        ("behaviors", TEXTS),
        *[(name, NUMBER) for name in ("max_owners", "max_terms", "max_work")],
    ],
)
register(
    "behavior_characterizations",
    BehaviorCharacterization,
    [
        *fields("request", "behavior", "owner", "coverage", "program", "summary", "model", "state"),
        ("dependencies", DEPENDENCIES),
        ("costs", COSTS),
        ("resources", RESOURCES),
        ("ordering", ORDERING),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
