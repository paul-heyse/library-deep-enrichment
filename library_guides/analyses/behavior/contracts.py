"""Owned executable and behavioral contracts; expressions form finite indexed DAGs."""

from __future__ import annotations

from enum import StrEnum

from attrs import frozen

from library_guides.corpus.contracts import Record, Selection


class Language(StrEnum):
    """The language whose executable semantics apply to a body."""

    RUST = "rust"
    PYTHON = "python"
    CXX = "cxx"


class Outcome(StrEnum):
    """Execution outcomes; unresolved and divergent are not ordinary returns."""

    RETURN = "return"
    RAISE = "raise"
    UNWIND = "unwind"
    ABORT = "abort"
    SUSPEND = "suspend"
    DIVERGE = "diverge"
    UNKNOWN = "unknown"


class Precision(StrEnum):
    """Analysis coverage, separate from evidence provenance and abstract values."""

    CLOSED = "closed_under_model"
    CONSERVATIVE = "conservative_with_frontiers"
    EXHAUSTED = "budget_exhausted"


@frozen(kw_only=True)
class Limits:
    """Finite independent limits, all part of the analysis request identity."""

    owners: int = 500
    steps: int = 200_000
    states: int = 10_000
    clauses: int = 256
    terms: int = 50_000
    call_depth: int = 12
    solver_ms: int = 1000
    solver_queries: int = 256
    widen_after: int = 3


@frozen(kw_only=True)
class Term:
    """One typed expression; arguments address earlier terms in the same table."""

    op: str
    args: tuple[int, ...] = ()
    value: str = ""
    ty: str = "unknown"


@frozen(kw_only=True)
class Instruction:
    """An evaluated operation at an exact source point, with an explicit result slot."""

    block: int
    index: int
    op: str
    destination: str = ""
    value: int = -1
    arguments: tuple[int, ...] = ()
    target: str = ""
    start: int = 0
    end: int = 0


@frozen(kw_only=True)
class Edge:
    """A guarded control edge; a missing condition is explicit, not an unknown test."""

    source: int
    target: int
    kind: str = "normal"
    condition: int = -1
    positive: bool = True


@frozen(kw_only=True)
class Frontier:
    """A precision loss with its location, affected dimension and causal explanation."""

    code: str
    dimension: str
    point: str
    detail: str


@frozen(kw_only=True)
class CallBinding:
    """An evidence-qualified target set; spelling alone never makes it complete."""

    caller: str
    point: int
    targets: tuple[str, ...]
    substitutions: tuple[str, ...]
    complete: bool
    evidence: tuple[Selection, ...]


@frozen(kw_only=True)
class BehaviorRequest(Record):
    """An exact finite body population and its contextual reconciliation inputs."""

    owners: tuple[str, ...]
    artifacts: tuple[str, ...]
    type_artifacts: tuple[str, ...] = ()
    bindings: tuple[CallBinding, ...] = ()
    limits: Limits = Limits()
    phase: str = "invoke"


@frozen(kw_only=True)
class MemberIdentity:
    """A logical member index/name and exact compiler definition within its type context."""

    index: int
    name: str
    definition: str
    type_name: str


@frozen(kw_only=True)
class VariantIdentity:
    """A source enum variant and its compiler-evaluated discriminant, not a physical offset."""

    index: int
    name: str
    discriminant: str
    discriminant_type: str
    fields: tuple[MemberIdentity, ...]


@frozen(kw_only=True)
class NominalIdentity:
    """Contextual logical type shape; declaration types retain their substitution policy."""

    definition: str
    name: str
    kind: str
    member_type_policy: str
    variants: tuple[VariantIdentity, ...]


@frozen(kw_only=True)
class BehaviorProgram(Record):
    """An admitted execution projection, reproducible from the original native evidence."""

    request: str
    owner: str
    artifact: str
    context: str
    language: Language
    symbol: str
    model: str
    parameters: tuple[str, ...]
    terms: tuple[Term, ...]
    instructions: tuple[Instruction, ...]
    edges: tuple[Edge, ...]
    blocks: tuple[int, ...]
    entry: int
    frontier: tuple[Frontier, ...]
    support: tuple[Selection, ...]
    phase: str = "invoke"
    nominals: tuple[NominalIdentity, ...] = ()


@frozen(kw_only=True)
class Guard:
    """A boolean expression and polarity under a specific outcome clause."""

    term: int
    positive: bool


@frozen(kw_only=True)
class Memory:
    """An output region or field relationship; weak updates do not prove equality."""

    location: str
    term: int
    strong: bool


@frozen(kw_only=True)
class Effect:
    """A possible effect, retaining phase, target and source ordering information."""

    kind: str
    target: str
    phase: str
    point: str


@frozen(kw_only=True)
class Region:
    """An allocation identity and mutable contents, separate from handles and ownership proof."""

    root: int
    contents: int
    extent: int
    kind: str
    owner: str
    unique: bool
    escaped: bool


@frozen(kw_only=True)
class Clause:
    """One guarded outcome with explicit uncertainty, heap changes and possible effects."""

    guards: tuple[Guard, ...]
    outcome: Outcome
    result: int
    memory: tuple[Memory, ...]
    effects: tuple[Effect, ...]
    assumptions: tuple[str, ...]
    frontier: tuple[Frontier, ...]
    regions: tuple[Region, ...] = ()


@frozen(kw_only=True)
class Metric:
    """An execution-derived analysis counter, not a library performance guarantee."""

    name: str
    value: int


@frozen(kw_only=True)
class BehaviorSummary(Record):
    """Guarded transformations under the named frontend, transfer model and assumptions."""

    request: str
    program: str
    model: str
    terms: tuple[Term, ...]
    clauses: tuple[Clause, ...]
    precision: Precision
    frontier: tuple[Frontier, ...]
    dependencies: tuple[str, ...]
    metrics: tuple[Metric, ...]
    support: tuple[Selection, ...]
