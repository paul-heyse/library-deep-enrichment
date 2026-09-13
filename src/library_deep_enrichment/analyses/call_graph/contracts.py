"""Contextual native call observations and finite helper-selection requests."""

from attrs import field, frozen

from library_deep_enrichment.analyses.behavior.contracts import Limits
from library_deep_enrichment.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class CallIndexRequest(Record):
    """Complete captured compiler catalogs, independent of public-owner selection."""

    artifacts: tuple[str, ...]
    max_facts: int = 100_000
    max_bytes: int = 128 * 1024 * 1024


@frozen(kw_only=True)
class ArgumentObservation:
    """An indexed substitution; the complete typed payload stays in the original native fact."""

    position: int
    kind: str
    scalar: str
    encoding: str
    type_fingerprint: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CallObservation:
    """One original MIR callsite, including open or non-item dispatch."""

    block: int
    declaration: str
    target: str
    instance_kind: str
    complete: bool
    substitutions: tuple[ArgumentObservation, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class OwnerObservation:
    """A definition body in one exact compiler context; no instance-body promotion."""

    owner: str
    artifact: str
    context: str
    definition: str
    phase: str
    native_bytes: int
    calls: tuple[CallObservation, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CallIndex(Record):
    """Complete finite native denominator with every call retained, regardless of resolution."""

    request: str
    model: str
    owners: tuple[OwnerObservation, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class CallClosureRequest(Record):
    """Explicit public or private roots and independent graph/interpreter budgets."""

    index: str
    roots: tuple[str, ...]
    max_depth: int = 12
    limits: Limits = field(factory=Limits)


@frozen(kw_only=True)
class SelectedCall:
    """An exact target lookup and its disposition within the finite captured catalog."""

    caller: str
    block: int
    target: str
    candidates: tuple[str, ...]
    state: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CallClosure(Record):
    """Selected roots/helpers and unresolved edges; not an effect-closure guarantee."""

    request: str
    index: str
    model: str
    roots: tuple[str, ...]
    helpers: tuple[str, ...]
    calls: tuple[SelectedCall, ...]
    behavior: str
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class SelectedReference:
    """Potential callable body at an original operand point; this is not an executed call."""

    statement: int
    role: str
    operand: int
    selection: SelectedCall


@frozen(kw_only=True)
class CallableClosure(CallClosure):
    """A versioned selection adding function references without changing historical call records."""

    references: tuple[SelectedReference, ...]


@frozen(kw_only=True)
class LifecycleClosure(CallableClosure):
    """Explicit drop-glue dependencies remain distinct from calls and callable operands."""

    drops: tuple[SelectedCall, ...]
