"""Portable layouts for observed compilation contexts and unresolved candidate joins."""

import pyarrow as pa

from library_deep_enrichment.analyses.compilation_contracts import CompilationPopulation, CompilationRequest
from library_deep_enrichment.corpus.schemas import NUMBER, SELECTIONS, TEXT, TEXTS, fields, register

SETTINGS = pa.list_(
    pa.struct(
        [
            pa.field("name", TEXT, nullable=False),
            pa.field("values", TEXTS, nullable=False),
            pa.field("state", TEXT, nullable=False),
        ]
    )
)
INPUTS = pa.list_(
    pa.struct(
        [pa.field(name, TEXT, nullable=False) for name in ("path", "digest", "source", "state")]
    )
)
CANDIDATES = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in ("metadata", "message", "package_id", "target_source")
            ],
            pa.field("declared_features", SETTINGS, nullable=False),
            pa.field("resolved_features", TEXTS, nullable=False),
            pa.field("compiled_features", TEXTS, nullable=False),
            pa.field("state", TEXT, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
UNITS = pa.list_(
    pa.struct(
        [
            *[
                pa.field(name, TEXT, nullable=False)
                for name in (
                    "artifact",
                    "context",
                    "invocation",
                    "invocation_source",
                    "compiler",
                    "producer",
                    "working_directory",
                )
            ],
            pa.field("inputs", INPUTS, nullable=False),
            pa.field("settings", SETTINGS, nullable=False),
            pa.field("candidates", CANDIDATES, nullable=False),
            pa.field("state", TEXT, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
COMMANDS = pa.list_(
    pa.struct(
        [
            *[pa.field(name, TEXT, nullable=False) for name in ("artifact", "source", "observer")],
            pa.field("settings", SETTINGS, nullable=False),
            pa.field("frontier", TEXTS, nullable=False),
        ]
    )
)
register(
    "compilation_requests",
    CompilationRequest,
    [
        ("executables", TEXTS),
        ("metadata", TEXTS),
        ("messages", TEXTS),
        ("max_facts", NUMBER),
        ("max_bytes", NUMBER),
    ],
)
register(
    "compilation_populations",
    CompilationPopulation,
    [
        *fields("request", "model"),
        ("units", UNITS),
        ("commands", COMMANDS),
        ("frontier", TEXTS),
        ("support", SELECTIONS),
    ],
)
