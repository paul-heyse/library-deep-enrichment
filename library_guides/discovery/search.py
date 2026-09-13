"""Manifest-pinned lexical and dense retrieval over independent eligible units."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import TYPE_CHECKING

import httpx
import numpy as np

from library_guides.corpus.backend import BudgetExceededError, CorpusError
from library_guides.corpus.encoding import digest
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import (
    Embedding,
    RetrievalUnit,
    SearchHit,
    SearchResult,
    SearchSelection,
)
from library_guides.discovery.scopes import current
from library_guides.discovery.scopes import units as selected_units

if TYPE_CHECKING:
    from library_guides.corpus.store import CorpusReader
    from library_guides.discovery.embeddings import EmbeddingClient

TOKEN = re.compile(r"[a-zA-Z][a-zA-Z0-9_]{1,}")
MAX_SEARCH_UNITS = 10_000
RRF_CONSTANT = 60


def _lexical(query: str, units: list[RetrievalUnit]) -> dict[str, float]:
    documents = [Counter(TOKEN.findall(unit.text.lower())) for unit in units]
    frequency = Counter(term for document in documents for term in document)
    query_terms = set(TOKEN.findall(query.lower()))
    average_length = sum(sum(document.values()) for document in documents) / max(1, len(documents))
    scores: dict[str, float] = {}
    for unit, document in zip(units, documents, strict=True):
        score = 0.0
        length = sum(document.values())
        for term in query_terms & document.keys():
            count = document[term]
            inverse = math.log(1 + (len(units) - frequency[term] + 0.5) / (frequency[term] + 0.5))
            score += (
                inverse
                * count
                * 2.2
                / (count + 1.2 * (0.25 + 0.75 * length / max(1, average_length)))
            )
        if score > 0:
            scores[revision_of(unit)] = score
    return scores


def search(
    reader: CorpusReader,
    query: str,
    *,
    client: EmbeddingClient | None = None,
    selection: SearchSelection = SearchSelection(),
    limit: int = 20,
) -> SearchResult:
    """Rank finite eligible units; missing vectors explicitly select lexical fallback.

    Returns:
        Discovery results carrying exact sources and analytical coverage limitations.

    Raises:
        BudgetExceededError: The bounded analytical projection is too large.
        CorpusError: The query or limit is invalid.

    """
    if not query.strip() or limit < 1:
        message = "search requires a nonempty query and positive result limit"
        raise CorpusError(message)
    units: list[RetrievalUnit] = []
    for unit in selected_units(reader, selection.scope):
        if not selection.profiles or unit.profile in selection.profiles:
            units.append(unit)
            if len(units) > MAX_SEARCH_UNITS:
                message = "search projection exceeds its unit budget; select a narrower profile"
                raise BudgetExceededError(message)
    lexical = _lexical(query, units)
    dense, frontier = _dense(reader, units, query, client)
    fused: dict[str, float] = {}
    for scores in (lexical, dense):
        for rank, identifier in enumerate(sorted(scores, key=lambda key: (-scores[key], key)), 1):
            fused[identifier] = fused.get(identifier, 0.0) + 1 / (RRF_CONSTANT + rank)
    selected = {revision_of(unit): unit for unit in units}
    hits = tuple(
        SearchHit(
            unit=identifier,
            subject=selected[identifier].subject,
            score=fused[identifier],
            lexical=lexical.get(identifier, 0.0),
            dense=dense.get(identifier, 0.0),
            channels=tuple(
                name
                for name, scores in (("lexical", lexical), ("dense", dense))
                if identifier in scores
            ),
            support=selected[identifier].support,
        )
        for identifier in sorted(fused, key=lambda key: (-fused[key], key))[:limit]
    )
    return SearchResult(
        manifest=reader.manifest_id,
        query=query,
        hits=hits,
        eligible=len(units),
        disposition="ranked-discovery-not-decision-universe",
        frontier=frontier,
        scope=revision_of(current(reader, selection.scope)) if selection.scope is not None else "",
    )


def _dense(
    reader: CorpusReader, units: list[RetrievalUnit], query: str, client: EmbeddingClient | None
) -> tuple[dict[str, float], tuple[str, ...]]:
    if client is None:
        return {}, ("Lexical retrieval; no embedding service was requested",)
    selected = {revision_of(unit): unit for unit in units}
    vectors = {
        item.unit: item
        for item in reader.records("embeddings")
        if isinstance(item, Embedding)
        and item.recipe == revision_of(client.recipe)
        and item.unit in selected
        and item.input_digest == digest(client.recipe.document_prefix + selected[item.unit].text)
    }
    if not vectors:
        return {}, ("Lexical fallback; this view has no vectors in the requested embedding space",)
    try:
        query_vector = np.asarray(client.embed_query(query), dtype=np.float32)
    except (OSError, ValueError, RuntimeError, httpx.HTTPError) as error:
        return {}, (f"Lexical fallback; query embedding failed: {type(error).__name__}",)
    scores = {
        key: float(np.dot(np.asarray(item.vector, dtype=np.float32), query_vector))
        for key, item in vectors.items()
    }
    frontier = (
        f"Dense coverage {len(vectors)}/{len(units)}; unembedded units remain eligible lexically",
    )
    return scores, frontier
