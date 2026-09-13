"""Source-aligned static typing evidence, separate from executable dispatch guarantees."""

from attrs import frozen

from library_deep_enrichment.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class DeclarationLocation:
    """A TSP declaration resolved only against the selected artifact's retained bytes."""

    path: str
    name: str
    category: str
    source: str
    start: int
    end: int
    state: str
    identity: str


@frozen(kw_only=True)
class TypePoint:
    """One static observation; protocol numbering is local to its original native fact."""

    fact: str
    role: str
    start: int
    end: int
    expected_fallback: bool
    declarations: tuple[DeclarationLocation, ...]


@frozen(kw_only=True)
class BehaviorTyping(Record):
    """Static evidence over source-owner coordinates under an independently recorded context."""

    request: str
    program: str
    artifact: str
    context: str
    source: str
    model: str
    points: tuple[TypePoint, ...]
    frontier: tuple[str, ...]
    support: tuple[Selection, ...]
