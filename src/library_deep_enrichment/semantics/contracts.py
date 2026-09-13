"""Typed semantics distinguish source interpretation, truth, and ranking."""

from __future__ import annotations

import re
from enum import StrEnum

from attrs import frozen

from library_deep_enrichment.corpus.contracts import Record, Selection


class State(StrEnum):
    """Evidence assessment under a named interpretation and applicability domain."""

    SUPPORTED = "supported"
    REFUTED = "refuted"
    UNKNOWN = "unknown"
    CONFLICTING = "conflicting"
    NOT_APPLICABLE = "not_applicable"


class Interpretation(StrEnum):
    """What an assertion's evidence can establish."""

    DECLARATION = "declaration"
    UPSTREAM_CONTRACT = "upstream_contract"
    MODELED = "modeled"
    WITNESSED = "witnessed"
    INTERPRETED = "interpreted"


class ValueKind(StrEnum):
    """Canonical language values; literal null is distinct from unknown evidence."""

    TEXT = "text"
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT_BITS = "float_bits"
    NULL = "null"
    SYMBOL = "symbol"


@frozen(kw_only=True)
class Value:
    """A canonical tagged scalar, retaining arbitrarily large integers and float bits."""

    kind: ValueKind
    text: str

    def __attrs_post_init__(self) -> None:
        """Reject ambiguous language literals at the typed boundary.

        Raises:
            ValueError: A tagged literal is not in its canonical representation.

        """
        valid = isinstance(self.kind, ValueKind) and isinstance(self.text, str)
        if self.kind == ValueKind.BOOLEAN:
            valid = valid and self.text in {"true", "false"}
        elif self.kind == ValueKind.INTEGER:
            valid = valid and re.fullmatch(r"(?:0|-?[1-9][0-9]*)", self.text) is not None
        elif self.kind == ValueKind.FLOAT_BITS:
            valid = valid and re.fullmatch(r"[0-9a-f]{16}", self.text) is not None
        elif self.kind == ValueKind.NULL:
            valid = valid and not self.text
        if not valid:
            message = "semantic value is not a canonical tagged literal"
            raise ValueError(message)


@frozen(kw_only=True)
class Predicate(Record):
    """A versioned property whose meaning is independent of language similarity."""

    name: str
    description: str
    value_kind: ValueKind
    allowed_values: tuple[str, ...]
    exclusive: bool
    interpretations: tuple[Interpretation, ...]
    template: str


@frozen(kw_only=True)
class Expression(Record):
    """An ordered condition node, evaluated as data without source execution."""

    operator: str
    arguments: tuple[str, ...]
    variable: str
    value: Value


@frozen(kw_only=True)
class Rule(Record):
    """A reusable extraction/transfer model, admitted separately from its approval."""

    algorithm: str
    source_family: str
    selector: str
    pattern: str
    predicate: str
    value: Value
    condition: str
    quantifier: str
    domain: str
    phase: str
    interpretation: Interpretation
    description: str
    version: str


@frozen(kw_only=True)
class Assertion(Record):
    """One precise consequence; unrelated prose cannot inherit its qualification."""

    subject: str
    predicate: str
    value: Value
    condition: str
    quantifier: str
    domain: str
    phase: str
    interpretation: Interpretation
    state: State
    support: tuple[Selection, ...]
    rule: str
    scope: str


@frozen(kw_only=True)
class Proof(Record):
    """A checkable consequence certificate with separate premises and read scope."""

    conclusion: str
    rule: str
    premises: tuple[Selection, ...]
    read_set: tuple[Selection, ...]
    scopes: tuple[str, ...]
    steps: tuple[str, ...]
    checker: str


@frozen(kw_only=True)
class Mode(Record):
    """A guarded operation specialization with explicit symbolic parameter bindings."""

    operation: str
    condition: str
    bindings: tuple[str, ...]
    assertions: tuple[str, ...]
    label: str


@frozen(kw_only=True)
class Slot:
    """A typed value/resource prerequisite in a capability or composition."""

    role: str
    type_expression: str
    representation: str
    resource: str
    consumes: bool


@frozen(kw_only=True)
class Capability(Record):
    """An operation-mode realization of a reusable problem-facing schema."""

    schema: str
    operation: str
    mode: str
    inputs: tuple[Slot, ...]
    outputs: tuple[Slot, ...]
    assertions: tuple[str, ...]
    condition: str
    label: str


@frozen(kw_only=True)
class Requirement:
    """A consumer constraint, including which evidence interpretation it accepts."""

    predicate: str
    value: Value
    operator: str
    interpretations: tuple[Interpretation, ...]
    mandatory: bool


@frozen(kw_only=True)
class Assignment:
    """One known context assignment; unassigned variables stay unknown."""

    variable: str
    value: Value


@frozen(kw_only=True)
class Task(Record):
    """A typed goal, partial use context, and independent candidate selection."""

    goal: str
    profiles: tuple[str, ...]
    requirements: tuple[Requirement, ...]
    context: tuple[Assignment, ...]
    inputs: tuple[Slot, ...]
    preferences: tuple[str, ...]
    description: str


@frozen(kw_only=True)
class RequirementResult:
    """One checked requirement with exact reasons and source assertion revisions."""

    predicate: str
    required: Value
    state: State
    assertions: tuple[str, ...]
    reason: str


@frozen(kw_only=True)
class CandidateResult:
    """A constraint-first alternative with unresolved dimensions preserved."""

    operation: str
    capability: str
    disposition: str
    requirements: tuple[RequirementResult, ...]
    reversing_conditions: tuple[str, ...]


@frozen(kw_only=True)
class Comparison(Record):
    """An attributed comparison over an independently recorded finite universe."""

    task: str
    universe: str
    candidates: tuple[CandidateResult, ...]
    disposition: str
    preferred: tuple[str, ...]
    unresolved: tuple[str, ...]


@frozen(kw_only=True)
class PlanStep:
    """An operation with explicit input-value bindings and produced value IDs."""

    capability: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


@frozen(kw_only=True)
class Composition(Record):
    """A bounded multi-input hypergraph candidate and its qualification frontier."""

    task: str
    universe: str
    steps: tuple[PlanStep, ...]
    assertions: tuple[str, ...]
    witnesses: tuple[str, ...]
    disposition: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class Witness(Record):
    """A compile/run observation restricted to its exact input and environment."""

    operation: str
    kind: str
    input_blob: str
    output_blob: str
    command: tuple[str, ...]
    environment: str
    exit_code: int
    scope: str
    assertions: tuple[str, ...]


@frozen(kw_only=True)
class CapabilitySchema(Record):
    """A data-authored reusable goal pattern, distinct from its operation realizations."""

    name: str
    description: str
    requirements: tuple[Requirement, ...]
    any_qualified_support: bool
