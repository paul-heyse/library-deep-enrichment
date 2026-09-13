"""Explicit Arrow layouts for versioned executable facts and behavioral consequences."""

import pyarrow as pa

from library_deep_enrichment.analyses.behavior.contracts import (
    BehaviorProgram,
    BehaviorRequest,
    BehaviorSummary,
)
from library_deep_enrichment.analyses.behavior.coverage import BehaviorCoverage
from library_deep_enrichment.analyses.behavior.origins import BehaviorOrigins
from library_deep_enrichment.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

NUMBERS = pa.list_(pa.field("item", NUMBER, nullable=False))
TERMS = pa.list_(
    pa.struct(
        [
            pa.field("op", TEXT, nullable=False),
            pa.field("args", NUMBERS, nullable=False),
            pa.field("value", TEXT, nullable=False),
            pa.field("ty", TEXT, nullable=False),
        ]
    )
)
FRONTIERS = pa.list_(
    pa.struct(
        [pa.field(name, TEXT, nullable=False) for name in ("code", "dimension", "point", "detail")]
    )
)
LIMITS = pa.struct(
    [
        pa.field(name, NUMBER, nullable=False)
        for name in (
            "owners",
            "steps",
            "states",
            "clauses",
            "terms",
            "call_depth",
            "solver_ms",
            "solver_queries",
            "widen_after",
        )
    ]
)
BINDINGS = pa.list_(
    pa.struct(
        [
            pa.field("caller", TEXT, nullable=False),
            pa.field("point", NUMBER, nullable=False),
            pa.field("targets", TEXTS, nullable=False),
            pa.field("substitutions", TEXTS, nullable=False),
            pa.field("complete", pa.bool_(), nullable=False),
            pa.field("evidence", SELECTIONS, nullable=False),
        ]
    )
)
INSTRUCTIONS = pa.list_(
    pa.struct(
        [
            *[pa.field(name, NUMBER, nullable=False) for name in ("block", "index")],
            *[pa.field(name, TEXT, nullable=False) for name in ("op", "destination")],
            pa.field("value", NUMBER, nullable=False),
            pa.field("arguments", NUMBERS, nullable=False),
            pa.field("target", TEXT, nullable=False),
            *[pa.field(name, NUMBER, nullable=False) for name in ("start", "end")],
        ]
    )
)
EDGES = pa.list_(
    pa.struct(
        [
            pa.field("source", NUMBER, nullable=False),
            pa.field("target", NUMBER, nullable=False),
            pa.field("kind", TEXT, nullable=False),
            pa.field("condition", NUMBER, nullable=False),
            pa.field("positive", pa.bool_(), nullable=False),
        ]
    )
)
GUARDS = pa.list_(
    pa.struct(
        [
            pa.field("term", NUMBER, nullable=False),
            pa.field("positive", pa.bool_(), nullable=False),
        ]
    )
)
MEMORY = pa.list_(
    pa.struct(
        [
            pa.field("location", TEXT, nullable=False),
            pa.field("term", NUMBER, nullable=False),
            pa.field("strong", pa.bool_(), nullable=False),
        ]
    )
)
EFFECTS = pa.list_(
    pa.struct(
        [pa.field(name, TEXT, nullable=False) for name in ("kind", "target", "phase", "point")]
    )
)
REGIONS = pa.list_(
    pa.struct(
        [
            *[pa.field(name, NUMBER, nullable=False) for name in ("root", "contents", "extent")],
            *[pa.field(name, TEXT, nullable=False) for name in ("kind", "owner")],
            *[pa.field(name, pa.bool_(), nullable=False) for name in ("unique", "escaped")],
        ]
    )
)
CLAUSES = pa.list_(
    pa.struct(
        [
            pa.field("guards", GUARDS, nullable=False),
            pa.field("outcome", TEXT, nullable=False),
            pa.field("result", NUMBER, nullable=False),
            pa.field("memory", MEMORY, nullable=False),
            pa.field("effects", EFFECTS, nullable=False),
            pa.field("assumptions", TEXTS, nullable=False),
            pa.field("frontier", FRONTIERS, nullable=False),
            pa.field("regions", REGIONS, nullable=False),
        ]
    )
)
METRICS = pa.list_(
    pa.struct(
        [
            pa.field("name", TEXT, nullable=False),
            pa.field("value", NUMBER, nullable=False),
        ]
    )
)
MEMBERS = pa.list_(
    pa.struct(
        [
            pa.field("index", NUMBER, nullable=False),
            *[pa.field(name, TEXT, nullable=False) for name in ("name", "definition", "type_name")],
        ]
    )
)
VARIANTS = pa.list_(
    pa.struct(
        [
            pa.field("index", NUMBER, nullable=False),
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("name", "discriminant", "discriminant_type")
            ],
            pa.field("fields", MEMBERS, nullable=False),
        ]
    )
)
NOMINALS = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("definition", "name", "kind", "member_type_policy")
            ],
            pa.field("variants", VARIANTS, nullable=False),
        ]
    )
)

register(
    "behavior_requests",
    BehaviorRequest,
    [
        ("owners", TEXTS),
        ("artifacts", TEXTS),
        ("type_artifacts", TEXTS),
        ("bindings", BINDINGS),
        ("limits", LIMITS),
        ("phase", TEXT),
    ],
)
register(
    "behavior_programs",
    BehaviorProgram,
    [
        *fields("request", "owner", "artifact", "context", "language", "symbol", "model"),
        ("parameters", TEXTS),
        ("terms", TERMS),
        ("instructions", INSTRUCTIONS),
        ("edges", EDGES),
        ("blocks", NUMBERS),
        ("entry", NUMBER),
        ("frontier", FRONTIERS),
        ("support", SELECTIONS),
        ("phase", TEXT),
        ("nominals", NOMINALS),
    ],
)
register(
    "behavior_summaries",
    BehaviorSummary,
    [
        *fields("request", "program", "model"),
        ("terms", TERMS),
        ("clauses", CLAUSES),
        *fields("precision"),
        ("frontier", FRONTIERS),
        ("dependencies", TEXTS),
        ("metrics", METRICS),
        ("support", SELECTIONS),
    ],
)
register(
    "behavior_coverage",
    BehaviorCoverage,
    [
        *fields("request", "owner", "program", "summary", "state", "phase", "detail"),
        ("metrics", METRICS),
    ],
)

VALUE_ORIGINS = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("program", "operation", "mode", "phase")
            ],
            pa.field("instruction", NUMBER, nullable=False),
            pa.field("result", NUMBER, nullable=False),
            pa.field("arguments", NUMBERS, nullable=False),
            pa.field("guards", GUARDS, nullable=False),
            pa.field("assumptions", TEXTS, nullable=False),
        ]
    )
)
register(
    "behavior_origins",
    BehaviorOrigins,
    [
        *fields("request", "summary", "model"),
        ("entries", VALUE_ORIGINS),
        ("support", SELECTIONS),
    ],
)
