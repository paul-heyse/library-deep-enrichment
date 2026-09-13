"""Finite concrete observations and checks, separate from abstract transfer authority."""

from __future__ import annotations

from enum import StrEnum

from attrs import frozen

from library_guides.analyses.behavior.contracts import Outcome
from library_guides.corpus.contracts import Record, Selection


class Verdict(StrEnum):
    """A finite comparison cannot establish a universal behavioral law."""

    MATCHED = "matched_observation"
    INCONCLUSIVE = "inconclusive"
    DISAGREEMENT = "disagreement"


@frozen(kw_only=True)
class Cell:
    """One concrete value in an acyclic table; heap identity is explicit, never inferred."""

    kind: str
    scalar: str = ""
    children: tuple[int, ...] = ()
    labels: tuple[str, ...] = ()
    definition: str = ""
    variant: str = ""
    identity: str = ""


@frozen(kw_only=True)
class Input:
    """A value supplied to an exact admitted parameter slot."""

    parameter: str
    value: int


@frozen(kw_only=True)
class Projection:
    """An explicitly observed output dimension, separate from the complete returned value."""

    kind: str
    key: str = ""


@frozen(kw_only=True)
class GlobalBinding:
    """One module binding observed within this invocation, not a static dispatch guarantee."""

    name: str
    value: int


@frozen(kw_only=True)
class CallObservation:
    """A normal call return at an exact instruction, with arguments observed at call entry."""

    instruction: int
    arguments: tuple[int, ...]
    result: int


@frozen(kw_only=True)
class OperationObservation:
    """One whole operator result with entry operands, distinct from an implicit callback result."""

    instruction: int
    arguments: tuple[int, ...]
    result: int


@frozen(kw_only=True)
class Observation:
    """A single executed invocation with separately observed input and output values."""

    case: str
    summary: str
    values: tuple[Cell, ...]
    inputs: tuple[Input, ...]
    outcome: Outcome
    result: int
    assumptions: tuple[str, ...] = ()
    projection: tuple[Projection, ...] = ()
    invocation: str = ""
    globals: tuple[GlobalBinding, ...] = ()
    calls: tuple[CallObservation, ...] = ()
    operations: tuple[OperationObservation, ...] = ()


@frozen(kw_only=True)
class ObservationSet:
    """The versioned finite wire protocol emitted by a concrete witness adapter."""

    version: str
    observations: tuple[Observation, ...]
    seed: int
    generation: str


@frozen(kw_only=True)
class CaseCheck:
    """A result comparison; matching clauses are not coverage of all possible executions."""

    case: str
    verdict: Verdict
    clauses: tuple[int, ...]
    detail: tuple[str, ...]


@frozen(kw_only=True)
class BehaviorWitnessRequest(Record):
    """Compare exact admitted summaries with an attributed finite observation selection."""

    summaries: tuple[str, ...]
    observations: Selection
    evidence: tuple[Selection, ...]
    max_cases: int = 1000
    max_cells: int = 100_000


@frozen(kw_only=True)
class BehaviorWitnessCheck(Record):
    """Replayable finite checks retaining disagreements and the original full denominator."""

    request: str
    summary: str
    model: str
    cases: tuple[CaseCheck, ...]
    matched: int
    inconclusive: int
    disagreements: int
    support: tuple[Selection, ...]
