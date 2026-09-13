"""Owned portable layouts for finite callable populations."""

import pyarrow as pa

from library_deep_enrichment.analyses.callable_contracts import CallablePopulation, CallableRequest
from library_deep_enrichment.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

BODIES = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("owner", "artifact", "context", "definition", "phase", "source")
            ],
            pa.field("start", NUMBER, nullable=False),
            pa.field("end", NUMBER, nullable=False),
            pa.field("state", TEXT, nullable=False),
        ]
    )
)
CANDIDATES = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("declaration", "context", "identity", "symbol")
            ],
            pa.field("routes", TEXTS, nullable=False),
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("reachability", "scope", "path", "source")
            ],
            pa.field("start", NUMBER, nullable=False),
            pa.field("end", NUMBER, nullable=False),
            pa.field("bodies", BODIES, nullable=False),
            pa.field("disposition", TEXT, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
register(
    "callable_requests",
    CallableRequest,
    [
        ("interfaces", TEXTS),
        ("executables", TEXTS),
        ("files", TEXTS),
        ("max_facts", NUMBER),
        ("max_bytes", NUMBER),
    ],
)
register(
    "callable_populations",
    CallablePopulation,
    [
        *fields("request", "model"),
        ("candidates", CANDIDATES),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
