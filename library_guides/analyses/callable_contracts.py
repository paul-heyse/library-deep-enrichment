"""Finite public candidate populations and contextual executable source correspondence."""

from attrs import frozen

from library_guides.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class CallableRequest(Record):
    """Immutable declaration and body catalogs; file names select observed source scope."""

    interfaces: tuple[str, ...]
    executables: tuple[str, ...]
    files: tuple[str, ...] = ()
    max_facts: int = 100_000
    max_bytes: int = 128 * 1024 * 1024


@frozen(kw_only=True)
class BodyCandidate:
    """An exact source correspondence in one compilation or Python extraction context."""

    owner: str
    artifact: str
    context: str
    definition: str
    phase: str
    source: str
    start: int
    end: int
    state: str


@frozen(kw_only=True)
class CallableCandidate:
    """A source identity independent of numbering; context remains a separate mandatory key.

    Matching source identities never merge compilation contexts or prove runtime binding.
    """

    declaration: str
    context: str
    identity: str
    symbol: str
    routes: tuple[str, ...]
    reachability: str
    scope: str
    path: str
    source: str
    start: int
    end: int
    bodies: tuple[BodyCandidate, ...]
    disposition: str
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class CallablePopulation(Record):
    """A replayable complete finite catalog with unresolved and unlocated candidates."""

    request: str
    model: str
    candidates: tuple[CallableCandidate, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]
