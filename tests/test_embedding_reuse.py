"""Cache protocol controls use explicitly synthetic vectors; pilot vectors come from vLLM."""

from __future__ import annotations

from typing import TYPE_CHECKING

from attrs import evolve
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Operation
from library_deep_enrichment.corpus.encoding import digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.discovery.contracts import Embedding, EmbeddingRecipe
from library_deep_enrichment.discovery.reuse import embed_current
from library_deep_enrichment.workflows.discovery import build_retrieval, definition
from library_deep_enrichment.workflows.engine import run_stage

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from library_deep_enrichment.discovery.contracts import RetrievalUnit


class FixtureProvider:
    """A counting protocol fixture, deliberately incapable of qualifying a real model pilot."""

    def __init__(self, recipe: EmbeddingRecipe) -> None:
        """Bind a synthetic test space and retain every requested input title."""
        self.recipe = recipe
        self.calls: list[tuple[str, ...]] = []

    def embed_units(self, units: Sequence[RetrievalUnit]) -> Iterator[Embedding]:
        """Record requested work and return synthetic unit vectors for cache tests.

        Yields:
            Explicit test fixtures without any model-quality assertion.

        """
        if units:
            self.calls.append(tuple(unit.title for unit in units))
        for unit in units:
            yield Embedding(
                logical_id=f"embedding:{revision_of(self.recipe)}:{unit.logical_id}",
                profile=unit.profile,
                unit=revision_of(unit),
                recipe=revision_of(self.recipe),
                input_digest=digest(self.recipe.document_prefix + unit.text),
                vector=(1.0, 0.0),
                tokens=1,
            )


def _operation(name: str) -> Operation:
    return Operation(
        logical_id=name,
        profile="fixture",
        symbol=name,
        package="fixture",
        version="1",
        language="python",
        kind="function",
        signature="(value)",
        parameters=(),
        returns="Object",
        routes=(name,),
        resolution="fixture",
        evidence=(),
    )


def test_new_competitor_reuses_unchanged_inputs_but_a_new_model_recomputes_every_vector(
    tmp_path: Path,
) -> None:
    """History reuse is recipe/text-specific and does not depend on current orphan rows."""
    corpus = Corpus(tmp_path)
    recipe = EmbeddingRecipe(
        logical_id="fixture-model",
        model="synthetic-test",
        model_revision="1",
        tokenizer="synthetic",
        tokenizer_revision="1",
        dimension=2,
        dtype="float32",
        pooling="fixture",
        normalization="l2",
        max_tokens=100,
        document_prefix="",
        query_template="{query}",
        runtime="synthetic-unit-test-only",
    )
    provider = FixtureProvider(recipe)
    writer = Coordinator(corpus, WriterIdentity(principal="fixture"))
    writer.commit((_operation("decode"), _operation("validate"), recipe), expected="")
    build_retrieval(corpus)
    stage = definition(
        "fixture-embeddings",
        {"retrieval_units": ("/text",), "embedding_recipes": ("/model_revision",)},
        ("embeddings",),
        ("discovery/reuse.py",),
        dependencies=("retrieval-units.v1",),
    )
    run_stage(corpus, stage, lambda reader: embed_current(reader, provider))
    assert provider.calls == [("decode", "validate")]
    writer.commit((_operation("new_competitor"),), expected=corpus.reader().manifest_id)
    assert not tuple(corpus.reader().records("embeddings"))
    build_retrieval(corpus)
    run_stage(corpus, stage, lambda reader: embed_current(reader, provider))
    assert provider.calls[-1] == ("new_competitor",)
    assert run_stage(corpus, stage, lambda reader: embed_current(reader, provider)).reused
    provider.recipe = evolve(recipe, model_revision="2")
    writer.commit((provider.recipe,), expected=corpus.reader().manifest_id)
    run_stage(corpus, stage, lambda reader: embed_current(reader, provider))
    assert set(provider.calls[-1]) == {"decode", "validate", "new_competitor"}
