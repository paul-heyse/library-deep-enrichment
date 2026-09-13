"""Family-specific Arrow schemas for computational semantic records."""

from __future__ import annotations

import pyarrow as pa

from library_guides.corpus.schemas import SELECTIONS, TEXT, TEXTS, fields, register
from library_guides.semantics import contracts as c

VALUE = pa.struct([pa.field("kind", TEXT, nullable=False), pa.field("text", TEXT, nullable=False)])
SLOT = pa.struct(
    [
        *[
            pa.field(name, TEXT, nullable=False)
            for name in ("role", "type_expression", "representation", "resource")
        ],
        pa.field("consumes", pa.bool_(), nullable=False),
    ]
)
SLOTS = pa.list_(pa.field("item", SLOT, nullable=False))
REQUIREMENT = pa.struct(
    [
        pa.field("predicate", TEXT, nullable=False),
        pa.field("value", VALUE, nullable=False),
        pa.field("operator", TEXT, nullable=False),
        pa.field("interpretations", TEXTS, nullable=False),
        pa.field("mandatory", pa.bool_(), nullable=False),
    ]
)
ASSIGNMENT = pa.struct(
    [
        pa.field("variable", TEXT, nullable=False),
        pa.field("value", VALUE, nullable=False),
    ]
)
REQUIREMENT_RESULT = pa.struct(
    [
        pa.field("predicate", TEXT, nullable=False),
        pa.field("required", VALUE, nullable=False),
        pa.field("state", TEXT, nullable=False),
        pa.field("assertions", TEXTS, nullable=False),
        pa.field("reason", TEXT, nullable=False),
    ]
)
CANDIDATE_RESULT = pa.struct(
    [
        *[
            pa.field(name, TEXT, nullable=False)
            for name in ("operation", "capability", "disposition")
        ],
        pa.field(
            "requirements",
            pa.list_(pa.field("item", REQUIREMENT_RESULT, nullable=False)),
            nullable=False,
        ),
        pa.field("reversing_conditions", TEXTS, nullable=False),
    ]
)
PLAN_STEP = pa.struct(
    [
        pa.field("capability", TEXT, nullable=False),
        pa.field("inputs", TEXTS, nullable=False),
        pa.field("outputs", TEXTS, nullable=False),
    ]
)

register(
    "predicates",
    c.Predicate,
    [
        *fields("name", "description", "value_kind", "template"),
        ("allowed_values", TEXTS),
        ("exclusive", pa.bool_()),
        ("interpretations", TEXTS),
    ],
)
register(
    "expressions",
    c.Expression,
    [*fields("operator", "variable"), ("arguments", TEXTS), ("value", VALUE)],
)
register(
    "rules",
    c.Rule,
    [
        *fields(
            "algorithm",
            "source_family",
            "selector",
            "pattern",
            "predicate",
            "condition",
            "quantifier",
            "domain",
            "phase",
            "interpretation",
            "description",
            "version",
        ),
        ("value", VALUE),
    ],
)
register(
    "assertions",
    c.Assertion,
    [
        *fields(
            "subject",
            "predicate",
            "condition",
            "quantifier",
            "domain",
            "phase",
            "interpretation",
            "state",
            "rule",
            "scope",
        ),
        ("value", VALUE),
        ("support", SELECTIONS),
    ],
)
register(
    "proofs",
    c.Proof,
    [
        *fields("conclusion", "rule", "checker"),
        ("premises", SELECTIONS),
        ("read_set", SELECTIONS),
        ("scopes", TEXTS),
        ("steps", TEXTS),
    ],
)
register(
    "modes",
    c.Mode,
    [
        *fields("operation", "condition", "label"),
        ("bindings", TEXTS),
        ("assertions", TEXTS),
    ],
)
register(
    "capabilities",
    c.Capability,
    [
        *fields("schema", "operation", "mode", "condition", "label"),
        ("inputs", SLOTS),
        ("outputs", SLOTS),
        ("assertions", TEXTS),
    ],
)
register(
    "tasks",
    c.Task,
    [
        *fields("goal", "description"),
        ("profiles", TEXTS),
        ("requirements", pa.list_(REQUIREMENT)),
        ("context", pa.list_(ASSIGNMENT)),
        ("inputs", SLOTS),
        ("preferences", TEXTS),
    ],
)
register(
    "comparisons",
    c.Comparison,
    [
        *fields("task", "universe", "disposition"),
        ("candidates", pa.list_(CANDIDATE_RESULT)),
        ("preferred", TEXTS),
        ("unresolved", TEXTS),
    ],
)
register(
    "compositions",
    c.Composition,
    [
        *fields("task", "universe", "disposition"),
        ("steps", pa.list_(PLAN_STEP)),
        ("assertions", TEXTS),
        ("witnesses", TEXTS),
        ("frontier", TEXTS),
    ],
)
register(
    "witnesses",
    c.Witness,
    [
        *fields("operation", "kind", "input_blob", "output_blob", "environment", "scope"),
        ("command", TEXTS),
        ("exit_code", pa.int64()),
        ("assertions", TEXTS),
    ],
)
register(
    "capability_schemas",
    c.CapabilitySchema,
    [
        *fields("name", "description"),
        ("requirements", pa.list_(REQUIREMENT)),
        ("any_qualified_support", pa.bool_()),
    ],
)
