"""Reuse actual admitted vectors only under exact recipe and effective-input equivalence."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from attrs import evolve

from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.discovery.contracts import (
    DiscoveryScope,
    Embedding,
    EmbeddingRecipe,
    RetrievalUnit,
)
from library_deep_enrichment.discovery.scopes import units as selected_units

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from library_deep_enrichment.corpus.store import CorpusReader

MAX_HISTORY_VIEWS = 16


class EmbeddingProvider(Protocol):
    """The exact recipe and finite inference boundary required by vector reuse."""

    @property
    def recipe(self) -> EmbeddingRecipe:
        """The immutable effective-input and embedding-space contract."""
        ...

    def embed_units(self, units: Sequence[RetrievalUnit]) -> Iterator[Embedding]:
        """Produce validated vectors for the explicitly requested current units.

        Returns:
            A finite stream of observations in the declared embedding space.

        """
        ...


def embed_current(
    reader: CorpusReader, client: EmbeddingProvider, scope: DiscoveryScope | None = None
) -> Iterator[Embedding]:
    """Recover unchanged inputs from committed ancestry; compute only new effective inputs.

    Yields:
        Current-unit embeddings with verified exact recipe and text identity. Historical
        membership supplies cache candidates; orphan rows are never queried.

    """
    units = tuple(selected_units(reader, scope))
    wanted = {digest(client.recipe.document_prefix + unit.text) for unit in units}
    recipe = revision_of(client.recipe)
    cached: dict[str, Embedding] = {}
    previous: CorpusReader | None = reader
    for _ in range(MAX_HISTORY_VIEWS):
        if previous is None or wanted <= cached.keys():
            break
        for item in previous.records("embeddings"):
            if (
                isinstance(item, Embedding)
                and item.recipe == recipe
                and item.input_digest in wanted
            ):
                cached.setdefault(item.input_digest, item)
        previous = previous.previous()
    missing = []
    for unit in units:
        key = digest(client.recipe.document_prefix + unit.text)
        if key in cached:
            yield evolve(
                cached[key],
                logical_id=f"embedding:{recipe}:{unit.logical_id}",
                profile=unit.profile,
                unit=revision_of(unit),
            )
        else:
            missing.append(unit)
    yield from client.embed_units(missing)
