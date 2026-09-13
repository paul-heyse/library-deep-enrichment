"""Reproducible real-vector reuse qualification over three admitted PyArrow operations."""

from __future__ import annotations

from collections import deque
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import uuid4

from attrs import evolve
from library_deep_enrichment.corpus.admission import Coordinator, WriterIdentity
from library_deep_enrichment.corpus.contracts import Operation, Passage
from library_deep_enrichment.corpus.encoding import CONVERTER, canonical, digest
from library_deep_enrichment.corpus.schemas import revision_of
from library_deep_enrichment.corpus.store import Corpus
from library_deep_enrichment.corpus.validation import references
from library_deep_enrichment.discovery.contracts import Embedding
from library_deep_enrichment.discovery.embeddings import EmbeddingClient
from library_deep_enrichment.discovery.reuse import embed_current
from library_deep_enrichment.discovery.search import search
from library_deep_enrichment.discovery.units import build_units
from library_deep_enrichment.publication.closure import _source_links
from library_deep_enrichment.runtime import RuntimeConfig, embedding_client
from library_deep_enrichment.workflows.discovery import definition
from library_deep_enrichment.workflows.engine import run_stage

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from library_deep_enrichment.corpus.contracts import Record
    from library_deep_enrichment.discovery.contracts import RetrievalUnit

SOURCE_SYMBOLS = {
    "compute-registry:add",
    "compute-registry:add_checked",
    "compute-registry:subtract",
}


class ObservedClient(EmbeddingClient):
    """Record inference requests while delegating every vector to the real local service."""

    def __init__(self, client: EmbeddingClient) -> None:
        """Keep the verified endpoint and byte-qualified recipe."""
        super().__init__(client.endpoint, client.recipe)
        self.requested: list[tuple[str, ...]] = []

    def embed_units(self, units: Sequence[RetrievalUnit]) -> Iterator[Embedding]:
        """Record exact requested unit identities.

        Yields:
            Actual validated service vectors.

        """
        self.requested.append(tuple(unit.logical_id for unit in units))
        yield from super().embed_units(units)


def _seed(corpus: Corpus) -> str:
    reader = Corpus(
        Path(".cache/library-guides-intelligence/pilot-v4/corpus"), max_rows=2_500_000
    ).reader()
    operations = tuple(
        item
        for item in reader.records("operations")
        if isinstance(item, Operation) and item.symbol in SOURCE_SYMBOLS
    )
    assert {item.symbol for item in operations} == SOURCE_SYMBOLS
    owners = {revision_of(item) for item in operations}
    pending = deque(("operations", revision_of(item)) for item in operations)
    pending.extend(
        ("passages", revision_of(item))
        for item in reader.records("passages")
        if isinstance(item, Passage) and item.owner in owners
    )
    retained: dict[str, Record] = {}
    while pending:
        family, revision = pending.popleft()
        if revision in retained:
            continue
        record = reader.get(family, revision)
        retained[revision] = record
        pending.extend((*references(record), *_source_links(record)))
    Coordinator(corpus, WriterIdentity(principal="exact-source-slice", role="migration")).commit(
        retained.values(),
        expected="",
    )
    return reader.manifest_id


def _qualify(corpus: Corpus, client: ObservedClient) -> dict[str, object]:
    units = tuple(sorted(build_units(corpus.reader()), key=lambda unit: unit.logical_id))
    assert len(units) == len(SOURCE_SYMBOLS)
    writer = Coordinator(corpus, WriterIdentity(principal="real-runtime-qualification"))
    writer.commit((*units[:2], client.recipe), expected=corpus.reader().manifest_id)
    stage = definition(
        "real-runtime-reuse.v1",
        {
            "retrieval_units": ("/text", "/text_digest"),
            "embedding_recipes": ("/runtime", "/document_prefix", "/query_template"),
        },
        ("embeddings",),
        ("discovery/embeddings.py", "discovery/reuse.py"),
    )
    stages = [run_stage(corpus, stage, lambda reader: embed_current(reader, client))]
    original = {
        item.unit: item.vector
        for item in corpus.reader().records("embeddings")
        if isinstance(item, Embedding)
    }
    writer.commit((units[2],), expected=corpus.reader().manifest_id)
    stages.append(run_stage(corpus, stage, lambda reader: embed_current(reader, client)))
    expanded = {
        item.unit: item.vector
        for item in corpus.reader().records("embeddings")
        if isinstance(item, Embedding)
    }
    assert all(expanded[key] == vector for key, vector in original.items())
    stages.append(run_stage(corpus, stage, lambda reader: embed_current(reader, client)))
    assert stages[-1].reused
    assert tuple(map(len, client.requested)) == (2, 1)
    original_recipe = revision_of(client.recipe)
    client.recipe = evolve(client.recipe, document_prefix="Library operation: ")
    writer.commit((client.recipe,), expected=corpus.reader().manifest_id)
    stages.append(run_stage(corpus, stage, lambda reader: embed_current(reader, client)))
    assert tuple(map(len, client.requested)) == (2, 1, 3)
    assert all(
        isinstance(item, Embedding) and item.recipe == revision_of(client.recipe)
        for item in corpus.reader().records("embeddings")
    )
    result = search(corpus.reader(), "add integers and report overflow errors", client=client)
    assert any("dense" in hit.channels for hit in result.hits)
    return {
        "actual_inference": True,
        "source_units": [unit.title for unit in units],
        "requested_units": client.requested,
        "inference_counts": tuple(map(len, client.requested)),
        "unchanged_vectors_reused_exactly": True,
        "initial_recipe": original_recipe,
        "changed_recipe": revision_of(client.recipe),
        "recipe_change": "Actual document prefix changed; model weights and upstream revision unchanged",
        "model_runtime": client.recipe.runtime,
        "vector_digests_before": {key: digest(vector) for key, vector in original.items()},
        "stages": [CONVERTER.unstructure(item) for item in stages],
        "hybrid_search": CONVERTER.unstructure(result),
    }


def main() -> None:
    """Qualify initial, additive, unchanged, and changed-recipe inference without fake inputs."""
    started = perf_counter()
    corpus = Corpus(Path(".cache/library-guides-intelligence/resume-runtime-reuse") / uuid4().hex)
    source_manifest = _seed(corpus)
    client = ObservedClient(
        embedding_client(
            RuntimeConfig(
                root=Path("/home/paul/.cache/library-guides-intelligence"),
            )
        )
    )
    report = _qualify(corpus, client)
    report.update(
        source_manifest=source_manifest,
        corpus=str(corpus.root),
        elapsed_seconds=perf_counter() - started,
    )
    Path(
        "tooling/library_deep_enrichment/pilot/intelligence/reports/resume-real-embedding-reuse.json"
    ).write_bytes(
        canonical(report) + b"\n",
    )


if __name__ == "__main__":
    main()
