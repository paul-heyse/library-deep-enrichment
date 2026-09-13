"""Explicit consumer objectives and computed changes of task requirements."""

from attrs import frozen

from library_deep_enrichment.corpus.contracts import Record
from library_deep_enrichment.semantics.contracts import Interpretation, Value


@frozen(kw_only=True)
class Objective:
    """A preference over established values, independent of discovery relevance."""

    predicate: str
    direction: str
    order: tuple[Value, ...]
    interpretations: tuple[Interpretation, ...]


@frozen(kw_only=True)
class PreferencePolicy(Record):
    """A task-selected lexicographic or Pareto objective policy."""

    strategy: str
    objectives: tuple[Objective, ...]
    rationale: str


@frozen(kw_only=True)
class Counterfactual(Record):
    """A bounded reevaluation, with actual candidate eligibility changes."""

    task: str
    baseline: str
    alternative_task: str
    alternative: str
    requirement: int
    before: Value
    after: Value
    became_eligible: tuple[str, ...]
    ceased_eligible: tuple[str, ...]
