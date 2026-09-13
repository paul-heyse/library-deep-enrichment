"""Arrow contracts for objective policies and exact task-comparison deltas."""

import pyarrow as pa

from library_guides.corpus.schemas import NUMBER, TEXT, TEXTS, fields, register
from library_guides.semantics import decision_contracts as c
from library_guides.semantics.schemas import VALUE

OBJECTIVE = pa.struct(
    [
        pa.field("predicate", TEXT, nullable=False),
        pa.field("direction", TEXT, nullable=False),
        pa.field("order", pa.list_(pa.field("item", VALUE, nullable=False)), nullable=False),
        pa.field("interpretations", TEXTS, nullable=False),
    ]
)
register(
    "preference_policies",
    c.PreferencePolicy,
    [
        *fields("strategy"),
        ("objectives", pa.list_(pa.field("item", OBJECTIVE, nullable=False))),
        *fields("rationale"),
    ],
)
register(
    "counterfactuals",
    c.Counterfactual,
    [
        *fields("task", "baseline", "alternative_task", "alternative"),
        ("requirement", NUMBER),
        ("before", VALUE),
        ("after", VALUE),
        ("became_eligible", TEXTS),
        ("ceased_eligible", TEXTS),
    ],
)
