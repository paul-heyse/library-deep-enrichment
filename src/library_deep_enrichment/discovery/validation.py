"""Admission checks for analytical references and exact embedding input identity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from library_deep_enrichment.corpus.backend import CorpusError
from library_deep_enrichment.corpus.contracts import Scope
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.discovery import contracts as d
from library_deep_enrichment.discovery.embeddings import validate_vector

if TYPE_CHECKING:
    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.corpus.store import CorpusReader


def references(record: Record) -> tuple[tuple[str, str], ...]:
    """Enumerate exact analytical inputs without treating labels as authorities.

    Returns:
        Required selected revisions by family.

    """
    pairs = _scope_references(record)
    if isinstance(record, d.RetrievalUnit):
        pairs.append((record.family, record.subject))
    if isinstance(record, d.Embedding):
        pairs.extend((("retrieval_units", record.unit), ("embedding_recipes", record.recipe)))
    if isinstance(record, d.GraphNode):
        pairs.extend((("operations", record.subject), ("retrieval_units", record.unit)))
    if isinstance(record, d.GraphEdge):
        pairs.extend((("operations", record.source), ("operations", record.target)))
    if isinstance(record, d.Concept):
        pairs.append(("scopes", record.scope))
        pairs.extend(("operations", item) for item in record.members)
        pairs.extend(("attributes", item) for item in record.attributes)
    if isinstance(record, d.Descriptor):
        pairs.append(("concepts", record.concept))
    if isinstance(record, d.Attribute):
        pairs.append(("predicates", record.predicate))
        if record.condition:
            pairs.append(("expressions", record.condition))
    return tuple(pairs)


def _scope_references(record: Record) -> list[tuple[str, str]]:
    if isinstance(record, d.DiscoveryScope):
        return [("native_artifacts", item) for item in record.artifacts]
    if isinstance(record, Scope) and record.owner == "scoped-operation-discovery":
        return [
            ("discovery_scopes", record.query),
            *(("operations", item) for item in record.members),
        ]
    return []


def validate(reader: CorpusReader, record: Record) -> None:
    """Check exact source input and embedding recipe compatibility before admission.

    Raises:
        CorpusError: An analytical record misstates its source input or vector recipe.

    """
    from library_deep_enrichment.discovery.scopes import MAX_SCOPE_UNITS, population

    if isinstance(record, d.DiscoveryScope) and (
        record.profile
        or not 0 < record.max_units <= MAX_SCOPE_UNITS
        or not any((record.profiles, record.packages, record.artifacts))
        or any(
            len(values) != len(set(values)) or "" in values
            for values in (record.profiles, record.packages, record.artifacts)
        )
    ):
        message = "discovery requires explicit unique selectors and a 1..10000 unit bound"
        raise CorpusError(message)
    if isinstance(record, Scope) and record.owner == "scoped-operation-discovery":
        selector = reader.get("discovery_scopes", record.query)
        if not isinstance(selector, d.DiscoveryScope) or population(reader, selector) != record:
            message = "discovery population differs from its complete contextual selection"
            raise CorpusError(message)
    if isinstance(record, d.RetrievalUnit) and record.text_digest != digest(record.text):
        message = "retrieval text differs from its declared input fingerprint"
        raise CorpusError(message)
    if not isinstance(record, d.Embedding):
        return
    unit = reader.get("retrieval_units", record.unit)
    recipe = reader.get("embedding_recipes", record.recipe)
    if not isinstance(unit, d.RetrievalUnit) or not isinstance(recipe, d.EmbeddingRecipe):
        message = "embedding refers to a different source or recipe contract"
        raise CorpusError(message)
    if (
        record.input_digest != digest(recipe.document_prefix + unit.text)
        or not 0 < record.tokens <= recipe.max_tokens
    ):
        message = "embedding input or token count differs from its admitted recipe"
        raise CorpusError(message)
    if validate_vector(list(record.vector), recipe) != record.vector:
        message = "embedding was not canonicalized to its declared numerical representation"
        raise CorpusError(message)
