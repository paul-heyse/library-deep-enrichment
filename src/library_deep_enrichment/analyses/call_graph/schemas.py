"""Owned Arrow layouts for complete native call catalogs and bounded selections."""

import pyarrow as pa

from library_deep_enrichment.analyses.behavior.schemas import LIMITS
from library_deep_enrichment.analyses.call_graph.contracts import (
    CallableClosure,
    CallClosure,
    CallClosureRequest,
    CallIndex,
    CallIndexRequest,
    LifecycleClosure,
)
from library_deep_enrichment.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

ARGUMENTS = pa.list_(
    pa.struct(
        [
            pa.field("position", NUMBER, nullable=False),
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("kind", "scalar", "encoding", "type_fingerprint")
            ],
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
CALLS = pa.list_(
    pa.struct(
        [
            pa.field("block", NUMBER, nullable=False),
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("declaration", "target", "instance_kind")
            ],
            pa.field("complete", pa.bool_(), nullable=False),
            pa.field("substitutions", ARGUMENTS, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
OWNERS = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("owner", "artifact", "context", "definition", "phase")
            ],
            pa.field("native_bytes", NUMBER, nullable=False),
            pa.field("calls", CALLS, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
SELECTED = pa.list_(
    pa.struct(
        [
            *[pa.field(name, TEXT, nullable=False) for name in ("caller", "target", "state")],
            pa.field("block", NUMBER, nullable=False),
            pa.field("candidates", TEXTS, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
register(
    "call_index_requests",
    CallIndexRequest,
    [("artifacts", TEXTS), ("max_facts", NUMBER), ("max_bytes", NUMBER)],
)
register(
    "call_indexes",
    CallIndex,
    [*fields("request", "model"), ("owners", OWNERS), ("frontier", TEXTS), ("support", SELECTIONS)],
)
register(
    "call_closure_requests",
    CallClosureRequest,
    [*fields("index"), ("roots", TEXTS), ("max_depth", NUMBER), ("limits", LIMITS)],
)
register(
    "call_closures",
    CallClosure,
    [
        *fields("request", "index", "model", "behavior"),
        ("roots", TEXTS),
        ("helpers", TEXTS),
        ("calls", SELECTED),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
register(
    "callable_closures",
    CallableClosure,
    [
        *fields("request", "index", "model", "behavior"),
        ("roots", TEXTS),
        ("helpers", TEXTS),
        ("calls", SELECTED),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
        (
            "references",
            pa.list_(
                pa.struct(
                    [
                        pa.field("statement", NUMBER, nullable=False),
                        pa.field("role", TEXT, nullable=False),
                        pa.field("operand", NUMBER, nullable=False),
                        pa.field("selection", SELECTED.value_type, nullable=False),
                    ]
                )
            ),
        ),
    ],
)
register(
    "lifecycle_closures",
    LifecycleClosure,
    [
        *fields("request", "index", "model", "behavior"),
        ("roots", TEXTS),
        ("helpers", TEXTS),
        ("calls", SELECTED),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
        (
            "references",
            pa.list_(
                pa.struct(
                    [
                        pa.field("statement", NUMBER, nullable=False),
                        pa.field("role", TEXT, nullable=False),
                        pa.field("operand", NUMBER, nullable=False),
                        pa.field("selection", SELECTED.value_type, nullable=False),
                    ]
                )
            ),
        ),
        ("drops", SELECTED),
    ],
)
