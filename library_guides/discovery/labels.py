"""c-TF-IDF navigation descriptors constrained to phrases present in retained sources."""

from __future__ import annotations

import math
import re
from typing import TYPE_CHECKING

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import CountVectorizer

from library_guides.corpus.backend import CorpusError
from library_guides.corpus.encoding import digest
from library_guides.corpus.evidence import select
from library_guides.corpus.schemas import revision_of
from library_guides.discovery.contracts import Concept, Descriptor
from library_guides.discovery.scopes import units as selected_units

if TYPE_CHECKING:
    from collections.abc import Iterator

    from library_guides.corpus.store import CorpusReader
    from library_guides.discovery.contracts import DiscoveryScope

MAX_FEATURES = 5000
MAX_DESCRIPTOR_CANDIDATES = 30


def _selected_concepts(reader: CorpusReader, scope: DiscoveryScope | None) -> list[Concept]:
    namespace = "" if scope is None else f"scoped:{digest(scope.logical_id)}:"
    return [
        item
        for item in reader.records("concepts")
        if isinstance(item, Concept)
        and item.members
        and (
            item.logical_id.startswith(namespace)
            if scope is not None
            else not item.logical_id.startswith("scoped:")
        )
    ]


def descriptors(
    reader: CorpusReader, *, per_concept: int = 5, scope: DiscoveryScope | None = None
) -> Iterator[Descriptor]:
    """Rank actual source phrases separately from concept identity and membership.

    Yields:
        Phrases with exact source selections; descriptors grant no behavioral authority.

    Raises:
        CorpusError: The vectorizer returns a different sparse representation.

    """
    units = {item.subject: item for item in selected_units(reader, scope)}
    concepts = _selected_concepts(reader, scope)
    documents = [
        "\n".join(units[member].text for member in concept.members if member in units)
        for concept in concepts
    ]
    if not documents or not any(re.search(r"\w\w", document) for document in documents):
        return
    vectorizer = CountVectorizer(
        ngram_range=(1, 2), stop_words="english", max_features=MAX_FEATURES
    )
    matrix = vectorizer.fit_transform(documents)
    if not isinstance(matrix, csr_matrix):
        message = "descriptor vectorizer did not return the expected sparse CSR matrix"
        raise CorpusError(message)
    terms = vectorizer.get_feature_names_out()
    totals = np.asarray(matrix.sum(axis=0)).ravel()
    lengths = np.asarray(matrix.sum(axis=1)).ravel()
    average = float(np.mean(lengths))
    for index, concept in enumerate(concepts):
        row = matrix.getrow(index)
        ranked = sorted(
            (
                (
                    float(count)
                    / max(1, lengths[index])
                    * math.log(1 + average / totals[position]),
                    int(position),
                )
                for position, count in zip(row.indices, row.data, strict=True)
            ),
            reverse=True,
        )
        emitted = 0
        for score, position in ranked[:MAX_DESCRIPTOR_CANDIDATES]:
            pattern = re.compile(
                r"\b"
                + r"\s+".join(re.escape(word) for word in str(terms[position]).split())
                + r"\b",
                re.IGNORECASE,
            )
            sources = [
                units[member]
                for member in concept.members
                if member in units and pattern.search(units[member].text)
            ]
            if not sources:
                continue
            yield Descriptor(
                logical_id=f"descriptor:{revision_of(concept)}:{position}",
                concept=revision_of(concept),
                phrase=str(terms[position]),
                score=float(score),
                support=tuple(select(unit, "/text", "source-phrase") for unit in sources[:3]),
            )
            emitted += 1
            if emitted >= per_concept:
                break
