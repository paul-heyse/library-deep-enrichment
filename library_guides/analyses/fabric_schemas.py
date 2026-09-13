"""Explicit Arrow fields for the reusable native source analysis surface."""

import pyarrow as pa

from library_guides.analyses.fabric_contracts import (
    AnalysisRequest,
    PythonBoundary,
    PythonBoundaryRequest,
    SourceAnalysis,
)
from library_guides.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

register("analysis_requests", AnalysisRequest, [*fields("artifact"), ("owners", TEXTS)])
register("python_boundary_requests", PythonBoundaryRequest, fields("owner", "types"))
register(
    "python_boundaries",
    PythonBoundary,
    [
        *fields("request", "model", "syntax_source", "typed_source"),
        (
            "calls",
            pa.list_(
                pa.struct(
                    [
                        pa.field("site", TEXT, nullable=False),
                        pa.field("start", NUMBER, nullable=False),
                        pa.field("end", NUMBER, nullable=False),
                        pa.field("lexical", TEXTS, nullable=False),
                        pa.field("targets", TEXTS, nullable=False),
                        pa.field("state", TEXT, nullable=False),
                    ]
                )
            ),
        ),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
register(
    "source_analyses",
    SourceAnalysis,
    [
        *fields("request", "owner", "model"),
        ("reachable", pa.list_(pa.field("item", NUMBER, nullable=False))),
        ("return_dependencies", TEXTS),
        ("may_effects", TEXTS),
        ("local_callees", TEXTS),
        ("effect_closed", pa.bool_()),
        (
            "control",
            pa.list_(
                pa.field(
                    "item",
                    pa.struct(
                        [
                            pa.field(name, NUMBER, nullable=False)
                            for name in ("branch", "successor", "dependent")
                        ]
                    ),
                    nullable=False,
                )
            ),
        ),
        *fields("control_state", "control_policy"),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
