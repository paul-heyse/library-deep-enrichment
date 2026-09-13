"""Task-independent dependency, local-cost and region-state characterization."""

from attrs import frozen

from library_guides.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class CharacterizationRequest(Record):
    """Exact behavioral populations; missing owner outcomes cannot disappear from the profile."""

    behaviors: tuple[str, ...]
    max_owners: int = 5000
    max_terms: int = 1_000_000
    max_work: int = 1_000_000


@frozen(kw_only=True)
class DependencyUse:
    """An expression dependency at a guarded summary outcome or original program point."""

    kind: str
    clause: int
    term: int
    point: int


@frozen(kw_only=True)
class DependencySource:
    """An ambient binding or unresolved result, without inferred service semantics."""

    kind: str
    name: str
    space: str
    term: int
    uses: tuple[DependencyUse, ...]
    qualification: str


@frozen(kw_only=True)
class LocalCost:
    """A structural count bound for one local CFG traversal, excluding callee internals."""

    metric: str
    lower: int
    upper: tuple[int, ...]
    basis: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class ResourceRelation:
    """One guarded region extent; expression indices refer to the exact retained summary."""

    clause: int
    root: int
    extent: int
    kind: str
    argument_dependencies: tuple[str, ...]
    ambient_dependencies: tuple[str, ...]
    escaped: bool
    unique: bool
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class OrderingObligation:
    """Observed lexical events and potential interference; never an inter-task order proof."""

    clause: int
    kind: str
    target: str
    point: str
    phase: str
    obligation: str


@frozen(kw_only=True)
class BehaviorCharacterization(Record):
    """Every requested owner receives analyzed dimensions or an explicit missing result."""

    request: str
    behavior: str
    owner: str
    coverage: str
    program: str
    summary: str
    model: str
    state: str
    dependencies: tuple[DependencySource, ...]
    costs: tuple[LocalCost, ...]
    resources: tuple[ResourceRelation, ...]
    ordering: tuple[OrderingObligation, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]
