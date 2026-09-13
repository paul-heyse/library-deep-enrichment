"""Persistent stage declarations with explicit input-family structure."""

import pyarrow as pa

from library_deep_enrichment.corpus.schemas import NUMBER, TEXT, TEXTS, fields, register
from library_deep_enrichment.workflows.contracts import ExecutionReceipt, InputReceipt, StageDefinition
from library_deep_enrichment.workflows.failure_records import FailureReceipt

INPUT = pa.struct(
    [pa.field("family", TEXT, nullable=False), pa.field("fields", TEXTS, nullable=False)]
)
register(
    "stage_definitions",
    StageDefinition,
    [
        ("inputs", pa.list_(pa.field("item", INPUT, nullable=False))),
        ("outputs", TEXTS),
        ("dependencies", TEXTS),
        *fields("implementation"),
        ("max_records", NUMBER),
        ("max_bytes", NUMBER),
        ("max_seconds", pa.float64()),
    ],
)

SELECTOR = pa.struct(
    [
        pa.field("family", TEXT, nullable=False),
        pa.field("profiles", TEXTS, nullable=False),
        pa.field("logical_ids", TEXTS, nullable=False),
        pa.field("prefix", TEXT, nullable=False),
    ]
)
register(
    "stage_input_receipts",
    InputReceipt,
    [
        *fields("stage", "definition"),
        ("selector", SELECTOR),
        ("fields", TEXTS),
        ("count", NUMBER),
        *fields("membership"),
    ],
)

register(
    "stage_executions",
    ExecutionReceipt,
    [
        *fields("definition", "request", "input_manifest", "route"),
        ("elapsed_seconds", pa.float64()),
        *[
            (name, NUMBER)
            for name in (
                "peak_sampled_tree_rss_bytes",
                "output_bytes",
                "records",
                "rss_limit_bytes",
                "address_space_limit_bytes",
            )
        ],
    ],
)

WORKER_OBSERVATION = pa.struct(
    [
        *[
            pa.field(name, TEXT, nullable=False)
            for name in ("request", "input_digest", "internal_progress")
        ],
        pa.field("elapsed_seconds", pa.float64(), nullable=False),
        *[
            pa.field(name, NUMBER, nullable=False)
            for name in (
                "peak_sampled_tree_rss_bytes",
                "rss_samples",
                "output_bytes",
                "delivered_records",
                "consumed_records",
                "returncode",
                "rss_limit_bytes",
                "address_space_limit_bytes",
            )
        ],
        pa.field(
            "expected_records", pa.list_(pa.field("item", NUMBER, nullable=False)), nullable=False
        ),
        pa.field("terminal_seen", pa.bool_(), nullable=False),
    ]
)
register(
    "stage_failures",
    FailureReceipt,
    [
        *fields("definition", "job", "request", "input_manifest", "phase", "interpretation"),
        *[
            (name, NUMBER)
            for name in (
                "collected_records",
                "collected_payload_bytes",
                "coordinator_high_water_before_bytes",
                "coordinator_high_water_after_bytes",
            )
        ],
        ("elapsed_seconds", pa.float64()),
        ("worker", pa.list_(pa.field("item", WORKER_OBSERVATION, nullable=False))),
    ],
)
