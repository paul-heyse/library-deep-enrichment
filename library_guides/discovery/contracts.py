"""Typed analytical views, recipes, and explicit finite projection universes."""

from __future__ import annotations

from attrs import frozen

from library_guides.corpus.contracts import Record, Selection


@frozen(kw_only=True)
class DiscoveryScope(Record):
    """Conjunctive contextual selectors; empty dimensions impose no restriction."""

    profiles: tuple[str, ...]
    packages: tuple[str, ...]
    artifacts: tuple[str, ...]
    max_units: int


@frozen(kw_only=True)
class SearchSelection:
    """A selected built population and an optional narrower query-time profile filter."""

    scope: DiscoveryScope | None = None
    profiles: tuple[str, ...] = ()


@frozen(kw_only=True)
class RetrievalUnit(Record):
    """An exact semantic source view, independent of its embedding or display labels."""

    subject: str
    family: str
    title: str
    text: str
    text_digest: str
    support: tuple[Selection, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class EmbeddingRecipe(Record):
    """Everything that determines one comparable embedding space."""

    model: str
    model_revision: str
    tokenizer: str
    tokenizer_revision: str
    dimension: int
    dtype: str
    pooling: str
    normalization: str
    max_tokens: int
    document_prefix: str
    query_template: str
    runtime: str


@frozen(kw_only=True)
class Embedding(Record):
    """A validated actual model response for one exact input and recipe."""

    unit: str
    recipe: str
    input_digest: str
    vector: tuple[float, ...]
    tokens: int


@frozen(kw_only=True)
class GraphNode(Record):
    """One included operation, including nodes with no retained edges."""

    projection: str
    subject: str
    unit: str


@frozen(kw_only=True)
class GraphEdge(Record):
    """A typed structural or analytical edge with its derivation inputs."""

    projection: str
    source: str
    target: str
    kind: str
    weight: float
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class Concept(Record):
    """A grouping whose recorded algorithm defines exactly what membership means."""

    kind: str
    scope: str
    members: tuple[str, ...]
    attributes: tuple[str, ...]
    recipe: str
    support: tuple[Selection, ...]
    frontier: tuple[str, ...]


@frozen(kw_only=True)
class Descriptor(Record):
    """A source phrase ranked for navigation; it never defines a predicate."""

    concept: str
    phrase: str
    score: float
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class SearchHit:
    """A relevance result with separate retrieval channel scores and exact support."""

    unit: str
    subject: str
    score: float
    lexical: float
    dense: float
    channels: tuple[str, ...]
    support: tuple[Selection, ...]


@frozen(kw_only=True)
class SearchResult:
    """Ranked discovery results and the evidence needed to interpret their coverage."""

    manifest: str
    query: str
    hits: tuple[SearchHit, ...]
    eligible: int
    disposition: str
    frontier: tuple[str, ...]
    scope: str = ""


@frozen(kw_only=True)
class Attribute(Record):
    """A qualified positive support class with all interpretation qualifiers retained."""

    predicate: str
    value_digest: str
    condition: str
    interpretation: str
    quantifier: str
    domain: str
    phase: str
