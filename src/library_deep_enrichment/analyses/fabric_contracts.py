"""Finite source-model requests and typed consequences owned by the corpus coordinator."""

from attrs import frozen

from library_deep_enrichment.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class AnalysisRequest(Record):
    """Exact same-artifact MIR owners; omitted callees remain explicit model frontiers."""

    artifact: str
    owners: tuple[str, ...]


@frozen(kw_only=True)
class ControlEdge:
    """A branch/successor/dependent triple under terminating-path control semantics."""

    branch: int
    successor: int
    dependent: int


@frozen(kw_only=True)
class SourceAnalysis(Record):
    """Recomputed MIR may-dependencies and effects; no universal behavioral qualification."""

    request: str
    owner: str
    model: str
    reachable: tuple[int, ...]
    return_dependencies: tuple[str, ...]
    may_effects: tuple[str, ...]
    local_callees: tuple[str, ...]
    effect_closed: bool
    control: tuple[ControlEdge, ...]
    control_state: str
    control_policy: str
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class PythonBoundaryRequest(Record):
    """One exact syntax owner and a separately retained typed observation lane."""

    owner: str
    types: str


@frozen(kw_only=True)
class PythonCall:
    """A syntactic call and source-aligned target candidates, without effect inference."""

    site: str
    start: int
    end: int
    lexical: tuple[str, ...]
    targets: tuple[str, ...]
    state: str


@frozen(kw_only=True)
class PythonBoundary(Record):
    """Complete finite owner call denominator with exact byte and candidate references."""

    request: str
    model: str
    syntax_source: str
    typed_source: str
    calls: tuple[PythonCall, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]
