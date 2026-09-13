"""Explicit Arrow schemas for source, mode, transfer, and experiment records."""

import pyarrow as pa

from library_deep_enrichment.corpus.schemas import (
    BYTE_RANGE,
    NUMBER,
    SELECTIONS,
    TEXT,
    TEXTS,
    fields,
    register,
)
from library_deep_enrichment.semantics import enrichment_contracts as c
from library_deep_enrichment.semantics.schemas import ASSIGNMENT, SLOTS, VALUE

VALUES = pa.list_(pa.field("item", VALUE, nullable=False))
ASSIGNMENTS = pa.list_(pa.field("item", ASSIGNMENT, nullable=False))
TRANSFER_RULE = pa.struct(
    [
        pa.field("output", TEXT, nullable=False),
        pa.field("operator", TEXT, nullable=False),
        pa.field("inputs", TEXTS, nullable=False),
        pa.field("value", VALUE, nullable=False),
    ]
)
register(
    "document_statements",
    c.DocumentStatement,
    [
        *fields("owner", "passage"),
        ("start", NUMBER),
        ("end", NUMBER),
        *fields("text", "section", "role", "subject"),
        ("qualifiers", TEXTS),
        ("links", TEXTS),
        *fields("interpretation"),
        ("support", SELECTIONS),
    ],
)
register(
    "parameter_modes",
    c.ParameterMode,
    [
        *fields("operation"),
        ("position", NUMBER),
        *fields("name", "kind"),
        ("required", pa.bool_()),
        *fields("default_expression", "default_status"),
        ("default_value", VALUE),
        ("domain", VALUES),
        ("support", SELECTIONS),
    ],
)
register(
    "transfer_models",
    c.TransferModel,
    [
        *fields("name", "condition"),
        ("rules", pa.list_(pa.field("item", TRANSFER_RULE, nullable=False))),
        *fields("description"),
    ],
)
register(
    "transfer_mappings",
    c.TransferMapping,
    [
        *fields("operation", "model", "condition", "interpretation", "scope"),
        ("support", SELECTIONS),
    ],
)
register(
    "state_transfers",
    c.StateTransfer,
    [
        *fields("mapping"),
        ("inputs", ASSIGNMENTS),
        ("outputs", ASSIGNMENTS),
        *fields("condition_state", "interpretation", "scope"),
        ("frontier", TEXTS),
    ],
)
register(
    "witness_recipes",
    c.WitnessRecipe,
    [
        *fields("name", "language"),
        ("program", BYTE_RANGE),
        ("manifest", BYTE_RANGE),
        ("packages", TEXTS),
        *fields("toolchain", "description"),
        ("fields", TEXTS),
    ],
)
register(
    "witness_runs",
    c.WitnessRun,
    [
        *fields("recipe", "context"),
        ("command", TEXTS),
        ("stdout", BYTE_RANGE),
        ("stderr", BYTE_RANGE),
        ("lockfile", BYTE_RANGE),
        ("returncode", NUMBER),
        *fields("isolation", "disposition"),
    ],
)
register(
    "witness_observations",
    c.WitnessObservation,
    [
        *fields("operation", "run", "field"),
        ("value", VALUE),
        *fields("scope"),
        ("support", SELECTIONS),
    ],
)
register(
    "evidence_requests",
    c.EvidenceRequest,
    [
        *fields("subject", "predicate", "lane", "query", "expected_information", "reason"),
        ("dependencies", SELECTIONS),
    ],
)
register(
    "invocation_contracts",
    c.InvocationContract,
    [
        *fields("capability", "mapping", "expression"),
        ("inputs", SLOTS),
        ("outputs", SLOTS),
        ("support", SELECTIONS),
        ("frontier", TEXTS),
    ],
)
register("composition_goals", c.CompositionGoal, [*fields("task"), ("required", ASSIGNMENTS)])
register(
    "composition_evaluations",
    c.CompositionEvaluation,
    [
        *fields("composition", "goal", "disposition"),
        ("invocations", TEXTS),
        ("transfers", TEXTS),
        ("outputs", ASSIGNMENTS),
        ("frontier", TEXTS),
    ],
)
register(
    "composition_programs",
    c.CompositionProgram,
    [
        *fields("composition"),
        ("inputs", ASSIGNMENTS),
        ("prologue", BYTE_RANGE),
        ("epilogue", BYTE_RANGE),
        ("program", BYTE_RANGE),
    ],
)
register(
    "composition_witnesses",
    c.CompositionWitness,
    [*fields("evaluation", "program", "run", "disposition"), ("fields", ASSIGNMENTS)],
)
