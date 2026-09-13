"""Portable layouts for source-aligned typing and declaration-location observations."""

import pyarrow as pa

from library_guides.analyses.behavior.typing_contracts import BehaviorTyping
from library_guides.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

DECLARATIONS = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("path", "name", "category", "source")
            ],
            *[pa.field(name, NUMBER, nullable=False) for name in ("start", "end")],
            *[pa.field(name, TEXT, nullable=False) for name in ("state", "identity")],
        ]
    )
)
POINTS = pa.list_(
    pa.struct(
        [
            *[pa.field(name, TEXT, nullable=False) for name in ("fact", "role")],
            *[pa.field(name, NUMBER, nullable=False) for name in ("start", "end")],
            pa.field("expected_fallback", pa.bool_(), nullable=False),
            pa.field("declarations", DECLARATIONS, nullable=False),
        ]
    )
)
register(
    "behavior_typing",
    BehaviorTyping,
    [
        *fields("request", "program", "artifact", "context", "source", "model"),
        ("points", POINTS),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
