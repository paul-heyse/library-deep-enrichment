"""Qualify explicitly scoped discovery against the expanded real source corpus."""

from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter

from library_guides.corpus.contracts import Operation
from library_guides.corpus.encoding import CONVERTER, canonical
from library_guides.corpus.schemas import revision_of
from library_guides.corpus.store import Corpus
from library_guides.discovery.contracts import DiscoveryScope, SearchSelection
from library_guides.discovery.scopes import current, units
from library_guides.discovery.search import search
from library_guides.runtime import RuntimeConfig, embedding_client
from library_guides.workflows.discovery import build_embeddings, build_graphs, build_retrieval

LOGGER = logging.getLogger(__name__)


def main() -> None:
    """Build source views, real vectors, and graph projections for one exact native artifact."""
    logging.basicConfig(level=logging.INFO)
    corpus = Corpus(Path(".cache/library-guides-intelligence/pilot-v4/corpus"), max_rows=2_500_000)
    selection = DiscoveryScope(
        logical_id="arrow-schema-docsrs-native",
        profiles=("rust-docsrs-54.1-58.4",),
        packages=("arrow_schema",),
        artifacts=("6c2a693b89f5e45f72a3347ffe0a17d9e5b1aaed4eee65171b3b0aab4e5b46d0",),
        max_units=1000,
    )
    root = Path("tooling/library_guides/pilot/intelligence")
    (root / "scopes").mkdir(exist_ok=True)
    (root / "scopes/arrow-schema-native.json").write_bytes(
        canonical(CONVERTER.unstructure(selection)) + b"\n"
    )
    started = perf_counter()
    before = corpus.reader()
    available = sum(
        isinstance(item, Operation)
        and item.profile in selection.profiles
        and item.package in selection.packages
        for item in before.records("operations")
    )
    client = embedding_client(
        RuntimeConfig(root=Path("/home/paul/.cache/library-guides-intelligence"))
    )
    stages = [build_retrieval(corpus, selection)]
    LOGGER.info("retrieval: %s", stages[-1])
    stages.append(build_embeddings(corpus, client, selection))
    LOGGER.info("embeddings: %s", stages[-1])
    stages.append(build_graphs(corpus, selection))
    LOGGER.info("graphs: %s", stages[-1])
    warm = [
        build_retrieval(corpus, selection),
        build_embeddings(corpus, client, selection),
        build_graphs(corpus, selection),
    ]
    assert all(stage.reused for stage in warm)
    reader = corpus.reader()
    population = current(reader, selection)
    source_units = tuple(units(reader, selection))
    result = search(
        reader,
        "construct a schema while preserving field and schema metadata",
        client=client,
        selection=SearchSelection(scope=selection),
    )
    assert result.eligible == len(population.members) == len(source_units)
    assert any("dense" in hit.channels for hit in result.hits)
    report = {
        "source_manifest": before.manifest_id,
        "manifest": reader.manifest_id,
        "selector": CONVERTER.unstructure(selection),
        "population": revision_of(population),
        "profile_package_operations": available,
        "native_artifact_operations": len(population.members),
        "units": len(source_units),
        "stages": [CONVERTER.unstructure(stage) for stage in stages],
        "warm": [CONVERTER.unstructure(stage) for stage in warm],
        "actual_inference": True,
        "embedding_recipe": revision_of(client.recipe),
        "search": CONVERTER.unstructure(result),
        "elapsed_seconds": perf_counter() - started,
        "limits": [
            "Contextual source scope; no operation is selected by retrieval rank",
            "Stage read sets and invalidation remain conservative at family level",
            "Scoped FCA and label stages are not yet exposed",
        ],
    }
    (root / "reports/resume-scoped-discovery.json").write_bytes(canonical(report) + b"\n")


if __name__ == "__main__":
    main()
